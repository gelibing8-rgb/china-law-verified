# Changelog

All notable project changes are recorded here.

## [Unreleased]

### Added
- Track all 16 P0 `UNKNOWN` records in a machine-readable official-version baseline.
- Add an offline drift guard and regression tests for known stale P0 candidates.

### Changed
- Upgrade GitHub Actions to `checkout@v7` / `setup-python@v7` and pin CI to Ubuntu 24.04.

## [5.0.3] - 2026-09-21

### Fixed
- Make `scripts/v501_p0.py --reports-only` leave registry and gap metadata unchanged.
- Synchronize known `COVERAGE_PARTIAL` scenarios with the machine-readable business-gap registry.
- Make business-gap deduplication deterministic and idempotent.

### Added
- Offline regression tests for shared-law domain aggregation, strict confirmation semantics, and gap-registry consistency.

## [5.0.2] - 2026-09-21

### Fixed
- Correct P0 business-domain mapping so domain codes resolve against `business-legal-map.json`.
- Preserve many-to-many relationships when one core law supports multiple P0 domains.
- Calculate `p0_current_effective_confirmed_rate` with the same strict conditions used by the current-version registry.
- Use `current_version_date` instead of deprecated `version_date` for duplicate detection.

### Added
- Standard OSS governance files.
- CI checks that do not depend on external candidate clones.
- Issue and pull-request templates.
- Explicit license/data-rights notice.
- Maintainer roadmap.

### Changed
- README rewritten around one current V5.0.1 factual snapshot.
- Maintenance wording changed from “no more expansion” to active freshness, quality, compatibility, and agent-integration maintenance.

## [5.0.1] - 2026-09-15
- Separated routing acceptance from coverage acceptance.
- Added strict current-version selected/confirmed/unconfirmed states.
- Added P0 readiness and data-quality reporting.
- Corrected legal document taxonomy and freshness handling.
