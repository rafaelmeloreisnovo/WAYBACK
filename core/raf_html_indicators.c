#include "raf_html_indicators.h"
static unsigned char fold(unsigned char c) {
  return (c >= (unsigned char)'A' && c <= (unsigned char)'Z') ? (unsigned char)(c + 32U) : c;
}
static int match(const unsigned char *p, unsigned int n, unsigned int i,
                 const char *word, unsigned int wn) {
  unsigned int j;
  if (wn > n || i > n - wn) return 0;
  for (j = 0; j < wn; ++j) if (fold(p[i + j]) != (unsigned char)word[j]) return 0;
  return 1;
}
static int digit(unsigned char c) { return c >= '0' && c <= '9'; }
int raf_html_indicators(const unsigned char *p, unsigned int n, struct raf_indicators *out) {
  struct raf_indicators x = {0, 0, 0, 0, 0, 0, 0};
  unsigned int i;
  if (!p || !out || n > 1048576U) return -1;
  for (i = 0; i < n; ++i) {
    x.meta += (unsigned int)match(p, n, i, "<meta", 5);
    x.form += (unsigned int)match(p, n, i, "<form", 5);
    x.onsubmit += (unsigned int)match(p, n, i, "onsubmit", 8);
    x.asp += (unsigned int)match(p, n, i, ".asp", 4);
    x.inc += (unsigned int)match(p, n, i, ".inc", 4);
    x.img += (unsigned int)match(p, n, i, "<img", 4);
    if (i + 10 <= n && digit(p[i]) && digit(p[i+1]) && digit(p[i+2]) &&
        digit(p[i+3]) && p[i+4] == '-' && digit(p[i+5]) && digit(p[i+6]) &&
        p[i+7] == '-' && digit(p[i+8]) && digit(p[i+9])) ++x.date_iso;
  }
  *out = x;
  return 0;
}
