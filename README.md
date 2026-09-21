# china-law-verified

[![CI](https://github.com/gelibing8-rgb/china-law-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/gelibing8-rgb/china-law-verified/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Data status](https://img.shields.io/badge/data-V5.0.1-blue)

**Verified Chinese legal-source infrastructure for human and AI-agent retrieval.**

`china-law-verified` is a public, local-first legal data and verification project for Chinese laws and regulations. It separates official verification, official metadata, and candidate text so an AI agent can distinguish “found something relevant” from “safe to cite as current official law”.

中文定位：面向法律研究、合规、产业园区、项目交易和 AI Agent 的中国法律规范检索与核验基础设施。核心目标不是“多抓法律”，而是让来源、版本、时效、可信等级和缺口可追踪、可复核。

## Why this exists

AI systems can retrieve stale, superseded, incomplete, or third-party legal text and still present it confidently. This project addresses that failure mode by maintaining:

- a canonical legal-universe index;
- explicit current-version and freshness states;
- trust levels (`VERIFIED`, `OFFICIAL_META`, `CANDIDATE`, `UNVERIFIED`);
- official-source allowlists;
- topic routing for agent workflows;
- reproducible QA and data-quality reports;
- explicit gaps instead of fabricated certainty.

This repository is **not** a substitute for official legal databases, professional legal judgment, or final legal verification.

## Current snapshot — V5.0.1

As of the current committed V5.0.1 data snapshot:

- Canonical legal norms: **5,637**
- `current_version_selected`: **5,362**
- `current_effective_confirmed`: **1,533**
- `current_effective_unconfirmed`: **3,829**
- P0 business domains: **19**
- P0 core norms: **20**
- P0 local-text availability: **20 / 20**
- P0 freshness: **4 FRESH / 0 STALE / 16 UNKNOWN / 0 CONFLICT**
- Topic routing acceptance: **10 / 10**
- Coverage acceptance: **7 / 10**, with 3 explicitly partial scenarios

The repository intentionally keeps `CANDIDATE` separate from official verification. A candidate match is useful for discovery, but it is **not final legal authority**.

See:

- [`reports/v5.0.1-data-quality.md`](reports/v5.0.1-data-quality.md)
- [`reports/p0-readiness.md`](reports/p0-readiness.md)
- [`reports/v5-acceptance.md`](reports/v5-acceptance.md)

## Trust model

| Level | Meaning | Use |
| --- | --- | --- |
| `VERIFIED` | Metadata and full text verified against an official source | Can support citation, subject to date/context review |
| `OFFICIAL_META` | Official metadata/structure verified; full text not line-by-line verified | Discovery and version identification; recheck before final citation |
| `CANDIDATE` | Open-source/local candidate used to locate relevant law | Discovery only; must return to official source |
| `UNVERIFIED` | Not sufficiently verified | Do not rely on it |

For contracts, legal opinions, litigation, arbitration, government documents, major investment, major transactions, or other high-stakes decisions, re-check the currently effective official source before relying on any result.

## What is in this repository

```text
china-law-verified/
├── README.md
├── LICENSE
├── NOTICE.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
├── ROADMAP.md
├── sources.yaml
├── laws/
├── legal-topics/
├── metadata/
├── reports/
├── scripts/
└── .github/
```

The repository contains project-owned code, metadata, schemas, reports, and selected official-source verification records. Candidate source repositories are used locally and are not silently re-published here.

## Quick start

### Search verified/official layers

```bash
python3 scripts/search.py "减资"
```

### Search across configured layers

```bash
python3 scripts/search_all.py \
  --query "公司减资如何通知债权人" \
  --keywords "减资" "通知债权人" "债权人"
```

The output keeps trust levels explicit instead of flattening every hit into a single “answer”.

### Run repository checks

```bash
python3 scripts/verify.py
python3 scripts/ci_check.py
```

## Data architecture

### 1. Canonical universe

`metadata/legal-universe.json` deduplicates candidate records into canonical documents and tracks document type, status, version, candidate sources, and freshness.

### 2. Current-version registry

`metadata/current-version-registry.json` separates:

- `current_version_selected`
- `current_effective_confirmed`
- `current_effective_unconfirmed`

A record is only “confirmed current effective” when all required conditions are met.

### 3. P0 business coverage

`metadata/p0-core-documents.json` and `reports/p0-readiness.md` track the legal core needed for 19 high-priority business/legal domains.

### 4. Topic routing

`legal-topics/` supports topic-scoped retrieval so an agent can route a business/legal question to a constrained legal domain before searching.

## Official-source policy

Allowed official domains are maintained in [`sources.yaml`](sources.yaml), including sources such as:

- `flk.npc.gov.cn`
- `npc.gov.cn`
- `gov.cn`
- `court.gov.cn`
- `moj.gov.cn`
- `spp.gov.cn`

The project does **not** authorize bypassing access controls.

### Hard boundaries

Automated workflows must not:

1. bypass CAPTCHA, login, sliders, cookies, tokens, or access controls;
2. evade rate limits, anti-bot controls, or abuse controls;
3. call unpublished internal APIs or private-network endpoints;
4. spoof identity/IP or distribute scraping to evade controls;
5. keep retrying after a site signals access restriction;
6. treat third-party legal text as official merely because it is easy to fetch.

When an official site blocks automation, the correct result is an explicit verification gap, not a workaround.

## Agent / LLM boundary

AI agents may:

- turn a natural-language question into search keywords;
- choose relevant topics;
- summarize verified metadata and clearly labeled candidate results;
- identify missing verification.

AI agents must not:

- invent legal text;
- rewrite a candidate as if it were official text;
- silently upgrade `CANDIDATE` to `VERIFIED`;
- hide uncertainty or freshness gaps.

## Maintenance policy

The project is actively maintained even when the core source set is stable.

Active maintenance includes:

- freshness and current-version checks;
- schema and data-quality fixes;
- official-source compatibility;
- topic routing and coverage improvements;
- regression tests;
- agent integration examples;
- documentation, issues, pull requests, and releases.

The project does not expand source coverage merely to increase record count. New sources should improve authority, reproducibility, or coverage of a known gap.

## Known limitations

- Most canonical records are still `CANDIDATE`, not `VERIFIED`.
- Several P0 laws still have `UNKNOWN` freshness and require official re-check.
- Some scenarios remain `COVERAGE_PARTIAL`, including industrial-land performance, government-platform cooperation, and investment-promotion/subsidy compliance.
- Candidate repositories and official sites have different licensing, availability, and access constraints.
- A successful search is not the same as a legally sufficient conclusion.

## Contributing

Contributions are welcome, especially for:

- reproducible data-quality fixes;
- official-source verification;
- tests and QA;
- topic routing improvements;
- documentation;
- agent integration examples.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security and data-integrity reports

See [`SECURITY.md`](SECURITY.md). Sensitive vulnerabilities should use GitHub Security Advisories rather than public issues.

## License and legal text notice

Project-owned code and documentation are licensed under the MIT License. Legal texts and third-party candidate sources have separate provenance and rights boundaries.

See [`LICENSE`](LICENSE) and [`NOTICE.md`](NOTICE.md).
