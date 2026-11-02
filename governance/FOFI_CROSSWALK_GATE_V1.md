# WAYBACK Omega — FOFI/FIFO Evidence Gate V1

State: DRAFT/HOLD, 2026-11-02. Producer: rafaelmeloreisnovo/WAYBACK; not official Internet Archive, GitHub, BLAKE3-team, or original ASP server. Preserve authorship and copyrights of external owners.

## Boundaries
SOURCE != ARTIFACT != EXECUTION != EVIDENCE != CLAIM.
C99 freestanding modules (raf_date_markers, raf_evidence_v2, raf_snapshot_free, raf_sha256_free) consume caller-owned bytes and return validated date literals, structural HTML tokens, and SHA-256. C has no libc, malloc, heap, syscall, HTTP or filesystem dependencies. Hosted Python stdlib adapter carries TLS/HTTP and JSON; this interface is NOT freestanding.

Historical site scope: www.cesarreis.com.br root and telas/prodfto.asp, www.reisoffice.com.br root; three eras 1996–2005, 2006–2018, 2019–2026, bounded sampling; user correction Raysoft was transcription of Reis Office. Prior dated 2006/2008 capture references used as pinned locators are NOT original WARC evidence. Provider CDX records and id_ replay body SHA are distinct sources.

Git scope: BLAKE3-team/BLAKE3 and rafaelmeloreisnovo/BLAKE3, public REST commits, pulls, issues, issue comments, PR review comments and commit comments. Commit SHA, author date, committer date, account hashes, PR/issue IDs, created/updated/merged timestamps, hashed message/comment body and provider URLs retained. Issues containing PR shadows must not be double counted. Metadata never proves what human ran a commit or intended a merge. User states no personally-created BLAKE3 commits in recent months; HUMAN_OPERATOR is TOKEN_VAZIO.

Date markers in HTML/IMG path, news/photo-looking URL, HTML comments and web replay are *literal source characters*, NOT EXIF photo creation dates, original publication dates, ownership or server modification times. Matching timestamps across years is not a causal bridge. Hashing an HTML body with modern SHA256 does not prove the site historically used SHA256 or BLAKE3.

Privacy: public CI artifacts retain hashes, timestamps, paths identified by bounded hashes, counts and source pointers only; never original photo bytes, arbitrary body text, credentials, personal information or executable scripts. No form submissions, browser scripts, login, crawls of arbitrary links, data deletion, automatic external Wayback saving, auto-merge or cron.

## Highest risks and terminal falsifiers
- SOURCE GAP: CDX returns empty [] in a bounded window => OK_EMPTY_BOUNDED_QUERY, not site absence; HTTP failure => TOKEN_VAZIO_PROVIDER, not zero. Fail evidence job when both source classes inaccessible.
- HISTORICAL AUTHENTICITY: compare independent original WARC bytes vs id_ replay for same source date. If WARC missing => BLOCKED_ORIGINALITY; do not claim historic edit event.
- LINK DUPLICATION: count every observed occurrence plus distinct hashed edge references; never equate hundreds of repeated prodfto references to hundreds of pages.
- DATE FALSE POSITIVES: freestanding Gregorian validation, boundary checking and explicit source-context label; reject invalid dates and embedded larger numeric tokens.
- CONTRIBUTOR ATTRIBUTION: GitHub linked account and web-flow signature are provider facts, not proof of physical operator, voluntary human approval or copyright.
- PR/ISSUE DOUBLE COUNT: de-duplicate (repo, PR, number) while preserving source entries.
- PRIVACY/RIGHTS: no raw photo download or public source-body publication; independent legal/ownership review required before broader export.
- CI AND ARTIFACTS: exact HEAD host tests, ASan/UBSan, x86_64/ARMv7/AArch64 freestanding object and no-undefined-symbol checks; upload SHA256SUMS-checked receipts with 90-day retention, not permanent or trusted timestamps.
- EXHAUSTIVENESS: each public query is capped (3 targets, 3 eras, up to 3 CDX records per era, first/last snapshots; 2 Git repos x6 endpoints x10), therefore not every archive or Git event. TOKEN_VAZIO for missing source.

## Authority and rollback
The existing GitHub main after WAYBACK PR#1 is preserved. This work is a distinct DRAFT/HOLD PR; no merge or production/site writes. Workflow runs on PR and when explicitly manually authorized after workflow availability on default; no schedule. No archive deposit claim.

Gate: source+authority+execution target+evidence rule; exact HEAD CI; rights/privacy review; provider evidence before claims. claim_allowed=false for historical causal attribution, human operator, original WARC authenticity or complete historical reconstruction.

Rollback: close unmerged PR, preserve original SHA-linked receipts, and append successor corrections rather than replacing history. STOP at verified scope or explicit BLOCKED; no infinite retry.
R3 = <F_ok: bounded reproducible C/CI source checks, F_gap: full WARC, historical photo custody and complete Git event graph, F_next: authenticated WARC same URL/date with byte diff, consent and rights gates>.
