#include "raf_evidence_v2.h"
#define RAF_MAX (1048576U)
static int ws(unsigned char c) { return c==9U||c==10U||c==12U||c==13U||c==32U; }
static unsigned char lc(unsigned char c) {
  return (c>=65U&&c<=90U)?(unsigned char)(c+32U):c;
}
static int eq(const unsigned char *p, unsigned int a, unsigned int b, const char *s) {
  unsigned int i=0U;
  while(s[i]) {
    if(a+i>=b||lc(p[a+i])!=(unsigned char)s[i]) return 0;
    ++i;
  }
  return a+i==b;
}
static int has(const unsigned char *p, struct raf_span s, const char *word) {
  unsigned int i,j;
  for(i=s.begin;i<s.end;++i) {
    for(j=0U;word[j]&&i+j<s.end&&lc(p[i+j])==(unsigned char)word[j];++j){}
    if(!word[j])return 1;
  }
  return 0;
}
/* Attributes are parsed within one quote-aware tag. End offsets are exclusive. */
static int attr(const unsigned char *p, unsigned int begin, unsigned int end,
                const char *key, struct raf_span *v) {
  unsigned int i=begin,a,b,q;
  while(i<end) {
    while(i<end&&(ws(p[i])||p[i]=='/'))++i;
    if(i>=end||p[i]=='>')break;
    a=i;
    while(i<end&&!ws(p[i])&&p[i]!='='&&p[i]!='>'&&p[i]!='/')++i;
    b=i;
    if(b==a){++i;continue;}
    while(i<end&&ws(p[i]))++i;
    if(i>=end||p[i]!='=')continue;
    ++i;
    while(i<end&&ws(p[i]))++i;
    if(i>=end)return -2;
    if(p[i]=='"'||p[i]=='\'') {
      q=p[i++];
      v->begin=i;
      while(i<end&&p[i]!=q)++i;
      if(i>=end)return -2;
      v->end=i++;
    } else {
      v->begin=i;
      while(i<end&&!ws(p[i])&&p[i]!='>')++i;
      v->end=i;
    }
    if(eq(p,a,b,key))return 1;
  }
  v->begin=0U;v->end=0U;
  return 0;
}
int raf_html_next(const unsigned char *src,unsigned int n,
                  unsigned int *cursor,struct raf_html_event *out) {
  unsigned int i,j,k,q=0U,closing=0U,flags=0U,tagname,kind=RAF_EV_OTHER;
  struct raf_html_event e;
  struct raf_span v={0U,0U},aux={0U,0U},name={0U,0U};
  int ok;
  if(!src||!cursor||!out||n>RAF_MAX||*cursor>n)return -1;
  i=*cursor;
  while(i<n&&src[i]!='<')++i;
  if(i==n){*cursor=n;return 0;}
  if(i+3U<n&&src[i+1U]=='!'&&src[i+2U]=='-'&&src[i+3U]=='-') {
    j=i+4U;
    while(j+2U<n) {
      if(src[j]=='-'&&src[j+1U]=='-'&&src[j+2U]=='>') {
        e.kind=RAF_EV_COMMENT;e.flags=0U;
        e.tag.begin=i;e.tag.end=j+3U;
        e.value.begin=i+4U;e.value.end=j;
        e.auxiliary.begin=0U;e.auxiliary.end=0U;
        *out=e;*cursor=j+3U;return 1;
      }
      ++j;
    }
    return -2;
  }
  j=i+1U;
  if(j<n&&src[j]=='/') {closing=1U;++j;}
  if(j<n&&(src[j]=='!'||src[j]=='?')) {
    /* Doctype/instructions are not markup events; still quote aware. */
    kind=RAF_EV_OTHER;
  }
  while(j<n&&ws(src[j]))++j;
  tagname=j;
  while(j<n&&((src[j]>='A'&&src[j]<='Z')||(src[j]>='a'&&src[j]<='z')||
                 (src[j]>='0'&&src[j]<='9')||src[j]=='-'||src[j]=='_'))++j;
  if(tagname==j) {
    /* Treat plain '<' inside text as non-tag to guarantee progress. */
    *cursor=i+1U;
    e.kind=RAF_EV_OTHER;e.flags=0U;
    e.tag.begin=i;e.tag.end=i+1U;
    e.value.begin=e.value.end=e.auxiliary.begin=e.auxiliary.end=0U;
    *out=e;return 1;
  }
  k=j;
  while(k<n) {
    if(q) { if(src[k]==q)q=0U; }
    else if(src[k]=='"'||src[k]=='\'')q=src[k];
    else if(src[k]=='>')break;
    ++k;
  }
  if(k==n||q)return -2;
  if(closing)flags|=RAF_F_ENDTAG;
  if(eq(src,tagname,j,"a"))kind=RAF_EV_LINK;
  else if(eq(src,tagname,j,"img"))kind=RAF_EV_IMAGE;
  else if(eq(src,tagname,j,"form"))kind=RAF_EV_FORM;
  else if(eq(src,tagname,j,"meta"))kind=RAF_EV_META;
  else if(eq(src,tagname,j,"script"))kind=RAF_EV_SCRIPT;
  else if(eq(src,tagname,j,"link"))kind=RAF_EV_RESOURCE;
  if(!closing) {
    const char *val_key=(kind==RAF_EV_LINK||kind==RAF_EV_RESOURCE)?"href":
             (kind==RAF_EV_IMAGE||kind==RAF_EV_SCRIPT)?"src":
             kind==RAF_EV_FORM?"action":kind==RAF_EV_META?"content":"";
    if(val_key[0]) {
      ok=attr(src,j,k,val_key,&v);
      if(ok<0)return -2;
    }
    if(kind==RAF_EV_FORM) {
      ok=attr(src,j,k,"method",&aux);
      if(ok<0)return -2;
      if(ok==0||eq(src,aux.begin,aux.end,"get"))flags|=RAF_F_GET;
      else if(eq(src,aux.begin,aux.end,"post"))flags|=RAF_F_POST;
      name.begin=name.end=0U;
      ok=attr(src,j,k,"onsubmit",&name);
      if(ok<0)return -2;
      if(ok>0)flags|=RAF_F_ONSUBMIT;
    }
    if(kind==RAF_EV_META) {
      ok=attr(src,j,k,"name",&aux);
      if(ok<0)return -2;
      if(ok>0&&eq(src,aux.begin,aux.end,"keywords"))flags|=RAF_F_KEYWORDS;
      if(ok>0&&eq(src,aux.begin,aux.end,"description"))flags|=RAF_F_DESCRIPTION;
    }
    if(v.end>v.begin) {
      if(has(src,v,".asp"))flags|=RAF_F_ASP;
      if(has(src,v,".inc"))flags|=RAF_F_INC;
    }
  }
  e.kind=kind;e.flags=flags;e.tag.begin=i;e.tag.end=k+1U;
  e.value=v;e.auxiliary=aux;
  *out=e;*cursor=k+1U;
  return 1;
}
static int leap(unsigned int y){return (y&3U)==0U;}
static unsigned int days_month(unsigned int m,unsigned int y) {
  static const unsigned char d[12]={31U,28U,31U,30U,31U,30U,31U,31U,30U,31U,30U,31U};
  if(!m||m>12U)return 0U;
  return (unsigned int)d[m-1U]+(m==2U&&(unsigned int)leap(y));
}
static int parse14(const unsigned char *p,unsigned long long *seconds,
                   unsigned int *year,unsigned int *month,unsigned int *day,unsigned int *tod) {
  unsigned int x[6]={0U,0U,0U,0U,0U,0U},lengths[6]={4U,2U,2U,2U,2U,2U};
  unsigned int i,j,k=0U,days=0U,y,m;
  if(!p)return -1;
  for(i=0U;i<6U;++i)for(j=0U;j<lengths[i];++j) {
    if(p[k]<'0'||p[k]>'9')return -1;
    x[i]=x[i]*10U+(unsigned int)(p[k++]-'0');
  }
  y=x[0];m=x[1];
  if(y<1970U||y>2099U||m<1U||m>12U||
     x[2]<1U||x[2]>days_month(m,y)||x[3]>23U||x[4]>59U||x[5]>59U)return -1;
  for(i=1970U;i<y;++i)days+=365U+(unsigned int)leap(i);
  for(i=1U;i<m;++i)days+=days_month(i,y);
  days+=x[2]-1U;
  *tod=x[3]*3600U+x[4]*60U+x[5];
  *seconds=(unsigned long long)days*86400ULL+(unsigned long long)*tod;
  *year=y;*month=m;*day=x[2];
  return 0;
}
int raf_stamp_compare(const unsigned char *a14,const unsigned char *b14,
                      unsigned int window_seconds,struct raf_time_match *out) {
  unsigned long long a,b,g;
  unsigned int ya,yb,ma,mb,da,db,ta,tb,diff,xa,xb;
  struct raf_time_match e;
  if(!a14||!b14||!out)return -1;
  if(parse14(a14,&a,&ya,&ma,&da,&ta)<0||parse14(b14,&b,&yb,&mb,&db,&tb)<0)return -1;
  g=a>=b?a-b:b-a;diff=ta>=tb?ta-tb:tb-ta;
  if(diff>43200U)diff=86400U-diff;
  e.gap_seconds=g;
  e.within_window=(g<=(unsigned long long)window_seconds);
  e.same_clock_minute=(diff<60U);
  e.month_apart_clock_match=(g>=2419200ULL&&diff<60U);
  xa=ya*12U+ma;xb=yb*12U+mb;
  e.month_distance=xa>=xb?xa-xb:xb-xa;
  e.same_calendar_day=(da==db);
  e.exact_one_month=(e.month_distance==1U&&e.same_calendar_day&&diff<60U);
  *out=e;
  return 0;
}
