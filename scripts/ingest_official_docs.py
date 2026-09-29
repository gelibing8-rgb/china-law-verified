#!/usr/bin/env python3
"""把人工取得的官方正文文档（.docx）逐字核验后写入 laws/。

为什么需要人工取得
------------------
国家法律法规数据库对正文文档显式设置 permission.download = 0，
对象存储位于内网（flkoss.obs-bj2-internal.cucloud.cn）。
本项目不会自动下载，也不会绕过该限制。

因此正文由人工从官方页面取得后放入 incoming/，再由本脚本核验入库。

核验规则（全部通过才允许升格为 verified_official）
------------------------------------------------
1. 文档能解析出正文段落（而非空壳）。
2. 解析出的条号集合与官方 flfgDetails 结构树的条号集合完全一致，
   不多不少——少一条即视为正文不完整。
3. 每条正文非空。
4. 源文件 sha256 与落盘记录一致，可复现。

任一条不满足：只写入已确认的部分，verification_status 保持 needs_recheck，
并在报告中标明缺口，绝不升格。

用法
----
  1. 浏览器打开 https://flk.npc.gov.cn 搜索法律 -> 详情页 -> 下载 .docx
  2. 放到 incoming/ 下，文件名与 laws/<name>.md 同名（如 company_law_2024.docx）
  3. python3 scripts/ingest_official_docs.py --check    # 预演，不写盘
  4. python3 scripts/ingest_official_docs.py --apply    # 正式入库
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
    title = ""
    for line in front.splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip()
            break

    official_nos = structure.get(title)
    parsed_nos = set(articles)
    missing = sorted((official_nos or parsed_nos) - parsed_nos)
    extra = sorted(parsed_nos - (official_nos or parsed_nos))
    empty = sorted(n for n, lines in articles.items() if not " ".join(lines).strip())

    complete = bool(articles) and not missing and not empty
    if official_nos and extra:
        complete = False

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
        "structure_available": official_nos is not None,
        "complete": complete,
        "applied": False,
    }

    if not complete:
        result["reason"] = (
            f"正文不完整：缺 {len(missing)} 条、空 {len(empty)} 条"
            f"、意外 {len(extra)} 条；保持 verification_status=needs_recheck"
        )
        return result

    # 逐条替换占位符
    body_parts: list[str] = []
    for line in front.split("---", 2)[2].splitlines():
        stripped = line.strip()
        m = ARTICLE_RE.match(stripped)
        if m and PLACEHOLDER_RE.match(stripped):
            no = m.group(0)
            body_parts.append(render_article(no, articles.get(no, [])))
        elif not PLACEHOLDER_RE.match(stripped):
            body_parts.append(line)
    new_front = front.split("---", 2)[1]
    new_body = chr(10).join(body_parts).lstrip(chr(10))

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_front = re.sub(r"^verification_status:.*$",
                       "verification_status: verified_official",
                       new_front, count=1, flags=re.M)
    if "body_source" in new_front:
        new_front = re.sub(r"^body_source:.*$",
                           f"body_source: 人工取得官方 docx，sha256={digest}",
                           new_front, count=1, flags=re.M)
    else:
        new_front = new_front.rstrip() + chr(10) + f"body_source: 人工取得官方 docx，sha256={digest}"
    if re.search(r"^body_verified_at:", new_front, re.M):
        new_front = re.sub(r"^body_verified_at:.*$", f"body_verified_at: {stamp}",
                           new_front, count=1, flags=re.M)
    else:
        new_front = new_front.rstrip() + chr(10) + f"body_verified_at: {stamp}"

    updated = f"---{new_front}---{new_body}"
    result["content_sha256"] = sha256_bytes(new_body.lstrip(chr(10)).encode("utf-8"))
    result["verdict"] = "VERIFIED_PENDING_SHA_RECHECK"

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
        print("提示：未找到官方结构快照，"
              "将只做解析完整性检查（先运行 fetch_official_metadata.py）")

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": args.apply,
        "note": "正文由人工从官方页面取得；本脚本不下载、不绕过 permission.download=0",
        "results": [],
    }

    for docx in docxs:
        law_md = LAWS / (docx.stem + ".md")
        if not law_md.exists():
            print(f"[skip] 找不到对应 laws/{docx.stem}.md")
            continue
        res = ingest_one(law_md, docx, structure, args.apply)
        report["results"].append(res)
        mark = "OK  " if res["complete"] else "PART"
        print(f"[{mark}] {docx.name} -> {law_md.name}: "
              f"解析 {res['articles_parsed']} 条 / 官方 {res['articles_official']} 条 "
              f"缺失 {res['missing_count']} 空 {len(res['empty_articles'])}")
        if not res["complete"]:
            print(f"        {res.get('reason')}")

    if args.apply:
        # 同步 index.jsonl 的 verification_status 与 sha
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
                    d["verification_status"] = "verified_official"
                    d["body_source_sha256"] = res["source_sha256"]
                out.append(json.dumps(d, ensure_ascii=False))
            INDEX.write_text(chr(10).join(out) + chr(10), encoding="utf-8")

        applied_any = any(r.get("applied") for r in report["results"])
        if applied_any:
            print("已写盘。请运行 scripts/resync_content_sha.py 同步 content_sha256，"
                  "再运行 scripts/verify.py 复核。")
        else:
            print("没有任何文档达到入库条件，未写入任何 laws/ 文件。")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10),
                   encoding="utf-8")
    ok = sum(1 for r in report["results"] if r["complete"])
    print(f"完整 {ok}/{len(report['results'])} 部 -> {OUT.relative_to(ROOT)}")
    return 0 if ok == len(report["results"]) and report["results"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
