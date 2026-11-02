# WAYBACK Ω — Cross-source cryptography and patent custody gate (2026-11-02)

Status: DRAFT_REVIEW / claim_allowed=false. Owner/producer: `rafaelmeloreisnovo/WAYBACK`. No authority over Internet Archive, external domains, BLAKE3-team, foreign forks, patent offices, or GitHub's service.

## Exact target matrix and origin disambiguation

Keep 12 independent `scheme × host` origins (NOT redirects or aliases by default):
- `cesarreis.com.br` (HTTP/HTTPS, www/non-www) = 4.
- `reisoffice.com.br` (HTTP/HTTPS, www/non-www) = 4.
- `reisoffice.com` (HTTP/HTTPS, www/non-www) = 4.

Both Reis Office domains are separate namespaces until registrar, DNS history, redirects, original contents and human rights/ownership evidence establish a relationship. A CDX result for one is not allowed as evidence for another. Absence or 502/timeout is `TOKEN_VAZIO_PROVIDER`, never zero captures. Do not silently canonicalize HTTP to HTTPS, www to apex, or .com to .com.br. Redirects are observations with source, target, time and status, not proof of shared historical authorship. Specific legacy paths (`/telas/prodfto.asp`) and additional paths require exact-source validation. No raw photo bodies, private metadata or raw historical page publication.

## GitHub provenance matrix — verify one record at a time

Repositories: `BLAKE3-team/BLAKE3`, `rafaelmeloreisnovo/BLAKE3`, with opt-in public named fork candidates (not an indiscriminate account crawl). Distinguish: Git object SHA-1/SHA-256 object format as reported; commit tree and parents; author/committer UTC from commit object; verified signature status; GitHub API occurrence/creation and PR event times; cross-repository head/base repo and SHA; merge commit SHA and merged_at; reviews/approvals/close/draft transitions; raw patch file hashes; comment id/created/updated and body hash. A hash of currently fetched comment text cannot reconstruct an earlier edited body. Push event time is an independent provider event if available, not committer date and not proof of who physically operated the account. GitHub shortened Events API availability from ~90 to ~30 days starting 2025-01-30: historical push events may be unrecoverable; use separately preserved original webhook or audit logs only with authorization. Never infer deliberate deletion, data exfiltration, or human operator from a gap or clock skew.

## Cryptographic taxonomy — prevent category errors

- `SHA-1`: legacy digest used by typical Wayback CDX `digest` (base32, archived response body), distinct from hash of downloaded replay.
- `SHA-2` (e.g. SHA-256/SHA-512) and `SHA-3` (Keccak): separately identified algorithms over the exact same bytes; differing outputs are expected.
- `BLAKE` (first family), `BLAKE2s/BLAKE2b`, `BLAKE3`: distinct algorithm families/versions. BLAKE3's specified compression derives from BLAKE2s with different message schedule, flags and tree/XOF construction. Same input should be compared against each algorithm's *own* published KAT, not cross-algorithm digest equality.
- `ChaCha20`: an ARX stream cipher, not a cryptographic hash. Related add/rotate/xor design primitives do not establish shared source code, patent infringement or an identical primitive.
- Capture byte scopes separately: `original_warc_body`, `id_replay_http_body`, `rendered_page`, `source_blob`, `git_tree`, `commit_object`, `build_artifact`. Label digest algorithm, input byte count, transformation, implementation/version and location.
- A matching digest on a specified byte scope supports byte equality (subject to algorithm assumptions), not chronology, creator or transmission. Cross-scheme/base-domain equal bodies can be mirrors, redirects or common templates.

## Patent/global prior-art track (separate authority)

Search primary patent offices by invention/claims, priority dates and patent families, not just by words `SHA`, `BLAKE`, `Reis` or `ChaCha`. For each positive candidate, record: office, publication number, application number, earliest claimed priority, publication date, inventor, applicant, claim text sections with independent citations, legal status by jurisdiction, earliest independently supported public prior art URL+timestamp+WARC record. Candidate keyword mention != patented algorithm != infringement != historical ownership. No verified patent number/dispute linking these domains and the BLAKE3 fork currently established: `TOKEN_VAZIO`. Data source references: EPO Espacenet https://www.epo.org/en/searching-for-patents/technical/espacenet ; GitHub Events retention https://github.blog/changelog/2024-11-08-upcoming-changes-to-data-retention-for-events-api-atom-feed-timeline-and-dashboard-feed-features/ ; BLAKE3 specification https://github.com/BLAKE3-team/BLAKE3-specs ; Wayback CDX description https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md ; patent archived-site admissibility https://manuals.ipaustralia.gov.au/patent/7.5.2-admissibility-of-evidence .

`FLORENCE` is an unresolved label. Do not join companies, names, books, cities, usernames, or patent metadata under this label without an exact source/ID. `BLACKTRACE`/`BREAKTRACE` are likewise unverified strings.

## FOFI -> FIFO terminal falsifiers, stop, and rollback

1. Revalidate exact 12-variant local tests and every origin isolation test at exact PR HEAD, plus all existing regression suites, before any live CI/manual dispatch.
2. Compare selected candidate archive memento with independent original WARC content bytes and archive provider digest as separately scoped evidence. If WARC cannot be obtained, `BLOCKED_ORIGINALITY`.
3. Compare fork/upstream commit/parent/file/tree/SHA and PR chronology from GitHub provider metadata; compare signed object validity when present; do not equate commit author date with GitHub push date. Resolve each fork path and status independently.
4. For patent relation, require exact patent/application publication ID and positive claims-to-feature map with independently supported earlier publication and valid jurisdiction/status; otherwise `TOKEN_VAZIO_PATENT_LINK`.
5. `NO_GO` on failing CI, cross-source contradiction, incomplete rights, unaudited new domain or unapproved merge. Never auto-merge, modify external sites, upload historical raw content, schedule a crawl, or claim exfiltration.
6. Stop at bounded evidence report or explicit BLOCKED state; rollback by closing draft/reverting only these isolated branch changes with append-only successor receipt; retain historical source receipts.

R3 = <F_ok: source matrices and strict URL disambiguation in candidate branch, F_gap: live captures/independent WARC/patent claims/external logs/CI terminal, F_next: exact HEAD tests + one independently sourced WARC pair and one named patent candidate if found>.
