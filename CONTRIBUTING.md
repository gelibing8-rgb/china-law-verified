# Contributing

Contributions are welcome when they improve reproducibility, legal-source integrity, data quality, or maintainability.

## Before opening a pull request

1. Open or reference an issue for non-trivial changes.
2. Keep the change small enough to review.
3. Do not add unverifiable legal text or unsupported status claims.
4. Preserve source provenance and trust levels.
5. Do not bypass official-site access controls.
6. Add or update tests/checks when behavior changes.

## Local checks

```bash
python3 scripts/verify.py
python3 scripts/ci_check.py
```

If your change depends on local candidate repositories, also run the relevant topic/data build checks in the documented local environment.

## Verification changes

A record may only be promoted to `VERIFIED` when the official text and required metadata have actually been checked under the repository's verification rules.

Do not promote a record because:

- a third-party repository labels it current;
- a search engine result looks authoritative;
- an LLM says it is current;
- an official URL exists but the full text was not checked.

## Good contribution areas

- official-source freshness checks;
- reproducible bug fixes in canonicalization or domain mapping;
- test coverage;
- data-quality assertions;
- topic routing;
- English/Chinese documentation;
- safe AI-agent integration examples;
- issue triage and reproducible bug reports.

## Pull request expectations

A pull request should state:

- what changed;
- why it changed;
- what source/data was affected;
- how it was validated;
- whether any trust/freshness status changed;
- known limitations or rollback considerations.

## Prohibited contribution patterns

- fabricated users, stars, downloads, or adoption claims;
- copied proprietary legal-database content;
- secrets, cookies, private tokens, or personal data;
- techniques intended to evade CAPTCHA, authentication, rate limits, or access controls;
- generated legal text presented as official text.
