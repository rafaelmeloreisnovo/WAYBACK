# WAYBACK — Evidence chain and safety contract v1
Observed 2026-11-01. Status: PROPOSAL, CLAIM_ALLOWED=false.

Sources: official Wayback is third party; public roots Reis Office, Cesar Reis and GeoCities.ws Track/1665. These are NOT owned, monitored or certified by this repo.

Chain: source URL scope -> HTTP outcome -> observed response bytes -> SHA256 + SHA3-256 -> redacted HTML indicator shapes -> receipt SHA256 + run ID -> optional prior receipt comparison -> human legal/security review -> external trusted timestamp/anchor (NOT IMPLEMENTED).

The uploaded screenshot visually displays the Internet Archive counter “Saved 400 times between October 29, 2005 and September 1, 2026” for www.reisoffice.com.br. It is USER_SUPPLIED_SCREENSHOT_EVIDENCE, not independently fetched CDX, evidence of authorship or proof that historic pages used BLAKE3. Other screenshots of Android version/status, ChatGPT UI and another agent's claimed GitHub dates do not authenticate site source code.

Hypotheses: same HTML/ASP skeleton through 2018 (user statement), prodfto.asp path, BLAKE3 encounter after Zenodo/CERNE app fork. These require independent timestamps, old/new byte-level comparison, fork/commit provenance and rights checks. A BLAKE3 digest made after 2020 does not prove that a 2005 site employed BLAKE3.

Freestanding core/raf_html_indicators.c is C99 without libc, malloc or syscalls. It counts byte-pattern indicators, NOT a W3C DOM parser; source strings can be comments or JS. Hosted Python adapter uses stdlib TLS/HTTP/HTMLParser/hashlib; network, crypto, filesystem are explicit hosted boundaries and not freestanding.

Cross compiling x86_64/ARMv7/AArch64 objects tests freestanding build and undefined symbols, NOT physical ARM execution. SHA-256 and SHA3-256 originate from hosted Python hashlib. BLAKE3 via rafaelmeloreisnovo/BLAKE3 RMR portable at observed source SHA 365516a302f23f94c538c3a27e3d26e3d294098e is a potential separately approved integration. Actual BLAKE3 digest=TOKEN_VAZIO_NOT_EXECUTED; KAT, provider executable hash and independent parity=NOT_RUN. No copied RMR code or implied shared license.

The workflow takes its read-only collector / publisher segregation philosophy from rafaelmeloreisnovo/actions evidence-registry.yml, itself a fork of Gradle Actions with upstream rights retained. GitHub Actions runner, official checkout action and upload-artifact are third-party hosted services; SHA pins do not imply authorial ownership.

Default: no network on PR, read-only permission, no cron. Manual live mode checks an exact hardcoded HTTPS allowlist, rejects credentials and arbitrary paths, redirects and params, fetches only one URL, caps at 1 MiB, no form submission, login, JavaScript or recursion. Legal/robots and copyright scope still need human review. No page bodies or screenshots publicly uploaded: only hashes, structural counts and redacted shapes. HTML keyword and title values suppressed, query parameter values suppressed.

Receipt append-only rule: unique output directory must not exist, use exclusive create and own SHA256SUMS, no overwrite. This sidecar is NOT an independent trusted time anchor. GitHub Actions artifacts expire after 90 days and need separate long-term custody.

Required negative tests: unsupported/off-allowlist addresses, credential URL, malformed data, missing/modified prior receipt, mismatch across source, POST parsing not submitting, no secret emitted, byte identity/change, C compile and host test. In a failed external fetch, event is FETCH_BLOCKED_NOT_ZERO and no body checksum exists; missing is not zero.

Review requires owner, legal basis, privacy/children assessment, access policy, rights of historical content, exact HEAD CI, external time anchor and repeatable CLI. Approval to investigate does NOT grant release or copyrighted source redistribution. LGPD, ECA Digital and potentially GDPR require competent legal interpretation; certification not claimed.

STOP at DRAFT/HOLD until human review. ROLLBACK: close draft without merge, retain historical source/receipts; no destructive changes. TERMINAL: synthetic PASS + exact hashes of files, no historical source claims.
