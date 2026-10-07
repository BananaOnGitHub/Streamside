#ifndef TAS_RN_COMPOSER_MODEL_H
#define TAS_RN_COMPOSER_MODEL_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
/* Check canvas, frame count and complete GIF block structure before asking the
 * lazy decoder to allocate. This parser never decompresses provider bytes. */
static inline unsigned tas_rn_composer_gif(const unsigned char *p,size_t n) {
    if (!p || n<14 || n>2*1024*1024 || (memcmp(p,"GIF87a",6) && memcmp(p,"GIF89a",6))) return 0;
    unsigned w=p[6]|p[7]<<8,h=p[8]|p[9]<<8,frames=0;
    if (!w || !h || w>4096 || h>4096 || (uint64_t)w*h>524288) return 0;
    size_t i=13;
    if (p[10]&128) i+=3u*(2u<<(p[10]&7));
    while (i<n) {
        unsigned tag=p[i++];
        if (tag==0x3b) return i==n && frames>1 ? frames : 0;
        if (tag==0x21) { if(i>=n)return 0;i++; }
        else if (tag==0x2c) {
            if (n-i<9 || ++frames>300) return 0;
            unsigned x=p[i]|p[i+1]<<8,y=p[i+2]|p[i+3]<<8;
            unsigned fw=p[i+4]|p[i+5]<<8,fh=p[i+6]|p[i+7]<<8,flags=p[i+8];i+=9;
            if (!fw || !fh || x+fw>w || y+fh>h) return 0;
            if (flags&128) i+=3u*(2u<<(flags&7));
            if (i>=n || p[i]<2 || p[i]>8) return 0;i++;
        } else return 0;
        for (;;) {
            if (i>=n) return 0;
            unsigned bytes=p[i++];if (!bytes) break;
            if (bytes>n-i) return 0;i+=bytes;
        }
    }
    return 0;
}
static inline double tas_rn_composer_delay(double delay) {
    return isfinite(delay) && delay>=0.01999999 ? delay : 0.1;
}
static inline double tas_rn_composer_delta(double now,double previous) {
    double delta=now-previous;
    return previous>0 && isfinite(delta) && delta>0 ? (delta>0.25 ? 0.25 : delta) : 0;
}
#endif
