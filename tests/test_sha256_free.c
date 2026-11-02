#include "../core/raf_sha256_free.h"
#include <stdio.h> /* Hosted test harness ONLY */
static const char hx[]="0123456789abcdef";
static int eqhex(const unsigned char *x,const char *v){
  unsigned int i;
  for(i=0U;i<32U;++i)if(hx[x[i]>>4]!=v[i*2U]||
     hx[x[i]&15U]!=v[i*2U+1U])return 0;
  return v[64]==0;
}
static int check(const unsigned char *p,unsigned int n,const char *expected,const char *label){
  unsigned char out[32];
  if(raf_sha256_free(p,n,out)!=0||!eqhex(out,expected)) {
    printf("SHA256_KAT_FAIL=%s n=%u\n",label,n);return 1;
  }
  return 0;
}
int main(void){
  unsigned char b[1000],out[32],sentinel=0x55U;
  unsigned int i;
  for(i=0U;i<1000U;++i)b[i]='a';
  if(check(b,0U,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","empty"))return 1;
  if(check((const unsigned char *)"abc",3U,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","abc"))return 1;
  if(check(b,55U,"9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318","55"))return 1;
  if(check(b,56U,"b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a","56"))return 1;
  if(check(b,64U,"ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb","64"))return 1;
  if(check(b,1000U,"41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3","1000"))return 1;
  out[0]=sentinel;
  if(raf_sha256_free(b,1048577U,out)!=-1||out[0]!=sentinel)return 1;
  if(raf_sha256_free((const unsigned char *)0,0U,out)!=-1||out[0]!=sentinel)return 1;
  return 0;
}
