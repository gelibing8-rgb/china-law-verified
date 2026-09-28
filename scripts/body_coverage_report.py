"""laws/ 正文覆盖率报告：把 VERIFIED 层的真实缺口变成可量化指标。

AGENTS.md 的分层定义要求 VERIFIED = 全文已官方原文逐字核验。
本脚本统计每个法条的正文状态，使「VERIFIED 层为空」这一事实
每次都能被复查，而不是只写在文档里。

分类口径与 search_all.classify_law_line 保持一致。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.search_all import classify_law_line  # noqa: E402

LAWS = ROOT / "laws"
OUT = ROOT / "metadata" / "body-coverage.json"
ARTICLE_RE = re.compile(r"^#{1,6}\s*(第[一二三四五六七八九十百千零〇\d]+条)\s*$")


def scan(path: pathlib.Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    articles = 0
    placeholder = 0
    with_text = 0
    i = 0
    while i < len(lines):
        m = ARTICLE_RE.match(lines[i].strip())
        if m:
            articles += 1
            # 条号之后的非标题、非空行即视为该条正文
            j = i + 1
            body_lines = []
            while j < len(lines) and not ARTICLE_RE.match(lines[j].strip()):
                s = lines[j].strip()
                if s and not s.startswith("#") and not s.startswith(">"):
                    body_lines.append(s)
                j += 1
            if body_lines:
                kind, _ = classify_law_line(body_lines[0])
                if kind == "text" and "正文待补" not in body_lines[0]:
                    with_text += 1
                else:
                    placeholder += 1
            else:
                placeholder += 1
            i = j
            continue
        i += 1
    return {
        "file": path.name,
        "articles": articles,
        "with_verified_text": with_text,
        "placeholder": placeholder,
        "coverage_pct": round(100.0 * with_text / articles, 2) if articles else 0.0,
    }


def main() -> int:
    files = [p for p in sorted(LAWS.glob("*.md")) if p.name.lower() != "readme.md"]
    rows = [scan(p) for p in files]
    total_articles = sum(r["articles"] for r in rows)
    total_text = sum(r["with_verified_text"] for r in rows)
    report = {
        "generated_by": "scripts/body_coverage_report.py",
        "law_files": len(rows),
        "total_articles": total_articles,
        "with_verified_text": total_text,
        "placeholder_articles": sum(r["placeholder"] for r in rows),
        "coverage_pct": round(100.0 * total_text / total_articles, 2) if total_articles else 0.0,
        "verified_layer_ready": total_text > 0 and total_text == total_articles,
        "blocker": (
            "官方详情页为 SPA 空壳（detail.html 仅 552 字节），正文经 WPS/OFD + "
            "内网 OSS 渲染，公网无直链；不可通过候选层拷贝补齐（AGENTS.md 禁止）。"
        ),
        "per_file": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")

    print("laws 正文覆盖率")
    for r in rows:
        print(
            "  {file}: {with_verified_text}/{articles} 条有逐字正文 "
            "({coverage_pct}%)".format(**r)
        )
    print(
        "  合计: {}/{} ({:.2f}%)  VERIFIED 层就绪={}".format(
            total_text, total_articles, report["coverage_pct"], report["verified_layer_ready"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
