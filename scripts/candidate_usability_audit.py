#!/usr/bin/env python3
"""候选层正文可用性审计：回答「今天到底有什么文本可用」。

laws/ 官方层正文覆盖为 0（官方正文不可公网下载，见 body_coverage_report）。
候选层本地存有大量法律全文；AGENTS.md 禁止把它们复制进 laws/，
但不禁止评估候选层能否支撑发现与定位。

两条必须遵守的统计口径：
  1. 民法典等在候选层按编拆成多个文件，必须按条号并集统计，
     否则只会数到最大的那一编，严重低估可用文本。
  2. 司法解释、实施条例等是不同法律文书，必须排除，
     否则会用它们污染本法的条文数与版本日期比较。

结论只到 CANDIDATE 信任级：候选文本不是官方正文，不得作为法律依据引用。
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent
SNAPSHOTS = ROOT / "metadata" / "official-snapshots"
OUT = ROOT / "metadata" / "candidate-usability.json"
NL = chr(10)

CANDIDATE_ROOTS = {
    "china-data-laws": WORKSPACE / "legal-sources" / "china-data-laws",
    "just-laws": WORKSPACE / "legal-sources" / "just-laws",
    "laws": WORKSPACE / "legal-sources" / "laws",
}
EXCLUDE_DIRS = ("司法解释", "行政法规", "地方性法规", "案例", "其他")
EXCLUDE_NAME = ("实施条例", "解释", "规定", "办法", "通知", "批复", "决定", "答复")
ARTICLE_RE = re.compile(r"^第[一二三四五六七八九十百千零〇\d]+条")
DATE_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")


def official_articles(title):
    for snap in sorted(SNAPSHOTS.glob("*.flfgDetails.json")):
        try:
            data = json.loads(snap.read_text(encoding="utf-8")).get("data") or {}
        except json.JSONDecodeError:
            continue
        if data.get("title") != title:
            continue
        found = set()

        def walk(node):
            head = (node.get("title") or "").strip()
            if ARTICLE_RE.match(head):
                found.add(head)
            for ch in node.get("children") or []:
                walk(ch)

        walk(data.get("content") or {})
        return found
    return set()


def scan_candidate(keywords):
    hits = []
    union = set()
    for source, root in CANDIDATE_ROOTS.items():
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            rel = str(path.relative_to(root))
            if not any(k in path.name or k in rel for k in keywords):
                continue
            if any(x in rel for x in EXCLUDE_DIRS):
                continue
            if any(x in path.name for x in EXCLUDE_NAME):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            nos = set()
            for line in text.splitlines():
                m = ARTICLE_RE.match(line.strip())
                if m:
                    nos.add(m.group(0))
            if not nos:
                continue
            union |= nos
            dm = DATE_RE.search(path.name)
            hits.append({
                "source": source,
                "relative_path": rel,
                "articles": len(nos),
                "version_date_in_name": dm.group(1) if dm else None,
            })
    hits.sort(key=lambda h: (-h["articles"], h["source"]))
    return hits, union


def verdict(official_nos, union, hits, official_date):
    if not official_nos:
        return "NO_OFFICIAL_STRUCTURE"
    if not union:
        return "NO_CANDIDATE_TEXT"
    dates = [h["version_date_in_name"] for h in hits if h["version_date_in_name"]]
    if official_date and dates and min(dates) < official_date:
        return "STALE_VERSION"
    if len(union) < len(official_nos):
        return "INCOMPLETE"
    return "ALIGNED_CANDIDATE"


def main() -> int:
    index = ROOT / "metadata" / "index.jsonl"
    if not index.exists():
        print("[FAIL] 缺少 " + str(index))
        return 2
    laws = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        title = rec.get("title", "")
        if not title:
            continue
        official_date = rec.get("current_version_date")
        nos = official_articles(title)
        hits, union = scan_candidate([title.replace("中华人民共和国", ""), title])
        laws.append({
            "title": title,
            "path": rec.get("path"),
            "official_current_version_date": official_date,
            "official_articles": len(nos),
            "candidate_distinct_articles": len(union),
            "candidate_files": len(hits),
            "candidate_hits": hits,
            "verdict": verdict(nos, union, hits, official_date),
            "trust_level": "CANDIDATE",
        })
    def count(v):
        return len([l for l in laws if l["verdict"] == v])
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "scripts/candidate_usability_audit.py",
        "trust_ceiling": "CANDIDATE",
        "disclaimer": ("候选层文本不得复制进 laws/，不得标记 verified_official，"
                       "不得作为法律依据引用；仅用于发现与定位。"),
        "official_body_coverage": "0/1624 官方正文不可公网下载，见 metadata/body-coverage.json",
        "laws": laws,
        "summary": {
            "laws_total": len(laws),
            "aligned_candidate": count("ALIGNED_CANDIDATE"),
            "stale_candidate": count("STALE_VERSION"),
            "incomplete_candidate": count("INCOMPLETE"),
            "no_candidate_text": count("NO_CANDIDATE_TEXT"),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + NL, encoding="utf-8")
    print("候选层可用性审计（信任上限 CANDIDATE）")
    for l in laws:
        print("  " + l["title"])
        print("      官方 " + str(l["official_articles"]) + " 条 / 现行 "
              + str(l["official_current_version_date"])
              + "  -> " + l["verdict"])
        print("      候选 " + str(l["candidate_distinct_articles"]) + " 条 / "
              + str(l["candidate_files"]) + " 个文件")
    s = report["summary"]
    print("  合计: 版本可用 " + str(s["aligned_candidate"]) + "/" + str(s["laws_total"])
          + "，版本过期 " + str(s["stale_candidate"])
          + "，条数不足 " + str(s["incomplete_candidate"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
