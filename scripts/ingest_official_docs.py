#!/usr/bin/env python3
"""把人工提供的正文文档（.docx）经结构检查后写入待复核的 laws/。

为什么需要人工取得
------------------
国家法律法规数据库对正文文档显式设置 permission.download = 0，
对象存储位于内网（flkoss.obs-bj2-internal.cucloud.cn）。
本项目不会自动下载，也不会绕过该限制。

因此文档须由人工通过获准的方式取得并放入 incoming/，本脚本只检查结构。

检查规则（全部通过才允许写入待人工复核正文）
------------------------------------------------
1. 文档能解析出正文段落（而非空壳）。
2. 解析出的条号集合与官方 flfgDetails 结构树的条号集合完全一致，
   不多不少——少一条即视为正文不完整。
3. 每条正文非空且无重复条号。
4. 必须按法律标题精确匹配官方结构快照。

以上仅是结构完整性检查，不证明文档来源真实性或正文逐字等同官方原文。
脚本永不自动升级 verification_status；逐字对照和来源确认后须人工升级。

任一条不满足：不写入法律文件，并在报告中标明缺口，绝不升格。

用法
----
  1. 通过获准渠道取得与官方页面可核对的 .docx，不绕过下载限制
  2. 放到 incoming/ 下，文件名与 laws/<name>.md 同名（如 company_law_2024.docx）
  3. python3 scripts/ingest_official_docs.py            # 预演，不写盘
  4. python3 scripts/ingest_official_docs.py --apply    # 写入待复核正文
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "incoming"
LAWS = ROOT / "laws"
INDEX = ROOT / "metadata" / "index.jsonl"
SNAPSHOTS = ROOT / "metadata" / "official-snapshots"
OUT = ROOT / "metadata" / "ingest-report.json"

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ARTICLE_RE = re.compile(r"^第\s*([一二三四五六七八九十百千零〇\d]+)\s*条")
PLACEHOLDER_RE = re.compile(r"^（正文待补：.*）$")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def extract_docx_paragraphs(path: Path) -> list[str]:
    """从 .docx 提取段落文本（仅用标准库，段落边界即 w:p 边界）。"""
    out: list[str] = []
    with zipfile.ZipFile(path) as zf:
        with zf.open("word/document.xml") as fh:
            root = ET.parse(fh).getroot()
    body = root.find(f"{W_NS}body")
    if body is None:
        return out
    for p in body.iter(f"{W_NS}p"):
        text = "".join(t.text or "" for t in p.iter(f"{W_NS}t"))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out


def load_official_structure() -> dict[str, set[str]]:
    """从官方 flfgDetails 快照读取每部法律的官方条号集合。"""
    if not SNAPSHOTS.exists():
        return {}
    out: dict[str, set[str]] = {}
    for snap in sorted(SNAPSHOTS.glob("*.flfgDetails.json")):
        try:
            data = json.loads(snap.read_text(encoding="utf-8")).get("data") or {}
        except json.JSONDecodeError:
            continue
        title = data.get("title") or snap.stem
        found: set[str] = set()

        def walk(node):
            heading = (node.get("title") or "").strip()
            if ARTICLE_RE.match(heading):
                found.add(heading)
            for ch in node.get("children") or []:
                walk(ch)

        walk(data.get("content") or {})
        if found:
            out[title] = found
    return out


def split_articles(paragraphs: list[str]) -> dict[str, list[str]]:
    """把段落切成 {条号: [正文行]}。"""
    articles: dict[str, list[str]] = {}
    current: str | None = None
    for para in paragraphs:
        m = ARTICLE_RE.match(para)
        if m:
            head = m.group(0)
            # 条号后紧跟的内容视为该条正文首行
            rest = para[m.end():].strip()
            current = head
            # 同一条号重复出现可能是目录、重复版面或伪造/拼接文档；
            # 不覆盖前文，也不允许以集合比对掩盖重复。
            if current in articles:
                articles[current].append("\u0000DUPLICATE_ARTICLE_MARKER")
                if rest:
                    articles[current].append(rest)
                continue
            articles.setdefault(current, [])
            if rest:
                articles[current].append(rest)
            continue
        if current is not None:
            articles[current].append(para)
    return articles


def render_article(no: str, lines: list[str]) -> str:
    body = " ".join(l for l in lines if l).strip()
    return f"{no} {body}".strip()


def ingest_one(law_md: Path, docx: Path, structure: dict[str, set[str]],
               apply: bool) -> dict:
    raw = docx.read_bytes()
    digest = sha256_bytes(raw)
    paragraphs = extract_docx_paragraphs(docx)
    articles = split_articles(paragraphs)

    front = law_md.read_text(encoding="utf-8")
    front_parts = front.split("---", 2)
    if len(front_parts) != 3 or front_parts[0] != "":
        raise ValueError(f"{law_md.name} 缺少合法 frontmatter")
    existing_status = re.search(r"^verification_status:\s*(\S+)", front_parts[1], re.M)
    status = existing_status.group(1) if existing_status else ""
    title = ""
    for line in front.splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip()
            break

    official_nos = structure.get(title)
    parsed_nos = set(articles)
    missing = sorted((official_nos or set()) - parsed_nos)
    extra = sorted(parsed_nos - (official_nos or set()))
    empty = sorted(n for n, lines in articles.items() if not " ".join(lines).strip())
    duplicates = sorted(n for n, lines in articles.items()
                        if "\u0000DUPLICATE_ARTICLE_MARKER" in lines)
    md_article_nos: set[str] = set()
    current_md_article: str | None = None
    placeholder_nos: set[str] = set()
    for line in front_parts[2].splitlines():
        stripped = line.strip()
        heading = re.match(r"^#{1,6}\s*(第\s*[一二三四五六七八九十百千零〇\d]+\s*条)", stripped)
        if heading:
            current_md_article = re.sub(r"\s+", "", heading.group(1))
            md_article_nos.add(current_md_article)
        elif current_md_article and PLACEHOLDER_RE.match(stripped):
            placeholder_nos.add(current_md_article)
    missing_md_headings = sorted((official_nos or set()) - md_article_nos)
    missing_placeholders = sorted((official_nos or set()) - placeholder_nos)

    # 条号完整性只是结构检查，不是对正文逐字真实性/官方来源的证明。
    # 没有精确标题匹配的官方结构或存在重复均 fail closed。
    structurally_complete = (bool(official_nos) and bool(articles) and not missing
                             and not empty and not extra and not duplicates
                             and not missing_md_headings and not missing_placeholders
                             and status == "needs_recheck")

    result = {
        "law_file": law_md.name,
        "docx": docx.name,
        "title": title,
        "source_sha256": digest,
        "source_bytes": len(raw),
        "paragraphs": len(paragraphs),
        "articles_parsed": len(articles),
        "articles_official": len(official_nos) if official_nos else None,
        "missing_articles": missing[:20],
        "missing_count": len(missing),
        "unexpected_articles": extra[:20],
        "empty_articles": empty[:20],
        "duplicate_articles": duplicates[:20],
        "missing_law_markdown_headings": missing_md_headings[:20],
        "missing_placeholders": missing_placeholders[:20],
        "existing_verification_status": status,
        "placeholders_to_replace": len(placeholder_nos),
        "structure_available": official_nos is not None,
        "structurally_complete": structurally_complete,
        "complete": structurally_complete,
        "verification_status": "needs_recheck",
        "promotion_allowed": False,
        "applied": False,
    }

    if not structurally_complete:
        result["reason"] = (
            f"正文不完整：缺 {len(missing)} 条、空 {len(empty)} 条"
            f"、意外 {len(extra)} 条、重复 {len(duplicates)} 条；"
            f"法库缺少条文标题 {len(missing_md_headings)} 条；"
            f"法库缺少待替换占位行 {len(missing_placeholders)} 条；"
            f"原状态={status or '缺失'}；"
            f"官方结构匹配={'是' if official_nos else '否'}；保持 verification_status=needs_recheck"
        )
        return result

    # 按仓库实际 Markdown 版式（#### 第X条 标题，下一行是占位文本）
    # 替换占位正文；原有条文编号、结构与其他内容均保留。
    body_parts: list[str] = []
    current_article: str | None = None
    for line in front_parts[2].splitlines():
        stripped = line.strip()
        heading = re.match(r"^#{1,6}\s*(第\s*[一二三四五六七八九十百千零〇\d]+\s*条)", stripped)
        if heading:
            current_article = re.sub(r"\s+", "", heading.group(1))
            body_parts.append(line)
            continue
        if current_article and PLACEHOLDER_RE.match(stripped):
            body_parts.append(render_article(current_article, articles.get(current_article, [])))
            continue
        body_parts.append(line)
    new_front = front_parts[1]
    new_body = chr(10).join(body_parts).lstrip(chr(10))

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # 自动解析和条号对齐不能证明正文与官方原文逐字一致；仅暂存正文，
    # 保留 OFFICIAL_META，人工完成来源与逐字复核后另行升级。
    if re.search(r"^body_source:", new_front, re.M):
        new_front = re.sub(r"^body_source:.*$",
                           f"body_source: 用户提供 DOCX，官方来源待人工核实，sha256={digest}",
                           new_front, count=1, flags=re.M)
    else:
        new_front = new_front.rstrip() + chr(10) + f"body_source: 用户提供 DOCX，官方来源待人工核实，sha256={digest}"
    if re.search(r"^body_ingested_at:", new_front, re.M):
        new_front = re.sub(r"^body_ingested_at:.*$", f"body_ingested_at: {stamp}",
                           new_front, count=1, flags=re.M)
    else:
        new_front = new_front.rstrip() + chr(10) + f"body_ingested_at: {stamp}"

    result["content_sha256"] = sha256_bytes(new_body.lstrip(chr(10)).encode("utf-8"))
    new_front = re.sub(r"^content_sha256:.*$",
                       f"content_sha256: {result['content_sha256']}",
                       new_front, count=1, flags=re.M)
    updated = f"---{new_front.rstrip()}\n---\n{new_body}"
    result["verdict"] = "STRUCTURE_MATCH_PENDING_HUMAN_VERIFICATION"

    if apply:
        law_md.write_text(updated, encoding="utf-8")
        result["applied"] = True
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写盘（默认预演）")
    args = ap.parse_args()

    if not INCOMING.exists():
        print(f"缺少投放目录 {INCOMING}")
        print("请先建立 incoming/ 并放入从 flk.npc.gov.cn 手动下载的 .docx，"
              "文件名与 laws/<name>.md 同名。")
        return 2

    docxs = sorted(p for p in INCOMING.glob("*.docx"))
    if not docxs:
        print(f"{INCOMING} 中没有 .docx。请放入人工下载的官方正文文档。")
        return 2

    structure = load_official_structure()
    if not structure:
        print("提示：未找到官方结构快照，全部文档将被拒绝写入"
              "（先运行 fetch_official_metadata.py）")

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": args.apply,
        "note": "来源真实性与逐字准确性待人工核实；本脚本不下载、不绕过访问限制",
        "results": [],
    }

    index_paths = []
    if args.apply:
        index_paths = [json.loads(line).get("path") for line in
                       INDEX.read_text(encoding="utf-8").splitlines() if line.strip()]

    unmatched = 0
    for docx in docxs:
        law_md = LAWS / (docx.stem + ".md")
        if not law_md.exists():
            print(f"[BLOCK] 找不到对应 laws/{docx.stem}.md")
            unmatched += 1
            continue
        if args.apply and index_paths.count("laws/" + law_md.name) != 1:
            print(f"[BLOCK] index.jsonl 中找不到唯一的 laws/{law_md.name} 记录")
            unmatched += 1
            continue
        res = ingest_one(law_md, docx, structure, args.apply)
        report["results"].append(res)
        mark = "STRUCT" if res["structurally_complete"] else "BLOCK"
        print(f"[{mark}] {docx.name} -> {law_md.name}: "
              f"解析 {res['articles_parsed']} 条 / 官方 {res['articles_official']} 条 "
              f"缺失 {res['missing_count']} 空 {len(res['empty_articles'])}")
        if not res["structurally_complete"]:
            print(f"        {res.get('reason')}")
        else:
            print("        仅条号结构匹配；正文仍为 needs_recheck，须人工逐字核验后才能升级。")

    if args.apply:
        # 同步正文来源哈希，但绝不自动提升 index.jsonl 的验证层级。
        for res in report["results"]:
            if not res.get("applied"):
                continue
            lines = INDEX.read_text(encoding="utf-8").splitlines()
            out = []
            for ln in lines:
                if not ln.strip():
                    out.append(ln)
                    continue
                d = json.loads(ln)
                if d.get("path") == "laws/" + res["law_file"]:
                    d["body_source_sha256"] = res["source_sha256"]
                    d["content_sha256"] = res["content_sha256"]
                out.append(json.dumps(d, ensure_ascii=False))
            INDEX.write_text(chr(10).join(out) + chr(10), encoding="utf-8")

        applied_any = any(r.get("applied") for r in report["results"])
        if applied_any:
            print("正文与哈希已写入待复核状态（verification_status 未升级）。"
                  "请运行 scripts/verify.py，并人工核实来源、逐字对照正文。")
        else:
            print("没有任何文档达到入库条件，未写入任何 laws/ 文件。")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10),
                   encoding="utf-8")
    ok = sum(1 for r in report["results"] if r["structurally_complete"])
    print(f"结构匹配 {ok}/{len(report['results'])} 部（不代表 VERIFIED）-> {OUT.relative_to(ROOT)}")
    return 0 if ok == len(report["results"]) and report["results"] and not unmatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
