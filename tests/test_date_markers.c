#include "../core/raf_date_markers.h"
#include <stdio.h> /* HOST TEST ONLY */
#define T(x) do {if(!(x)){printf("DATE_MARKER_TEST_FAIL=%u\n",(unsigned)__LINE__);return 1;}}while(0)
int main(void){
 static const unsigned char p[]="news-2008-02-29 | foto_20080229.jpg | 29/02/2008 | 2008/03/02 | 20090229 | 20080807120000 | 2026-11-02";
 struct raf_date_marker z,w;unsigned int cur=0U;int n=0,r;
 static const unsigned int expected[]={20080229U,20080229U,20080229U,20080302U,20261102U};
 while((r=raf_next_date(p,(unsigned int)sizeof(p)-1U,&cur,&z))==1){
   T(n<5);T(z.yyyymmdd==expected[n]);++n;
 }
 T(r==0);T(n==5);
 w.yyyymmdd=12345U;cur=0U;
 T(raf_next_date((const unsigned char *)0,20U,&cur,&w)==-1);
 T(w.yyyymmdd==12345U&&cur==0U);
 T(raf_next_date(p,1048577U,&cur,&w)==-1);
 T(w.yyyymmdd==12345U);
 return 0;
}
