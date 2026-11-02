#include "../core/raf_html_indicators.h"
int main(void) {
  static const unsigned char sample[] = "<META name=keywords><FORM onsubmit=x><IMG src=x><a href=prodfto.asp><script src=x.inc>2005-12-15";
  struct raf_indicators r;
  if (raf_html_indicators(sample, sizeof(sample)-1, &r) != 0) return 1;
  if (r.meta != 1 || r.form != 1 || r.onsubmit != 1 || r.img != 1 || r.asp != 1 || r.inc != 1 || r.date_iso != 1) return 2;
  if (raf_html_indicators(0, 7, &r) == 0) return 3;
  if (raf_html_indicators(sample, 1048577, &r) == 0) return 4;
  return 0;
}
