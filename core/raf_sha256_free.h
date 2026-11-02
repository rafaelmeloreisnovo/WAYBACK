/* SHA-256 (FIPS 180-4) freestanding one-shot implementation.
 * Original local implementation; algorithm standard is NIST, not an
 * original cryptographic algorithm. Caller-owned input/output only.
 * n<=1048576; no libc, malloc, heap, IO, syscalls or undefined symbols.
 * This is integrity hashing, not signature, consent or WARC certification.
 */
#ifndef RAF_SHA256_FREE_H
#define RAF_SHA256_FREE_H
/* 0 success; -1 invalid pointer or size. Out unmodified on failure. */
int raf_sha256_free(const unsigned char *in, unsigned int n,
                    unsigned char out32[32]);
#endif
