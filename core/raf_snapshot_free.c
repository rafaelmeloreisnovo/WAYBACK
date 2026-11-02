#include "raf_snapshot_free.h"
#include "raf_evidence_v2.h"
#include "raf_sha256_free.h"
int raf_snapshot_bytes(const unsigned char *html,unsigned int n,
                       struct raf_snapshot *out) {
  struct raf_snapshot t = {0};
  struct raf_html_event e;
  unsigned int cursor=0U;
  int r;
  if(!html||!out||n>1048576U)return -1;
  if(raf_sha256_free(html,n,t.raw_sha256)!=0)return -1;
  while((r=raf_html_next(html,n,&cursor,&e))>0) {
    if(e.flags&RAF_F_ENDTAG)continue;
    ++t.tags;
    if(e.kind==RAF_EV_META) {
      ++t.meta;
      if(e.flags&RAF_F_KEYWORDS){
        ++t.keywords;
        if(!t.has_keywords){
          if(e.value.end<e.value.begin||e.value.end>n)return -2;
          if(raf_sha256_free(html+e.value.begin,
                             e.value.end-e.value.begin,
                             t.first_keywords_sha256)!=0)return -2;
          t.has_keywords=1U;
        }
      }
      if(e.flags&RAF_F_DESCRIPTION)++t.description;
    } else if(e.kind==RAF_EV_LINK){
      ++t.links;
      if(!t.has_link){
        if(e.value.end<e.value.begin||e.value.end>n)return -2;
        if(raf_sha256_free(html+e.value.begin,
                           e.value.end-e.value.begin,
                           t.first_link_sha256)!=0)return -2;
        t.has_link=1U;
      }
    } else if(e.kind==RAF_EV_IMAGE)++t.images;
    else if(e.kind==RAF_EV_FORM){
      ++t.forms;
      if(e.flags&RAF_F_POST)++t.post_forms;
      if(e.flags&RAF_F_GET)++t.get_forms;
      if(e.flags&RAF_F_ONSUBMIT)++t.onsubmit_forms;
    } else if(e.kind==RAF_EV_SCRIPT)++t.scripts;
    else if(e.kind==RAF_EV_COMMENT)++t.comments;
    if(e.flags&RAF_F_ASP)++t.asp_refs;
    if(e.flags&RAF_F_INC)++t.inc_refs;
  }
  if(r<0)return r;
  *out=t;
  return 0;
}
