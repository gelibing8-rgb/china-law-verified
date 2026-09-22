# P0 official-version candidate audit — 2026-09-22

This is a conservative version/provenance audit. It does **not** upgrade
candidate text to `VERIFIED` or freshness to `FRESH`.

- P0 UNKNOWN records tracked: **16**
- Official version baselines currently verified: **2**
- Current just-laws candidate provenance records: **2**

## Mixed-version candidate sets

| Law | current local candidate | older dated candidate also present | official current version | result |
| --- | --- | --- | --- | --- |
| 中华人民共和国公司法 | just-laws, 2023 revision signature confirmed | china-data-laws 2018-10-26 | 2023-12-29 | `MIXED_VERSION_CANDIDATES` |
| 中华人民共和国民事诉讼法 | just-laws, 2023 fifth-amendment signature confirmed | china-data-laws 2021-12-24 | 2023-09-01 | `MIXED_VERSION_CANDIDATES` |

## Interpretation

The earlier `LOCAL_STALE` description was too broad. The repository's candidate
set already contains a current just-laws candidate for both laws, while older
dated china-data candidate copies remain present.

The safe conclusion is therefore:

- a current discovery-layer candidate exists;
- older copies also exist;
- trust remains `CANDIDATE`;
- freshness remains `UNKNOWN`;
- consumers must not flatten the mixed set into a single `FRESH` assertion.

See `metadata/p0-current-candidate-provenance.json` for the exact upstream
commit, paths, file counts and deterministic tree SHA-256 values.
