#include "raf_date_markers.h"
static int dig(unsigned char c){return c>='0'&&c<='9';}
static unsigned int read2(const unsigned char *p){return (unsigned int)(p[0]-'0')*10U+(unsigned int)(p[1]-'0');}
static unsigned int read4(const unsigned char *p){return read2(p)*100U+read2(p+2);}
static unsigned int leap(unsigned int y){return (y%4U)==0U&&((y%100U)!=0U||(y%400U)==0U);}
static unsigned int valid(unsigned int y,unsigned int m,unsigned int d){
  static const unsigned char days[12]={31,28,31,30,31,30,31,31,30,31,30,31};
  if(y<1990U||y>2099U||m<1U||m>12U||d<1U)return 0U;
  return d<=(unsigned int)days[m-1U]+(unsigned int)((m==2U)&&leap(y));
}
static int ymd(const unsigned char *p,unsigned int n,unsigned int i,
               unsigned int *y,unsigned int *m,unsigned int *d,
               unsigned int *len,unsigned int *style){
  unsigned int k;
  if(n-i>=10U){
    for(k=0;k<4U;++k)if(!dig(p[i+k]))break;
    if(k==4U&&(p[i+4U]=='-'||p[i+4U]=='/'||p[i+4U]=='_')&&p[i+7U]==p[i+4U]&&
       dig(p[i+5U])&&dig(p[i+6U])&&dig(p[i+8U])&&dig(p[i+9U])){
      *y=read4(p+i);*m=read2(p+i+5U);*d=read2(p+i+8U);
      *len=10U;*style=(p[i+4U]=='-')?RAF_DATE_ISO:\n         (p[i+4U]=='_')?RAF_DATE_UNDER_YMD:RAF_DATE_SLASH_YMD;
      return 1;
    }
    if(dig(p[i])&&dig(p[i+1U])&&(p[i+2U]=='/'||p[i+2U]=='-'||p[i+2U]=='_'||p[i+2U]=='.')&&\n       dig(p[i+3U])&&dig(p[i+4U])&&p[i+5U]==p[i+2U]&&dig(p[i+6U])&&dig(p[i+7U])&&dig(p[i+8U])&&dig(p[i+9U])){
      *y=read4(p+i+6U);*m=read2(p+i+3U);*d=read2(p+i);
      *len=10U;*style=(p[i+2U]=='/')?RAF_DATE_SLASH_DMY:\n        (p[i+2U]=='-')?RAF_DATE_DASH_DMY:\n        (p[i+2U]=='_')?RAF_DATE_UNDER_DMY:RAF_DATE_DOT_DMY;return 1;
    }
  }
  if(n-i>=8U){
    for(k=0U;k<8U;++k)if(!dig(p[i+k]))break;
    if(k==8U){
      *y=read4(p+i);*m=read2(p+i+4U);*d=read2(p+i+6U);
      *len=8U;*style=RAF_DATE_COMPACT_YMD;return 1;
    }
  }
  return 0;
}
int raf_next_date(const unsigned char *p,unsigned int n,unsigned int *cursor,
                  struct raf_date_marker *out){
  unsigned int i,y,m,d,len,style,mark;
  struct raf_date_marker next;
  if(!p||!cursor||!out||n>1048576U||*cursor>n)return -1;
  for(i=*cursor;i<n;++i){
    if(!dig(p[i]))continue;
    if(i&&dig(p[i-1U]))continue;
    if(!ymd(p,n,i,&y,&m,&d,&len,&style))continue;
    if(i+len<n&&dig(p[i+len]))continue;
    if(!valid(y,m,d))continue;
    mark=y*10000U+m*100U+d;
    next.begin=i;next.end=i+len;next.yyyymmdd=mark;next.notation=style;
    *out=next;*cursor=i+len;return 1;
  }
  *cursor=n;return 0;
}
