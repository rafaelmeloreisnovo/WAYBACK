/* RAFAELIA WAYBACK V2: freestanding byte-source HTML/timeline evidence.
 * No libc, heap, syscall, IO, networking or external symbols.
 * Caller owns source bytes and offsets; returned spans are NOT redacted.
 * HTML fragments and timestamp correlation are indicators, NOT WARC authenticity,
 * JavaScript execution, server-side ASP source, authorship or causality.
 */
#ifndef RAF_EVIDENCE_V2_H
#define RAF_EVIDENCE_V2_H
struct raf_span { unsigned int begin, end; };
enum {
  RAF_EV_OTHER=1, RAF_EV_COMMENT, RAF_EV_LINK, RAF_EV_IMAGE,
  RAF_EV_FORM, RAF_EV_META, RAF_EV_SCRIPT, RAF_EV_RESOURCE
};
enum {
  RAF_F_KEYWORDS=1U, RAF_F_DESCRIPTION=2U, RAF_F_POST=4U,
  RAF_F_GET=8U, RAF_F_ONSUBMIT=16U, RAF_F_ASP=32U,
  RAF_F_INC=64U, RAF_F_ENDTAG=128U
};
struct raf_html_event {
  unsigned int kind, flags;
  struct raf_span tag, value, auxiliary;
};
/* ret 1 event, 0 end, -1 invalid arguments, -2 truncated/malformed tag.
 * On negative return, cursor and output are unchanged.
 * value is href/src/action/META content; auxiliary is FORM method/META name.
 */
int raf_html_next(const unsigned char *src, unsigned int n,
                  unsigned int *cursor, struct raf_html_event *out);
struct raf_time_match {
  unsigned long long gap_seconds;
  unsigned int within_window, same_clock_minute, month_apart_clock_match;
  unsigned int month_distance, same_calendar_day, exact_one_month;
};
/* UTC timestamps exactly YYYYMMDDhhmmss; 1970..2099. No offset parsing.
 * 0 on success; -1 on bad calendar/inputs without writing output.
 * Matching time-of-day across months is NOT evidence of a common actor.
 */
int raf_stamp_compare(const unsigned char *a14, const unsigned char *b14,
                      unsigned int window_seconds, struct raf_time_match *out);
#endif
