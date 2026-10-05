#ifndef TAS_EMOTE_WIRE_H
#define TAS_EMOTE_WIRE_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
/* Bounded container inspection, not pixel decoding. No input is retained. */
typedef struct { const char *kind; int frames,animated; bool complete; } TASWireInfo;
static inline uint32_t tas_wire_u32(const unsigned char *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static inline bool tas_wire_blocks(const unsigned char *b,size_t n,size_t *p) {
    while (*p<n) { unsigned size=b[(*p)++];if (!size) return true;if (size>n-*p) return false;*p+=size; }
    return false;
}
static inline TASWireInfo tas_wire_info(const void *bytes,size_t n) {
    TASWireInfo r={"other",-1,-1,false};const unsigned char *b=bytes;
    if (!b) return r;
    if (n>=6 && (!memcmp(b,"GIF87a",6) || !memcmp(b,"GIF89a",6))) {
        r.kind="GIF";if (n<13) return r;
        size_t p=13,table=(b[10]&128) ? 3U<<(1+(b[10]&7)) : 0;int frames=0;
        if (table>n-p) return r;
        p+=table;
        while (p<n) {
            unsigned tag=b[p++];
            if (tag==0x3b) { r.frames=frames;r.animated=frames>1;r.complete=p==n;return r; }
            if (tag==0x21) { if (p==n) return r;p++;if (!tas_wire_blocks(b,n,&p)) return r; }
            else if (tag==0x2c) {
                if (n-p<9) return r;
                table=(b[p+8]&128) ? 3U<<(1+(b[p+8]&7)) : 0;p+=9;
                if (table>n-p) return r;
                p+=table;if (p==n) return r;p++;
                if (!tas_wire_blocks(b,n,&p)) return r;
                frames++;
            } else return r;
        }
    } else if (n>=12 && !memcmp(b,"RIFF",4) && !memcmp(b+8,"WEBP",4)) {
        r.kind="WebP";uint64_t end=(uint64_t)tas_wire_u32(b+4)+8;if (end!=n) return r;
        size_t p=12;int frames=0;bool still=false,anim=false,flag=false;
        while (p<n) {
            if (n-p<8) return r;
            uint32_t size=tas_wire_u32(b+p+4);const unsigned char *tag=b+p;p+=8;
            uint64_t padded=(uint64_t)size+(size&1);if (padded>n-p) return r;
            if (!memcmp(tag,"ANMF",4)) { if (size<16) return r;frames++; }
            else if (!memcmp(tag,"ANIM",4)) { if (size!=6) return r;anim=true; }
            else if (!memcmp(tag,"VP8X",4)) { if (size!=10) return r;flag=(b[p]&2)!=0; }
            else if (!memcmp(tag,"VP8 ",4) || !memcmp(tag,"VP8L",4)) still|=size>0;
            p+=(size_t)padded;
        }
        if (frames && anim && flag && !still) { r.frames=frames;r.animated=1;r.complete=true; }
        else if (!frames && !anim && !flag && still) { r.frames=1;r.animated=0;r.complete=true; }
    }
    return r;
}
#endif
