#!/usr/bin/env python3
"""V4 专题 QA：不联网，仅校验 JSON、路径、枚举和统计一致性。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "legal-topics"
SOURCES = {
    "just-laws": ROOT.parent / "legal-sources" / "just-laws",
    "lawtext-laws": ROOT.parent / "legal-sources" / "laws",
    "china-data-laws": ROOT.parent / "legal-sources" / "china-data-laws",
}
VS = {"VERIFIED", "OFFICIAL_META", "CANDIDATE", "UNVERIFIED"}
LS = {"effective", "repealed", "replaced", "historical", "draft", "pending_verification", "not_applicable"}
RS = {"core", "direct", "related", "pending_relation"}
REF = {"active", "no_longer_reference", "historical", "pending_verification"}
AUTH = {"guiding_case", "people_court_database_case", "gazette_case", "typical_case"}


def commit(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def main() -> int:
    errors: list[str] = []
    manifests = sorted(p for p in TOPICS.glob("*/manifest.json") if p.parent.name != "_schema")
    for path in manifests:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            fail(errors, f"{path}: JSON {e}")
            continue
        topic = d.get("topic", {})
        if topic.get("schema_version") != "V4":
            fail(errors, f"{path}: schema_version != V4")
        for k in ("documents", "documents_related", "case_collections", "cases", "cases_related", "statistics", "verification", "known_gaps", "update_state"):
            if k not in d:
                fail(errors, f"{path}: 缺少 {k}")
        docs = list(d.get("documents", [])) + list(d.get("documents_related", []))
        ids = [x.get("document_id") for x in docs]
        if len(ids) != len(set(ids)):
            fail(errors, f"{path}: 重复 document_id")
        for x in docs:
            if x.get("verification_status") not in VS:
                fail(errors, f"{path}: document verification_status 非法 {x.get('document_id')}")
            if x.get("legal_status") not in LS:
                fail(errors, f"{path}: document legal_status 非法 {x.get('document_id')}")
            if x.get("relation_strength") not in RS:
                fail(errors, f"{path}: document relation_strength 非法 {x.get('document_id')}")
            for cs in x.get("candidate_sources", []) or []:
                source = cs.get("source")
                root = SOURCES.get(source)
                if not root:
                    fail(errors, f"{path}: 未知 candidate source {source}")
                    continue
                fp = root / cs.get("relative_path", "")
                if not fp.exists():
                    fail(errors, f"{path}: candidate path 不存在 {source}:{cs.get('relative_path')}")
                if not cs.get("source_commit"):
                    fail(errors, f"{path}: candidate source 缺少 commit {source}:{cs.get('relative_path')}")
        cases = list(d.get("cases", [])) + list(d.get("cases_related", []))
        cids = [x.get("case_id") for x in cases]
        if len(cids) != len(set(cids)):
            fail(errors, f"{path}: 重复 case_id")
        for x in cases:
            if x.get("verification_status") not in VS or x.get("reference_status") not in REF or x.get("case_authority") not in AUTH:
                fail(errors, f"{path}: case 状态字段非法 {x.get('case_id')}")
            if x.get("relation_strength") not in RS:
                fail(errors, f"{path}: case relation_strength 非法 {x.get('case_id')}")
        stats = d.get("statistics", {})
        if "documents_total" in stats and stats["documents_total"] != len(d.get("documents", [])) + len(d.get("documents_related", [])):
            fail(errors, f"{path}: documents_total 与清单不一致")
        if "cases_total" in stats and stats["cases_total"] != len(cases):
            fail(errors, f"{path}: cases_total 与清单不一致")

    topics_path = TOPICS / "topics.json"
    catalog_path = TOPICS / "catalog.json"
    try:
        topics = json.loads(topics_path.read_text(encoding="utf-8")).get("topics", [])
        catalog = json.loads(catalog_path.read_text(encoding="utf-8")).get("laws", [])
    except Exception as e:
        fail(errors, f"registry: {e}")
        topics, catalog = [], []
    if len(topics) != len(manifests):
        fail(errors, f"topics.json 数量 {len(topics)} != manifest 数量 {len(manifests)}")
    if len(catalog) != 311:
        fail(errors, f"catalog.json 法律数量 {len(catalog)} != 311")
    if len({x.get('title') for x in catalog}) != len(catalog):
        fail(errors, "catalog.json 存在重复标题")
    current = {k: commit(v) for k, v in SOURCES.items()}
    for m in manifests:
        d = json.loads(m.read_text(encoding="utf-8"))
        for x in list(d.get("documents", [])) + list(d.get("documents_related", [])):
            for cs in x.get("candidate_sources", []) or []:
                if cs.get("source_commit") and current.get(cs.get("source")) and cs["source_commit"] != current[cs["source"]]:
                    fail(errors, f"{m}: candidate commit stale {cs.get('source')}")
    if errors:
        print("[FAIL] QA")
        print("\n".join("- " + e for e in errors))
        return 1
    print(f"[OK] manifests={len(manifests)} catalog={len(catalog)} sources_commits=checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
