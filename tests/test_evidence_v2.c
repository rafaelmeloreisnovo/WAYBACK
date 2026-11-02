#include "../core/raf_evidence_v2.h"
static int errors=0;
static void ck(int x){if(!x)++errors;}
static int match(const unsigned char *p,struct raf_span s,const char *t) {
  unsigned int i=0U;
  while(t[i]) {if(s.begin+i>=s.end||p[s.begin+i]!=(unsigned char)t[i])return 0;++i;}
  return s.begin+i==s.end;
}
int main(void){
  static const unsigned char html[]=
    "<html><!-- <form method='post'> fake --><head>"
    "<meta name='keywords' content='Canon, fotograFIA, impressora'>"
    "<META content=\"Catalogo\" name=\"description\">"
    "</head><body><a href='/telas/prodfto.asp?Grupo=A'>Fotos</a>"
    "<img src='2023.png'><form method='POST' action='/consulta.asp' "
    "onsubmit='return valida(2>1);'></form>"
    "<link href='estilo.css'><script src='base.inc'></script></body></html>";
  unsigned int cur=0U,links=0U,kw=0U,comments=0U,images=0U,forms=0U,inc=0U;
  int r;
  struct raf_html_event e,before;
  struct raf_time_match tm;
  while((r=raf_html_next(html,(unsigned int)(sizeof(html)-1U),&cur,&e))==1) {
    if(e.kind==RAF_EV_LINK){++links;ck((e.flags&RAF_F_ASP)!=0U);ck(match(html,e.value,"/telas/prodfto.asp?Grupo=A"));}
    if(e.kind==RAF_EV_META&&(e.flags&RAF_F_KEYWORDS)){++kw;ck(match(html,e.value,"Canon, fotograFIA, impressora"));}
    if(e.kind==RAF_EV_COMMENT)++comments;
    if(e.kind==RAF_EV_IMAGE)++images;
    if(e.kind==RAF_EV_FORM){++forms;ck((e.flags&(RAF_F_ONSUBMIT|RAF_F_POST|RAF_F_ASP))==(RAF_F_ONSUBMIT|RAF_F_POST|RAF_F_ASP));}
    if(e.flags&RAF_F_INC)++inc;
  }
  ck(r==0);ck(links==1U&&kw==1U&&comments==1U&&images==1U&&forms==1U&&inc==1U);
  ck(raf_stamp_compare((const unsigned char *)"20030721165004",
      (const unsigned char *)"20051221165008",60U,&tm)==0);
  ck(tm.month_apart_clock_match==1U&&tm.within_window==0U&&tm.same_clock_minute==1U);
  ck(raf_stamp_compare((const unsigned char *)"20261101060000",
      (const unsigned char *)"20261101060058",60U,&tm)==0);
  ck(tm.within_window==1U);
  ck(raf_stamp_compare((const unsigned char *)"20030229000000",
      (const unsigned char *)"20051221165008",60U,&tm)<0);
  before.kind=199U;
  ck(raf_html_next((const unsigned char *)"<meta content='unterminated",
      27U,&cur,&before)<0); /* invalid cursor (old >n) is fail closed */
  ck(before.kind==199U);
  return errors?1:0;
}
