#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-_/](\d{2})[-_/](\d{2})(?!\d)")

def extract_candidate_dates(paths):
    out = []
    for path in paths:
        for y, m, d in DATE_RE.findall(path or ""):
            try:
                out.append(date(int(y), int(m), int(d)))
            except ValueError:
                pass
    return sorted(set(out))

def classify_candidate_set(candidate_paths, official_date, current_provenance):
    official = date.fromisoformat(official_date)
    dates = extract_candidate_dates(candidate_paths)
    older = [d for d in dates if d < official]
    aligned = [d for d in dates if d == official]
    newer = [d for d in dates if d > official]

    if current_provenance:
        if older:
            return "MIXED_VERSION_CANDIDATES", max(older).isoformat()
        return "CURRENT_CANDIDATE_PRESENT", None

    if aligned:
        return "DATE_ALIGNED", official.isoformat()

    if newer:
        return "BASELINE_BEHIND_LOCAL", max(newer).isoformat()

    if older:
        return "LOCAL_STALE_ONLY", max(older).isoformat()

    return "NO_DATED_CANDIDATE", None

def main():
    p0 = json.loads(
        (ROOT / "metadata" / "p0-core-documents.json").read_text(encoding="utf-8")
    )
    baseline = json.loads(
        (ROOT / "metadata" / "p0-official-version-baseline.json").read_text(encoding="utf-8")
    )
    provenance = json.loads(
        (ROOT / "metadata" / "p0-current-candidate-provenance.json").read_text(encoding="utf-8")
    )

    docs = {
        r["canonical_document_id"]: r
        for r in p0.get("p0_core_documents", [])
    }
    prov = {
        r["canonical_document_id"]: r
        for r in provenance.get("records", [])
    }

    errors = []

    tracked = baseline.get("tracked_unknown", [])
    if baseline.get("tracked_unknown_count") != len(tracked):
        errors.append("tracked_unknown_count mismatch")

    for item in tracked:
        cid = item["canonical_document_id"]
        rec = docs.get(cid)
        if not rec:
            errors.append("tracked P0 missing: " + cid)
            continue
        if rec.get("freshness_status") != "UNKNOWN":
            errors.append(
                f"{cid}: tracked UNKNOWN changed without explicit baseline review "
                f"(freshness={rec.get('freshness_status')})"
            )

    for item in baseline.get("verified_version_baselines", []):
        cid = item["canonical_document_id"]
        rec = docs.get(cid)
        if not rec:
            errors.append("verified baseline P0 missing: " + cid)
            continue

        p = prov.get(cid)
        if p:
            if p.get("official_current_version_date") != item.get("official_current_version_date"):
                errors.append(f"{cid}: provenance/baseline official date mismatch")
            if not re.fullmatch(r"[0-9a-f]{64}", p.get("candidate_tree_sha256", "")):
                errors.append(f"{cid}: invalid candidate tree sha256")
            if not re.fullmatch(r"[0-9a-f]{40}", provenance.get("source_commit", "")):
                errors.append("invalid just-laws source commit")

        status, old_date = classify_candidate_set(
            rec.get("candidate_paths", []),
            item["official_current_version_date"],
            p,
        )

        expected = item["expected_local_status"]
        print(
            f"[CHECK] {item['title']}: "
            f"status={status} old_dated_copy={old_date or '-'} "
            f"freshness={rec.get('freshness_status')} "
            f"trust={rec.get('verification_status')}"
        )

        if status != expected:
            errors.append(
                f"{item['title']}: detected={status}, expected={expected}"
            )

        if (
            status in {"MIXED_VERSION_CANDIDATES", "LOCAL_STALE_ONLY"}
            and rec.get("freshness_status") == "FRESH"
        ):
            errors.append(
                f"{item['title']}: mixed/stale candidate set must not be marked FRESH"
            )

    if errors:
        print("[FAIL] P0 official-version drift guard")
        for error in errors:
            print(" - " + error)
        return 1

    print(
        f"[OK] tracked_unknown={len(tracked)} "
        f"current_candidate_provenance={len(prov)}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
