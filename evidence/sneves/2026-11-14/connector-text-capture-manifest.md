# RAFAELIA Ω · GitHub textual capture manifest (2026-11-14)

Status: **EVIDENCE_SCOPED / EXTERNAL_ARCHIVE_NOT_OBSERVED / HOLD** · `claim_allowed=false`

This is a **new 2026 observation**, not a 2013–2014 Wayback snapshot or evidence of authorship. The Git-hosted author/committer dates can be set independently of the initial publication time. No accusation of copying or fraud is established.

## Capture contract

- Source: authenticated GitHub connector reading exact repository, commit and path.
- `SHA-256`: digest of the UTF-8 **text provided by the connector**, computed using PostgreSQL `digest(convert_to(text,'UTF8'),'sha256')`; **not** the original HTTP response payload hash and not independently timestamped.
- `Git blob SHA-1`: content-object identifier provided by GitHub connector (different identity domain).
- Complete textual file bodies: separately stored in a **private Drive custody document**, not duplicated in this public review branch. Raw network payloads and independent historical captures remain uncollected.
- No silent overwrites, no inferred license, no automated claim promotion; review before merging.

## File matrix

| Repository | Commit | Path | Git blob SHA-1 | Connector UTF-8 SHA-256 | UTF-8 bytes |
|---|---|---|---|---|---:|
| [sneves/chacha-avx2](https://github.com/sneves/chacha-avx2) | [ddc7623a](https://github.com/sneves/chacha-avx2/commit/ddc7623a50919d0314c074344ce59d2b904d018f) | [`.gitattributes`](https://github.com/sneves/chacha-avx2/blob/ddc7623a50919d0314c074344ce59d2b904d018f/.gitattributes) | `412eeda78dc9de1186c2e0e1526764af82ab3431` | `dcc4e04a9952ff446b9d78c624d80379b0f20f5817a89b9b2b1ab8b55b82fd52` | 483 |
| [sneves/chacha-avx2](https://github.com/sneves/chacha-avx2) | [ddc7623a](https://github.com/sneves/chacha-avx2/commit/ddc7623a50919d0314c074344ce59d2b904d018f) | [`.gitignore`](https://github.com/sneves/chacha-avx2/blob/ddc7623a50919d0314c074344ce59d2b904d018f/.gitignore) | `b9d6bd92f5f09e195d6bc19536500b6494dd2b75` | `1d5189269aa96147468b2ea7a88e45383c0fbdb5b621ca0cb6495a0bfcefe89b` | 2643 |
| [sneves/chacha-avx2](https://github.com/sneves/chacha-avx2) | [ddc7623a](https://github.com/sneves/chacha-avx2/commit/ddc7623a50919d0314c074344ce59d2b904d018f) | [`api.h`](https://github.com/sneves/chacha-avx2/blob/ddc7623a50919d0314c074344ce59d2b904d018f/api.h) | `4a2fa551d2ffb9571815d1fdafa602d4317ea21d` | `b3813b103241fff914de8336120c0ae50688a258d6006f5fb9114facbbe969a2` | 56 |
| [sneves/chacha-avx2](https://github.com/sneves/chacha-avx2) | [ddc7623a](https://github.com/sneves/chacha-avx2/commit/ddc7623a50919d0314c074344ce59d2b904d018f) | [`chacha-avx2.c`](https://github.com/sneves/chacha-avx2/blob/ddc7623a50919d0314c074344ce59d2b904d018f/chacha-avx2.c) | `5dbd3a3e7c5ea5a3eecfcff7c5ffd1b03eec9220` | `34eeef9a2621bef00cd8dfc747adc0986eeff8df125aab7e03459b98261bb5a7` | 15666 |
| [sneves/avx512-utils](https://github.com/sneves/avx512-utils) | [ee0ef8e7](https://github.com/sneves/avx512-utils/commit/ee0ef8e7c2136cdffa2865f55745c6270bdd396a) | [`example.cpp`](https://github.com/sneves/avx512-utils/blob/ee0ef8e7c2136cdffa2865f55745c6270bdd396a/example.cpp) | `6c4298aea1ef1b297f590d41166c242e3fa65e25` | `eeb45f17b54d13d24d4e51e87366bb4b42f271ec8d01ef2475d4686f4a3096d7` | 915 |
| [sneves/avx512-utils](https://github.com/sneves/avx512-utils) | [ee0ef8e7](https://github.com/sneves/avx512-utils/commit/ee0ef8e7c2136cdffa2865f55745c6270bdd396a) | [`makefile`](https://github.com/sneves/avx512-utils/blob/ee0ef8e7c2136cdffa2865f55745c6270bdd396a/makefile) | `1bfbf980ed467f9fb9120aea3a5e763689d493f7` | `3267b059c31f5c15c4c735e0237371bd0d1fd3ad43806527f873c494f7187636` | 175 |
| [sneves/avx512-utils](https://github.com/sneves/avx512-utils) | [ee0ef8e7](https://github.com/sneves/avx512-utils/commit/ee0ef8e7c2136cdffa2865f55745c6270bdd396a) | [`ternlog.hpp`](https://github.com/sneves/avx512-utils/blob/ee0ef8e7c2136cdffa2865f55745c6270bdd396a/ternlog.hpp) | `d6fc1ca725da1cb58fe2c6e2d2feb64fb8cc7822` | `e974045fd35b8da4c193c34de7d0523145e7d299c1e93da950250fae7d02bc7e` | 4591 |
| [sneves/avx512-utils](https://github.com/sneves/avx512-utils) | [ee0ef8e7](https://github.com/sneves/avx512-utils/commit/ee0ef8e7c2136cdffa2865f55745c6270bdd396a) | [`test.cpp`](https://github.com/sneves/avx512-utils/blob/ee0ef8e7c2136cdffa2865f55745c6270bdd396a/test.cpp) | `0ce9369754681c4a658410032eac25e734013d65` | `ace03d7b84f3f42b51cec88f51d81b4c79e81c9cb17aab94eae5d76f5a00ca84` | 2281 |

## Independent archiving targets · no historical retrieval yet

- Wayback CDX: https://web.archive.org/cdx/search/cdx?url=github.com%2Fsneves%2Fchacha-avx2
- Software Heritage origins: https://archive.softwareheritage.org/ (search `https://github.com/sneves/chacha-avx2` and `https://github.com/sneves/avx512-utils`; record visit timestamps separately)
- GH Archive: https://www.gharchive.org/ (2013–2014 events; event timestamps must be verified against original archived payload)

**Not observed:** archive-owned first-capture timestamp; archived bytes; independent historical source equivalence; earliest public availability. `TOKEN_VAZIO` does not mean no evidence exists. No scheduled crawling, publication, historical commits rewrite, force-push or merge performed.

## Falsifier / next

Search independent snapshots with source-verified observation dates and content; compare actual archived file bytes against these hashes, keeping Git metadata dates distinct from archive capture dates. A discrepancy is an investigation lead, not an automatic conclusion of fraud.
