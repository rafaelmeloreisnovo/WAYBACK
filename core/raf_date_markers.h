/* WAYBACK Ω historical date-token extraction (C99 freestanding).
 * No libc, malloc, heap, syscalls, file/network I/O or external symbols.
 * These are DATE LITERALS IN BYTES, not proof of photo creation or publication.
 */
#ifndef RAF_DATE_MARKERS_H
#define RAF_DATE_MARKERS_H
enum { RAF_DATE_ISO=1, RAF_DATE_SLASH_YMD=2,
       RAF_DATE_COMPACT_YMD=3, RAF_DATE_SLASH_DMY=4,
       RAF_DATE_UNDER_YMD=5, RAF_DATE_DASH_DMY=6,
       RAF_DATE_UNDER_DMY=7, RAF_DATE_DOT_DMY=8 };
struct raf_date_marker {
  unsigned int begin, end, yyyymmdd, notation;
};
/* 1=found; 0=end; -1=invalid argument. On negative return no writes.
 * Input capped at 1 MiB. Cursor advances monotonically, never loops.
 * Validate Gregorian years 1990..2099, reject embedded digit sequences.
 */
int raf_next_date(const unsigned char *src, unsigned int length,
                  unsigned int *cursor, struct raf_date_marker *out);
#endif
