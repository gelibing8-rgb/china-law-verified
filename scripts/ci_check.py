#!/usr/bin/env python3
"""Offline CI checks for committed china-law-verified artifacts.

This script intentionally does not access official websites and does not require
the sibling candidate repositories used by the local build pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "metadata"
REPORTS = ROOT / "reports"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "NOTICE.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "CODE_OF_CONDUCT.md",
    ROOT / "CHANGELOG.md",
    ROOT / "ROADMAP.md",
    ROOT / ".github" / "pull_request_template.md",
    ROOT / ".github" / "workflows" / "ci.yml",
    META / "legal-universe.json",
    META / "business-legal-map.json",
    META / "current-version-registry.json",
    META / "p0-core-documents.json",
    REPORTS / "p0-readiness.md",
    REPORTS / "v5.0.1-data-quality.md",
]

ALLOWED_FRESHNESS = {"FRESH", "STALE", "UNKNOWN", "CONFLICT"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        return 1

    business_map = load_json(META / "business-legal-map.json")
    registry = load_json(META / "current-version-registry.json")
    p0 = load_json(META / "p0-core-documents.json")

    domains = business_map.get("domains", [])
    p0_domains = [d for d in domains if d.get("priority") == "P0"]
    p0_codes = {d.get("domain_code") for d in p0_domains}

    if business_map.get("domain_count") != len(domains):
        errors.append("business-legal-map domain_count does not match domains length")
    if len(domains) != 51:
        errors.append(f"expected 51 business domains, got {len(domains)}")
    if len(p0_domains) != 19:
        errors.append(f"expected 19 P0 domains, got {len(p0_domains)}")

    docs = p0.get("p0_core_documents", [])
    if p0.get("p0_core_total") != len(docs):
        errors.append("p0_core_total does not match p0_core_documents length")

    mapped_codes: set[str] = set()
    for rec in docs:
        freshness = rec.get("freshness_status")
        if freshness not in ALLOWED_FRESHNESS:
            errors.append(
                f"{rec.get('canonical_document_id')}: invalid freshness_status={freshness!r}"
            )

        domain_codes = rec.get("domain_codes", [])
        business_domains = rec.get("business_domains", [])
        if not domain_codes:
            errors.append(
                f"{rec.get('canonical_document_id')}: missing domain_codes many-to-many mapping"
            )
        if len(domain_codes) != len(business_domains):
            errors.append(
                f"{rec.get('canonical_document_id')}: domain_codes/business_domains length mismatch"
            )
        mapped_codes.update(domain_codes)

    missing_p0_codes = sorted(p0_codes - mapped_codes)
    if missing_p0_codes:
        errors.append(
            "P0 domains without any core-document mapping: " + ", ".join(missing_p0_codes)
        )

    selected = registry.get("current_version_selected_count")
    confirmed = registry.get("current_effective_confirmed_count")
    unconfirmed = registry.get("current_effective_unconfirmed_count")
    if not all(isinstance(x, int) for x in (selected, confirmed, unconfirmed)):
        errors.append("current-version registry counts are missing or non-integer")
    elif selected != confirmed + unconfirmed:
        errors.append(
            f"selected ({selected}) != confirmed ({confirmed}) + unconfirmed ({unconfirmed})"
        )

    readiness = (REPORTS / "p0-readiness.md").read_text(encoding="utf-8")
    if "| ? |" in readiness:
        errors.append("p0-readiness still contains unresolved '?' domain codes")
    if "0/0" in readiness:
        errors.append(
            "p0-readiness still contains 0/0 P0 core mappings; check shared-law aggregation"
        )

    if errors:
        print("[FAIL] offline CI checks")
        for e in errors:
            print(" - " + e)
        return 1

    print(
        f"[OK] domains={len(domains)} p0_domains={len(p0_domains)} "
        f"p0_core={len(docs)} selected={selected} confirmed={confirmed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
