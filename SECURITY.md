# Security Policy

Security in this project includes both software security and legal-data integrity.

## Reporting

For sensitive vulnerabilities, use GitHub Security Advisories when available. Do not publish secrets, exploit details, credentials, private tokens, cookies, or personal data in a public issue.

Non-sensitive reproducible data-quality bugs may be reported through GitHub Issues.

## Supported version

The latest release and current `main` branch are the supported development targets.

## Important security boundaries

The project must not:

- bypass CAPTCHA, authentication, anti-bot controls, or rate limits;
- use stolen/replayed cookies or tokens;
- access private/internal endpoints without authorization;
- hide data provenance;
- silently promote candidate legal text to verified status.

## Data-integrity incidents

Treat the following as security/data-integrity issues:

- a `VERIFIED` record that cannot be reproduced from its official source;
- a wrong current-version selection that could materially affect legal analysis;
- a source/provenance mismatch;
- a hash mismatch in verified content;
- a workflow that can silently downgrade verification rules;
- accidental publication of secrets or private material.

## Secrets

This repository should not require committed credentials. If a real secret is committed, rotate it immediately and remove it from repository history where appropriate.
