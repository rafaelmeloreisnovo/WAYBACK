#include "../core/raf_snapshot_free.h"
#include <stdio.h> /* hosted TEST harness only */
static const unsigned char a[] =
 "<html><head><meta name='keywords' content='Canon,copiadora'>"
 "<meta name='description' content='site 2003'></head><body>"
 "<!-- historical fixture not from Wayback -->"
 "<a href='/telas/prodfto.asp'>Fotos</a><img src='foto.jpg'>"
 "<form action='/busca.asp' method='get' onsubmit='return ok()'></form>"
 "<script src='legacy.inc'></script></body></html>";
static const unsigned char b[] =
 "<html><head><meta name='keywords' content='Canon,impressora'>"
 "<meta name='description' content='site 2003'></head><body>"
 "<!-- historical fixture not from Wayback -->"
 "<a href='/telas/prodfto.asp'>Fotos</a><img src='foto.jpg'>"
 "<form action='/busca.asp' method='get' onsubmit='return ok()'></form>"
 "<script src='legacy.inc'></script></body></html>";
static int different(const unsigned char *x,const unsigned char *y) {
  unsigned int i;
  for(i=0U;i<32U;++i)if(x[i]!=y[i])return 1;
  return 0;
}
#define CHECK(x) do {if(!(x)){printf("SNAPSHOT_FAIL_LINE=%u\n",(unsigned)__LINE__);return 1;}}while(0)
int main(void) {
  struct raf_snapshot x,y,keep;
  unsigned int i;
  static const unsigned char bad[]="<meta name='keywords' content='unfinished";
  CHECK(raf_snapshot_bytes(a,(unsigned int)sizeof(a)-1U,&x)==0);
  CHECK(raf_snapshot_bytes(b,(unsigned int)sizeof(b)-1U,&y)==0);
  CHECK(different(x.raw_sha256,y.raw_sha256));
  CHECK(different(x.first_keywords_sha256,y.first_keywords_sha256));
  CHECK(!different(x.first_link_sha256,y.first_link_sha256));
  CHECK(x.has_keywords==1U && x.keywords==1U && x.description==1U);
  CHECK(x.links==1U && x.images==1U && x.forms==1U);
  CHECK(x.get_forms==1U && x.post_forms==0U && x.onsubmit_forms==1U);
  CHECK(x.comments==1U && x.scripts==1U && x.asp_refs==2U && x.inc_refs==1U);
  keep=x;
  CHECK(raf_snapshot_bytes(bad,(unsigned int)sizeof(bad)-1U,&x)==-2);
  for(i=0U;i<32U;++i)CHECK(x.raw_sha256[i]==keep.raw_sha256[i]);
  CHECK(x.links==keep.links);
  CHECK(raf_snapshot_bytes(a,1048577U,&x)==-1);
  CHECK(raf_snapshot_bytes((const unsigned char *)0,0U,&x)==-1);
  return 0;
}
