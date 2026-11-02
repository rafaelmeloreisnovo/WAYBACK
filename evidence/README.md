# Append-only evidence manifest

No public raw pages or screenshots. Each CI job emits unique artifact name based on run_id/run_attempt containing:
- receipt.json and SHA256SUMS from a single completed/blocked observation
- kind SYNTHETIC_ONLY / OBSERVED_HTTP_BYTES / FETCH_BLOCKED_NOT_ZERO
- raw_body_sha256/raw_body_sha3_256 only for available body bytes
- byte comparison BYTE_CHANGED/BYTE_IDENTICAL/TOKEN_VAZIO_NO_PREVIOUS
- BLAKE3 TOKEN_VAZIO_NOT_EXECUTED
- source URL fingerprint, method/keyword indicator shape with content redacted
- previous receipt checksum, never a purported independent time anchor.

On a fresh local run:
python3 -m unittest discover -s tests -p test_wayback.py -v
python3 host/observe.py --mode synthetic --output /tmp/wb-run-0001
(cd /tmp/wb-run-0001 && sha256sum -c SHA256SUMS)

On a second run use --previous-receipt /tmp/wb-run-0001/receipt.json and a *new* output path, then review both receipts. A GitHub artifact expires after 90 days. Long-term retention/signature/third-party public preservation is a human-approved follow-on.
