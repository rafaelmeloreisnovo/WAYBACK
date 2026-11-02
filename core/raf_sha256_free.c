#include "raf_sha256_free.h"
typedef char raf_u32_must_be_32_bits[(sizeof(unsigned int)==4U)?1:-1];
static const unsigned int k256[64]={
0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,0x923f82a4U,0xab1c5ed5U,
0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,
0xe49b69c1U,0xefbe4786U,0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,0x06ca6351U,0x14292967U,
0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,
0xa2bfe8a1U,0xa81a664bU,0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,0x5b9cca4fU,0x682e6ff3U,
0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U
};
static unsigned int rotr(unsigned int v,unsigned int n){return (v>>n)|(v<<(32U-n));}
static unsigned char padded(const unsigned char *p,unsigned int n,
                            unsigned int total,unsigned int pos) {
  unsigned int i;
  if(pos<n)return p[pos];
  if(pos==n)return 0x80U;
  if(pos<total-8U)return 0U;
  i=pos-(total-8U);
  if(i<4U)return 0U;
  return (unsigned char)(((n<<3U)>>((7U-i)*8U))&255U);
}
int raf_sha256_free(const unsigned char *p,unsigned int n,unsigned char out32[32]) {
  unsigned int h[8]={
    0x6a09e667U,0xbb67ae85U,0x3c6ef372U,0xa54ff53aU,
    0x510e527fU,0x9b05688cU,0x1f83d9abU,0x5be0cd19U
  };
  unsigned int w[64],total,blocks,block,i,j,word,a,b,c,d,e,f,g,q;
  unsigned int s0,s1,choice,majority,t1,t2;
  if(!p||!out32||n>1048576U)return -1;
  blocks=(n+72U)>>6U;
  total=blocks<<6U;
  for(block=0U;block<blocks;++block) {
    for(i=0U;i<16U;++i) {
      word=0U;
      for(j=0U;j<4U;++j) {
        word=(word<<8U)|(unsigned int)padded(p,n,total,block*64U+i*4U+j);
      }
      w[i]=word;
    }
    for(i=16U;i<64U;++i) {
      s0=rotr(w[i-15U],7U)^rotr(w[i-15U],18U)^(w[i-15U]>>3U);
      s1=rotr(w[i-2U],17U)^rotr(w[i-2U],19U)^(w[i-2U]>>10U);
      w[i]=w[i-16U]+s0+w[i-7U]+s1;
    }
    a=h[0];b=h[1];c=h[2];d=h[3];e=h[4];f=h[5];g=h[6];q=h[7];
    for(i=0U;i<64U;++i) {
      s1=rotr(e,6U)^rotr(e,11U)^rotr(e,25U);
      choice=(e&f)^(~e&g);
      t1=q+s1+choice+k256[i]+w[i];
      s0=rotr(a,2U)^rotr(a,13U)^rotr(a,22U);
      majority=(a&b)^(a&c)^(b&c);
      t2=s0+majority;
      q=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
    }
    h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;
    h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=q;
  }
  for(i=0U;i<8U;++i)for(j=0U;j<4U;++j)
    out32[i*4U+j]=(unsigned char)((h[i]>>((3U-j)*8U))&255U);
  return 0;
}
