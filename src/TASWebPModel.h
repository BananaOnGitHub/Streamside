#ifndef TAS_WEBP_MODEL_H
#define TAS_WEBP_MODEL_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define TAS_WEBP_MAX_FRAMES 2048U
#define TAS_WEBP_MAX_BYTES (8U*1024U*1024U)
#define TAS_WEBP_MAX_PIXELS 524288U
typedef struct { unsigned width,height,count; uint32_t delay_ms[TAS_WEBP_MAX_FRAMES]; } TASWebPInfo;
static inline uint32_t tas_webp_u24(const unsigned char *p) {return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16;}
static inline uint32_t tas_webp_u32(const unsigned char *p) {return tas_webp_u24(p)|(uint32_t)p[3]<<24;}
static inline int tas_webp_header(const unsigned char *p,size_t n) {return p && n>=12 && !memcmp(p,"RIFF",4) && !memcmp(p+8,"WEBP",4);}
/* Validate the container and animation rectangles before invoking ImageIO.
 * Pixels, blending and disposal remain the system decoder's responsibility. */
static inline int tas_webp_info(const unsigned char *p,size_t n,TASWebPInfo *out) {
    if(!out || !tas_webp_header(p,n) || n>TAS_WEBP_MAX_BYTES || (uint64_t)tas_webp_u32(p+4)+8!=n)return 0;
    TASWebPInfo info={0};unsigned animated=0,anim=0,still=0;size_t at=12;
    while(at+8<=n) {
        const unsigned char *tag=p+at;size_t bytes=tas_webp_u32(p+at+4);at+=8;
        if(bytes>n-at || (bytes+(bytes&1))>n-at)return 0;
        const unsigned char *v=p+at;
        if(!memcmp(tag,"VP8X",4)) {
            if(bytes!=10 || info.width || at!=20 || (v[0]&0xc1))return 0;
            info.width=tas_webp_u24(v+4)+1;info.height=tas_webp_u24(v+7)+1;animated=v[0]&2;
        } else if(!memcmp(tag,"ANIM",4)) {
            if(bytes!=6 || !animated || anim++ || info.count)return 0;
        } else if(!memcmp(tag,"ANMF",4)) {
            if(!animated || !anim || bytes<24 || info.count>=TAS_WEBP_MAX_FRAMES || (v[15]&~3U))return 0;
            uint32_t x=2*tas_webp_u24(v),y=2*tas_webp_u24(v+3),w=1+tas_webp_u24(v+6),h=1+tas_webp_u24(v+9);
            if(x>info.width || y>info.height || w>info.width-x || h>info.height-y)return 0;
            size_t sub=16;unsigned images=0,alpha=0;
            while(sub+8<=bytes) {
                size_t len=tas_webp_u32(v+sub+4);const unsigned char *kind=v+sub;sub+=8;
                if(len>bytes-sub || len+(len&1)>bytes-sub)return 0;
                if(!memcmp(kind,"ALPH",4)){if(alpha++ || images || !len)return 0;}
                else if(!memcmp(kind,"VP8 ",4) || !memcmp(kind,"VP8L",4)){
                    if(images++)return 0;
                    const unsigned char *bits=v+sub;uint32_t bw=0,bh=0;
                    if(!memcmp(kind,"VP8 ",4)){
                        if(len<10 || (bits[0]&1) || memcmp(bits+3,"\x9d\x01\x2a",3))return 0;
                        bw=(bits[6]|(uint32_t)bits[7]<<8)&0x3fff;bh=(bits[8]|(uint32_t)bits[9]<<8)&0x3fff;
                    } else {
                        if(len<5 || bits[0]!=0x2f || (bits[4]&0xe0) || alpha)return 0;
                        uint32_t packed=tas_webp_u32(bits+1);bw=1+(packed&0x3fff);bh=1+((packed>>14)&0x3fff);
                    }
                    if(bw!=w || bh!=h)return 0;
                }
                else return 0;
                sub+=len+(len&1);
            }
            if(sub!=bytes || images!=1)return 0;
            uint32_t delay=tas_webp_u24(v+12);info.delay_ms[info.count++]=delay<=10?100:delay<20?20:delay;
        } else if(!memcmp(tag,"VP8 ",4) || !memcmp(tag,"VP8L",4)) {
            if(animated || still++)return 0;
            if(!info.width && !memcmp(tag,"VP8 ",4) && bytes>=10 && !memcmp(v+3,"\x9d\x01\x2a",3)) {
                info.width=(v[6]|(unsigned)v[7]<<8)&0x3fff;info.height=(v[8]|(unsigned)v[9]<<8)&0x3fff;
            } else if(!info.width && !memcmp(tag,"VP8L",4) && bytes>=5 && v[0]==0x2f) {
                info.width=1+((v[1]|(unsigned)v[2]<<8)&0x3fff);info.height=1+(((unsigned)v[2]>>6|(unsigned)v[3]<<2|(unsigned)v[4]<<10)&0x3fff);
            }
        }
        at+=bytes+(bytes&1);
    }
    if(at!=n || !info.width || !info.height || info.width>4096 || info.height>4096 ||
       (uint64_t)info.width*info.height>TAS_WEBP_MAX_PIXELS || (animated?(!anim || info.count<2):!still))return 0;
    if(!animated)info.count=1;
    *out=info;return 1;
}
#endif
