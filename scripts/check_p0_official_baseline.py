#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATE_RE = re.compile(
    r"(?<!\d)(20\d{2})[-_/](\d{2})[-_/](\d{2})(?!\d)"
)


def extract_candidate_dates(paths):
    out = []

    for path in paths:
        for y, m, d in DATE_RE.findall(path or ""):
            try:
                out.append(
                    date(
                        int(y),
                        int(m),
                        int(d),
                    )
                )
            except ValueError:
                pass

    return sorted(set(out))


def detect_local_status(paths, official_date):
    dates = extract_candidate_dates(paths)

    if not dates:
        return (
            "NO_DATED_CANDIDATE",
            None,
        )

    latest = max(dates)
    official = date.fromisoformat(
        official_date
    )

    if latest < official:
        return (
            "LOCAL_STALE",
            latest.isoformat(),
        )

    if latest == official:
        return (
            "DATE_ALIGNED",
            latest.isoformat(),
        )

    return (
        "BASELINE_BEHIND_LOCAL",
        latest.isoformat(),
    )


def main():
    p0 = json.loads(
        (
            ROOT
            / "metadata"
            / "p0-core-documents.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    baseline = json.loads(
        (
            ROOT
            / "metadata"
            / "p0-official-version-baseline.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    docs = {
        r["canonical_document_id"]: r
        for r in p0.get(
            "p0_core_documents",
            [],
        )
    }

    errors = []

    tracked = baseline.get(
        "tracked_unknown",
        [],
    )

    if (
        baseline.get("tracked_unknown_count")
        != len(tracked)
    ):
        errors.append(
            "tracked_unknown_count mismatch"
        )

    for item in tracked:
        cid = item[
            "canonical_document_id"
        ]

        rec = docs.get(cid)

        if not rec:
            errors.append(
                "tracked P0 missing: " + cid
            )
            continue

        if (
            rec.get("freshness_status")
            != "UNKNOWN"
        ):
            errors.append(
                "tracked UNKNOWN changed "
                "without baseline review: "
                f"{cid} freshness="
                f"{rec.get('freshness_status')}"
            )

    for item in baseline.get(
        "verified_version_baselines",
        [],
    ):
        cid = item[
            "canonical_document_id"
        ]

        rec = docs.get(cid)

        if not rec:
            errors.append(
                "verified baseline P0 missing: "
                + cid
            )
            continue

        status, local_date = (
            detect_local_status(
                rec.get(
                    "candidate_paths",
                    [],
                ),
                item[
                    "official_current_version_date"
                ],
            )
        )

        print(
            f"[CHECK] {item['title']}: "
            f"local={local_date or '-'} "
            f"official="
            f"{item['official_current_version_date']} "
            f"status={status} "
            f"freshness="
            f"{rec.get('freshness_status')} "
            f"trust="
            f"{rec.get('verification_status')}"
        )

        if (
            status
            != item["expected_local_status"]
        ):
            errors.append(
                f"{item['title']}: "
                f"detected={status}, "
                f"expected="
                f"{item['expected_local_status']}"
            )

        if (
            status == "LOCAL_STALE"
            and rec.get("freshness_status")
            == "FRESH"
        ):
            errors.append(
                item["title"]
                + ": known stale candidate "
                  "must not be FRESH"
            )

    if errors:
        print(
            "[FAIL] P0 official-version "
            "drift guard"
        )

        for error in errors:
            print(" - " + error)

        return 1

    print(
        "[OK] tracked_unknown="
        f"{len(tracked)} "
        "verified_version_baselines="
        f"{len(baseline.get('verified_version_baselines', []))}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
