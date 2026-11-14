# RAFAELIA Ω — S2 ZIP custody readback (2026-11-14)

Predecessor: [GitHub textual capture manifest](./connector-text-capture-manifest.md) on review-only branch.

- State: `PASS_SCOPED_SOURCE_TEXT_RECONSTRUCTION_AND_DRIVE_DOWNLOAD` — not a historical authenticity PASS.
- `claim_allowed=false`.
- 8 ASCII file bodies captured via GitHub connector at fixed SHA refs, transported in a private Base64 document, decoded and SHA-256 checked per file.
- Offline ZIP contains 8 reconstructed source files, `manifest.json`, `README.md`; ZIP contents CRC checked and internal SHA-256 verified.
- Zip byte length: **10,550**.
- SHA-256 of ZIP: `3b5c1a157068ec950c9c796d82d598ada2a69711f051f9a2a82331db0758c4de`.
- SHA-256 of `manifest.json` source file: `8cdc5ff0dc0bb0cd1aeae6c66058f32858e4e0688e1dda0f2e75a9f65b1d6e59`.
- Storage: private Google Drive custody folder. Initial upload acknowledged; provider folder listing confirmed private ZIP metadata, and fresh raw-file download matched the ZIP SHA-256 exactly. No public Drive link is exposed in this public repository.
- Supabase private continuity S1: `MU-WAYBACK-SNEVES-TEXT-20261114-S1`; S2 to be indexed separately.
- alphaXiv: its available interface catalogs papers/arXiv items, not web page snapshots, so no claim of alphaXiv content upload.

Historical mirror state: `WAYBACK_CDX_NOT_RETRIEVED`; `SOFTWARE_HERITAGE_VISIT_NOT_RETRIEVED`; `GH_ARCHIVE_2013_2014_EVENT_NOT_RETRIEVED`.

**Negative controls:** byte equality of 2026 GitHub connector text does not establish initial publication year, authorship, ownership, code copying, repository push chronology, or independent archive capture. A matching SHA-256 does not certify a capture timestamp. All evidence stays review only.

F_next: retrieve an independent archive-owned timestamp plus content bytes, then compare exact file hashes and snapshots with source attribution.
