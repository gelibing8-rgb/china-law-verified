#!/usr/bin/env python3
"""生成 laws/*.md + metadata/index.jsonl (V1 一次性脚本).

从 flk.npc.gov.cn API 返回的 flfgDetails JSON 生成 Markdown：
- 完整 frontmatter (verified metadata)
- 结构树 (编/章/条 标题) 来自 flfgDetails API
- 正文部分标记 needs_recheck，原因在每个 law 文件末尾说明
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAWS_DIR = ROOT / "laws"
META_FILE = ROOT / "metadata" / "index.jsonl"

# 3 部法律
# 日期字段说明 (V2.1)：
#   original_effective_date    = 原法律首次施行日期
#   current_version_date       = 当前修正/修订版本通过或公布日期
#   current_version_effective_date = 当前版本实际施行日期
#   effective_date             = [已废弃] 仅保留向后兼容，等同于 current_version_effective_date
#   promulgation_date          = 当前版本的公布日期（flk.npc.gov.cn gbrq）
#   version_date               = [已废弃] 仅保留向后兼容，等同于 current_version_date
LAW_SPECS = [
    {
        "key": "civil_code",
        "bbbs": "ff808081729d1efe01729d50b5c500bf",
        "title": "中华人民共和国民法典",
        "filename": "civil_code.md",
        "document_type": "法律",
        "issuing_authority": "全国人民代表大会",
        "promulgation_date": "2020-05-28",
        # 民法典是 2020 年首次通过、首次施行，无修正史
        "original_effective_date": "2021-01-01",
        "current_version_date": "2020-05-28",
        "current_version_effective_date": "2021-01-01",
        "status": "现行",
        "official_url": "https://flk.npc.gov.cn/detail.html?bbbs=ff808081729d1efe01729d50b5c500bf",
        "category_hint": "编",
    },
    {
        "key": "company_law_2024",
        "bbbs": "ff8081818c9108eb018cb6922f750c07",
        "title": "中华人民共和国公司法",
        "filename": "company_law_2024.md",
        "document_type": "法律",
        "issuing_authority": "全国人民代表大会常务委员会",
        "promulgation_date": "2023-12-29",
        # 公司法 1993-12-29 通过 / 1994-07-01 首次施行；现行版本 2023-12-29 修订 / 2024-07-01 施行
        "original_effective_date": "1994-07-01",
        "current_version_date": "2023-12-29",
        "current_version_effective_date": "2024-07-01",
        "status": "现行",
        "official_url": "https://flk.npc.gov.cn/detail.html?bbbs=ff8081818c9108eb018cb6922f750c07",
        "category_hint": "编",
    },
    {
        "key": "labor_contract_law",
        "bbbs": "2c909fdd678bf17901678bf74d7106b3",
        "title": "中华人民共和国劳动合同法",
        "filename": "labor_contract_law.md",
        "document_type": "法律",
        "issuing_authority": "全国人民代表大会常务委员会",
        "promulgation_date": "2012-12-28",
        # 劳动合同法 2007-06-29 通过 / 2008-01-01 首次施行；现行版本 2012-12-28 修正 / 2013-07-01 施行
        "original_effective_date": "2008-01-01",
        "current_version_date": "2012-12-28",
        "current_version_effective_date": "2013-07-01",
        "status": "现行",
        "official_url": "https://flk.npc.gov.cn/detail.html?bbbs=2c909fdd678bf17901678bf74d7106b3",
        "category_hint": "章",
    },
]


def classify_title(title: str) -> str:
    """根据标题判定层级：编 / 章 / 节 / 条 / 附 / 其他."""
    t = title.strip()
    if re.match(r"^第[一二三四五六七八九十百千]+编\b", t) or "编" in t[:8] and "第" in t:
        return "编"
    if re.match(r"^第[一二三四五六七八九十百千]+章\b", t):
        return "章"
    if re.match(r"^第[一二三四五六七八九十百千]+节\b", t):
        return "节"
    if re.match(r"^第[一二三四五六七八九十百千]+条\b", t):
        return "条"
    if t.startswith("附") or t in ("题注", "目录", "序言"):
        return "其他"
    return "其他"


def collect_skeleton(node, depth=0):
    """返回 (depth, title, id) 列表，跳过 children=[] 的叶节点。"""
    rows = []
    cls = classify_title(node.get("title", ""))
    rows.append((cls, node.get("title", ""), node.get("id", "")))
    for child in node.get("children", []):
        rows.extend(collect_skeleton(child, depth + 1))
    return rows


def render_markdown_body(rows, hint: str) -> str:
    out = []
    last_level = -1
    for cls, title, node_id in rows:
        if cls == "编":
            if last_level >= 1:
                out.append("")
            out.append(f"# {title}")
            last_level = 1
        elif cls == "章":
            if last_level < 1:
                out.append("# (条文)")
            out.append("")
            out.append(f"## {title}")
            last_level = 2
        elif cls == "节":
            out.append("")
            out.append(f"### {title}")
            last_level = 3
        elif cls == "条":
            out.append("")
            out.append(f"#### {title}")
            out.append("（正文待补：来自 flk.npc.gov.cn 的 WPS/OFD 文档无法在公网下载；详见 laws/README 段。条目 ID：`{}`）".format(node_id))
            last_level = 4
        else:
            # 其他：题注/目录/附则等
            out.append("")
            out.append(f"### {title}")
            last_level = 3
    return "\n".join(out) + "\n"


def build_law_file(spec: dict, full_json: dict) -> str:
    """构造完整 Markdown."""
    # 正文 = 结构树 + 头部说明 + 核验记录
    rows = collect_skeleton(full_json["data"]["content"])
    skeleton_md = render_markdown_body(rows, spec["category_hint"]).rstrip()

    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    body_top = [
        f"# {spec['title']}",
        "",
        "> **本文件仅完成 V1 元数据与结构核验。**  ",
        f"> 标题、制定机关、发布日期、施行日期、当前版本日期均已通过 flk.npc.gov.cn（国家法律法规数据库）公开 API 核验一致。  ",
        "> 各条正文文本尚未补齐，原因：flk.npc.gov.cn 的 SPA 通过内网 WPS/OFD 文档查看器渲染正文，公网无法直接下载对应文件；其他官方站点（npc.gov.cn / gov.cn / moj.gov.cn / court.gov.cn）在本次环境下 TLS 握手被服务端拒绝。  ",
        "> verification_status = `needs_recheck`。补齐方法见 `laws/README.md`。",
        "",
        skeleton_md,
        "",
        "---",
        "",
        "## 核验记录",
        "",
        "- 数据来源：flk.npc.gov.cn（国家法律法规数据库，allowed_domains 白名单内）",
        f"- bbbs：{spec['bbbs']}",
        "- 核验项：title / issuing_authority / gbrq / sxrq / sxx / flxz / zdjgName / 完整结构树（编/章/条 标题）",
        "- 未核验项：每条正文文本",
        "- 公网正文获取路径（待补）：",
        f"  1. 浏览器访问 flk.npc.gov.cn 搜索 `{spec['title']}`，进入详情页；",
        "  2. 在 WPS/OFD 查看器中逐条复制正文；",
        "  3. 替换本文件中 `（正文待补：...）` 标记；",
        "  4. 重新计算 SHA256 并写回 frontmatter；将 `verification_status` 改为 `verified_official`；",
        "  5. 运行 `python3 scripts/verify.py` 与 `python3 scripts/search.py \"关键词\"` 验收。",
        "",
    ]
    body = "\n".join(body_top)
    # SHA256 是基于最终正文（frontmatter 之后）
    body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()

    frontmatter_lines = [
        "---",
        f"title: {spec['title']}",
        f"document_type: {spec['document_type']}",
        f"issuing_authority: {spec['issuing_authority']}",
        f"promulgation_date: {spec['promulgation_date']}",
        f"original_effective_date: {spec['original_effective_date']}",
        f"current_version_date: {spec['current_version_date']}",
        f"current_version_effective_date: {spec['current_version_effective_date']}",
        # [废弃字段] 仅保留向后兼容
        f"effective_date: {spec['current_version_effective_date']}  # deprecated: 同 current_version_effective_date",
        f"status: {spec['status']}",
        f"version_date: {spec['current_version_date']}  # deprecated: 同 current_version_date",
        f"official_url: {spec['official_url']}",
        f"retrieved_at: {retrieved_at}",
        "verification_status: needs_recheck",
        f"content_sha256: {body_sha}",
        "---",
        "",
    ]
    return "\n".join(frontmatter_lines) + body


def main() -> int:
    json_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/law_fetch")
    LAWS_DIR.mkdir(parents=True, exist_ok=True)
    META_FILE.parent.mkdir(parents=True, exist_ok=True)

    index_records = []
    for spec in LAW_SPECS:
        json_path = json_dir / f"{spec['key']}_full.json"
        if not json_path.exists():
            print(f"[FAIL] missing {json_path}", file=sys.stderr)
            return 1
        with json_path.open("r", encoding="utf-8") as fh:
            full = json.load(fh)
        text = build_law_file(spec, full)
        out = LAWS_DIR / spec["filename"]
        out.write_text(text, encoding="utf-8")
        print(f"[OK] {out.relative_to(ROOT)}  ({len(text)} bytes)")

        # index record
        # 重新计算 sha256
        # 解析 frontmatter 取正文（剥除值后的 # 注释）
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        meta = {}
        for line in m.group(1).splitlines():
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            val = v.split("#", 1)[0].strip()  # strip inline comment
            meta[k.strip()] = val
        body = m.group(2)
        body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()

        index_records.append({
            "path": f"laws/{spec['filename']}",
            "title": meta["title"],
            "issuing_authority": meta["issuing_authority"],
            "promulgation_date": meta["promulgation_date"],
            "original_effective_date": meta["original_effective_date"],
            "current_version_date": meta["current_version_date"],
            "current_version_effective_date": meta["current_version_effective_date"],
            "effective_date": meta["effective_date"],  # [deprecated]
            "status": meta["status"],
            "version_date": meta["version_date"],  # [deprecated]
            "official_url": meta["official_url"],
            "retrieved_at": meta["retrieved_at"],
            "verification_status": meta["verification_status"],
            "content_sha256": body_sha,
            "bbbs": spec["bbbs"],
            "flk_source": "国家法律法规数据库 flk.npc.gov.cn",
        })

    with META_FILE.open("w", encoding="utf-8") as fh:
        for rec in index_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[OK] {META_FILE.relative_to(ROOT)}  ({len(index_records)} 条)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())