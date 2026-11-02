# WAYBACK — Evidence Router V1

Status: DRAFT/HOLD. SOURCE != ARTIFACT != EXECUTION != EVIDENCE != CLAIM.

The WAYBACK repo is a producer candidate of a new bounded, read-only experiment, NOT the Internet Archive, BLAKE3-team, RMR or Gradle Actions.

Reconstruction:
1. Read README.md + governance/GATES.md; load only one scoped receipt at a time.
2. Inspect one allowlisted root, no automatic crawl, no form submission or login.
3. Capture HTTP status, observation time, bytes size, SHA256/SHA3-256, HTML navigation shapes, unverified headers.
4. To compare, supply the previous receipt with its SHA256SUMS: BYTE_CHANGED only when two comparable response bodies exist. Never overwrite a historical receipt.
5. Browser-rendered HTML does NOT expose original server-side ASP or .inc. Unknown dates, prodfto.asp bytes, copyright, sources and authorization are TOKEN_VAZIO.
6. RMR BLAKE3 provider is not integrated: TOKEN_VAZIO_NOT_EXECUTED, never pretend SHA256 is BLAKE3.
7. CI is offline synthetic. A public GET is separately opt-in using workflow_dispatch. No schedule, no main promotion.

The initial public repo was empty. This isolated experiment is a draft for review. Rights to this authorial delta are pending an explicit license choice. Closing the PR, retaining historic receipts, is the smallest rollback.
