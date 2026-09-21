# Changelog

All notable project changes are recorded here.

## [5.0.2] - Unreleased

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
