/* RAFAELIA WAYBACK: byte-indicator scanner V1.
 * Freestanding C: no libc, malloc, heap, network, IO or crypto.
 * Indicators can occur in comments and JS; NOT DOM parsing or proof of form execution.
 * Authorial delta; license grant TOKEN_VAZIO, see README.
 */
#ifndef RAF_HTML_INDICATORS_H
#define RAF_HTML_INDICATORS_H
struct raf_indicators {
  unsigned int meta;
  unsigned int form;
  unsigned int onsubmit;
  unsigned int asp;
  unsigned int inc;
  unsigned int img;
  unsigned int date_iso;
};
/* Return 0 on success; negative on bad inputs or too large; no writes on error. */
int raf_html_indicators(const unsigned char *src, unsigned int n, struct raf_indicators *out);
#endif
