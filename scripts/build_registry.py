#!/usr/bin/env python3
"""从本地 just-laws 和专题 manifest 生成 topics.json / catalog.json。"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUST = ROOT.parent / "legal-sources" / "just-laws"
TOPICS = ROOT / "legal-topics"

TOPIC_MAP = {
    "中华人民共和国民法典": "civil-code",
    "中华人民共和国公司法": "company-law",
    "中华人民共和国劳动合同法": "labor-contract-law",
    "中华人民共和国招标投标法": "tendering-bidding-law",
    "中华人民共和国政府采购法": "government-procurement-law",
    "中华人民共和国土地管理法": "land-administration-law",
    "中华人民共和国城乡规划法": "urban-rural-planning-law",
    "中华人民共和国建筑法": "construction-law",
    "中华人民共和国安全生产法": "work-safety-law",
    "中华人民共和国环境保护法": "environmental-protection-law",
    "中华人民共和国行政处罚法": "administrative-penalty-law",
    "中华人民共和国民事诉讼法": "civil-procedure-law",
}


def commit(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def title(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines()[:80]:
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def official_titles() -> set[str]:
    out: set[str] = set()
    p = ROOT / "metadata" / "index.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("title"):
                out.add(d["title"])
    return out


def build_catalog() -> list[dict]:
    rows = []
    official = official_titles()
    for p in sorted((JUST / "docs").rglob("README.md")):
        if "versions" in p.parts or "MessageBoard" in p.parts or p.parent.name == "category":
            continue
        t = title(p)
        if not t or t in {"Just Laws", "留言板"}:
            continue
        rp = str(p.relative_to(JUST))
        category = p.relative_to(JUST / "docs").parts[0]
        rows.append({
            "law_id": "JUST-" + re.sub(r"[^A-Za-z0-9]+", "-", rp).strip("-").lower(),
            "title": t,
            "category": category,
            "candidate_path": rp,
            "candidate_source": "just-laws",
            "topic_exists": t in TOPIC_MAP and (TOPICS / TOPIC_MAP[t] / "manifest.json").exists(),
            "topic_id": TOPIC_MAP.get(t),
            "verification_status": "OFFICIAL_META" if t in official else "CANDIDATE",
        })
    return rows


def build_topics() -> list[dict]:
    rows = []
    for p in sorted(TOPICS.glob("*/manifest.json")):
        if p.parent.name == "_schema":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        t = d.get("topic", {})
        stats = d.get("statistics", {})
        by_vs = stats.get("documents_by_verification_status", {})
        kw_path = p.with_name("topic-keywords.json")
        topic_keywords: list[str] = []
        if kw_path.exists():
            try:
                topic_keywords = list(json.loads(kw_path.read_text(encoding="utf-8")).get("keywords", []) or [])
            except (OSError, json.JSONDecodeError):
                topic_keywords = []
        rows.append({
            "topic_id": t.get("id", p.parent.name),
            "title": t.get("title"),
            "primary_law": t.get("primary_law"),
            "primary_document_id": t.get("primary_document_id"),
            "topic_status": t.get("topic_status"),
            "schema_version": t.get("schema_version", "V4"),
            "last_generated_at": t.get("generated_at") or d.get("update_state", {}).get("last_generated_at"),
            "last_candidate_update": d.get("update_state", {}).get("candidate_commits", {}),
            "verified_count": by_vs.get("VERIFIED", 0),
            "official_meta_count": by_vs.get("OFFICIAL_META", 0),
            "candidate_count": by_vs.get("CANDIDATE", 0),
            "known_gap_count": len(d.get("known_gaps", [])),
            "topic_keywords": topic_keywords,
        })
    return rows


def main() -> int:
    catalog = build_catalog()
    topics = build_topics()
    (TOPICS / "catalog.json").write_text(json.dumps({"schema_version": "V4", "source": "just-laws", "generated_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), "laws": catalog}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (TOPICS / "topics.json").write_text(json.dumps({"schema_version": "V4", "topics": topics}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] catalog.json laws={len(catalog)}")
    print(f"[OK] topics.json topics={len(topics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
