/* RAFAELIA WAYBACK: caller-owned, freestanding HTML snapshot digest V1.
 * Source boundary: archived HTTP replay bytes, not server ASP source or WARC.
 * No libc/malloc/network/filesystem. The host handles transport and privacy.
 * SHA-256 is NIST FIPS 180-4; the local C implementation is not a novel cipher.
 */
#ifndef RAF_SNAPSHOT_FREE_H
#define RAF_SNAPSHOT_FREE_H
struct raf_snapshot {
  unsigned char raw_sha256[32];
  unsigned char first_keywords_sha256[32];
  unsigned char first_link_sha256[32];
  unsigned int has_keywords, has_link;
  unsigned int tags, meta, keywords, description;
  unsigned int links, images, forms, scripts, comments;
  unsigned int post_forms, get_forms, onsubmit_forms, asp_refs, inc_refs;
};
/* 0 success; -1 invalid bounds/ptr; -2 malformed HTML token.
 * Output is unchanged on failure. No raw content retained in result.
 */
int raf_snapshot_bytes(const unsigned char *html, unsigned int n,
                       struct raf_snapshot *out);
#endif
