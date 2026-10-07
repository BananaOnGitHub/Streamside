#ifndef TAS_RN_LOCAL_ECHO_PATCH_H
#define TAS_RN_LOCAL_ECHO_PATCH_H
#include "TASRNWidthPatch.h"

#define TAS_RN_LOCAL_INDEX 34307U
#define TAS_RN_LOCAL_OFFSET 25052014U
#define TAS_RN_LOCAL_SIZE 121U
#define TAS_RN_LOCAL_HEADER (128U + TAS_RN_LOCAL_INDEX * 12U)

/* LibraryTmiClient's completed ordinary-chat line, after native translation and nonce handling.
 * r4 (line) and r5 (client) remain intact. r1..r3/r6..r9 are dead Value registers.
 * Only own, non-shared lines call the separate module through NativeModules.
 * Native objects remain in JS: concatenate provider-only ranges to emotes.
 * Missing loader/module/method or a refused match leaves the line unchanged.
 */
static inline size_t tas_rn_local_code(unsigned char *out) {
    unsigned char *p=out, *jumps[8]; unsigned n=0;
#define LOCAL_BYTES(...) do { const unsigned char b[]={__VA_ARGS__}; memcpy(p,b,sizeof(b)); p+=sizeof(b); } while (0)
#define LOCAL_KEY(reg,key) LOCAL_BYTES(144,reg,(key)&255,(key)>>8)
#define LOCAL_FALSE(reg) do { jumps[n++]=p; LOCAL_BYTES(179,0,0,0,0,reg); } while (0)
    LOCAL_BYTES(137,6,1);                     /* LoadParam event */
    LOCAL_KEY(7,40125); LOCAL_BYTES(93,6,6,7); /* sentByCurrentUser */
    LOCAL_FALSE(6);
    LOCAL_KEY(7,59101); LOCAL_BYTES(93,6,4,7); /* sourceRoomID */
    jumps[n++]=p; LOCAL_BYTES(177,0,0,0,0,6); /* JmpTrueLong: shared scope */
    LOCAL_BYTES(61,6);                        /* global */
    LOCAL_KEY(7,18843); LOCAL_BYTES(93,7,6,7); /* __r */
    LOCAL_FALSE(7);
    LOCAL_BYTES(139,8,16,110,7,7,6,8);        /* require NativeModules */
    LOCAL_FALSE(7);
    LOCAL_KEY(9,110); LOCAL_BYTES(93,7,7,9);   /* default */
    LOCAL_FALSE(7);
    LOCAL_KEY(9,20058); LOCAL_BYTES(93,7,7,9); /* buildLocalEcho module */
    LOCAL_FALSE(7);
    LOCAL_BYTES(93,8,7,9);                    /* method */
    LOCAL_FALSE(8);
    LOCAL_KEY(9,80); LOCAL_BYTES(93,1,4,9);   /* body */
    LOCAL_KEY(9,90); LOCAL_BYTES(93,2,4,9);   /* channel */
    LOCAL_KEY(9,57438); LOCAL_BYTES(93,3,4,9);/* native emotes */
    LOCAL_BYTES(112,1,8,7,1,2,3);             /* method(body,channel,emotes) */
    LOCAL_FALSE(1);
    LOCAL_KEY(2,102); LOCAL_BYTES(93,2,3,2);  /* native emotes.concat */
    LOCAL_BYTES(110,1,2,3,1);                 /* concat(additions) */
    LOCAL_KEY(2,57438); LOCAL_BYTES(96,4,2,1);/* line.emotes only */
    for (unsigned i=0;i<n;i++) tas_rn_put32(jumps[i]+1,(uint32_t)(p-jumps[i]));
#undef LOCAL_FALSE
#undef LOCAL_KEY
#undef LOCAL_BYTES
    return (size_t)(p-out);
}

/* Accepts only the admitted width output. Append a new copy of function 34307,
 * widen its short null-return branch, then insert at the nonce-handling / emitLine join.
 * The nonce gate lands at the injection; null skips it entirely.
 */
static inline unsigned char *tas_rn_local_patch(const unsigned char *body,
        size_t length, TASRNSHA1 sha1, size_t *result_length) {
    static const unsigned char header[12]={0x6e,0x43,0x7e,5,0x79,0,0x3e,0x18,0x12,8,2,2};
    if (result_length) *result_length=0;
    if (!body || !sha1 || !result_length || length!=TAS_RN_BODY_SIZE+1207 ||
        tas_rn_u32(body+32)!=length || memcmp(body+TAS_RN_LOCAL_HEADER,header,12)) return NULL;
    unsigned char digest[20];
    if (!sha1(body,(uint32_t)length-20,digest) || memcmp(digest,body+length-20,20)) return NULL;
    unsigned char code[256]; size_t extra=tas_rn_local_code(code);
    size_t count=length+TAS_RN_LOCAL_SIZE+3+extra;
    unsigned char *copy=malloc(count);
    if (!copy) return NULL;
    memcpy(copy,body,length-20);
    unsigned char *fn=copy+length-20;
    memcpy(fn,body+TAS_RN_LOCAL_OFFSET,0x32);
    fn[0x32]=179; tas_rn_put32(fn+0x33,(uint32_t)(67+3+extra)); fn[0x37]=4;
    memcpy(fn+0x38,body+TAS_RN_LOCAL_OFFSET+0x35,0x6a-0x35);
    memcpy(fn+0x6d,code,extra);
    memcpy(fn+0x6d+extra,body+TAS_RN_LOCAL_OFFSET+0x6a,TAS_RN_LOCAL_SIZE-0x6a);
    tas_rn_put32(copy+TAS_RN_LOCAL_HEADER,
        (tas_rn_u32(body+TAS_RN_LOCAL_HEADER)&0xfe000000U)|(uint32_t)(length-20));
    uint16_t size=(uint16_t)(TAS_RN_LOCAL_SIZE+3+extra);
    memcpy(copy+TAS_RN_LOCAL_HEADER+4,&size,2);
    tas_rn_put32(copy+32,(uint32_t)count);
    if (!sha1(copy,(uint32_t)count-20,copy+count-20)) { free(copy); return NULL; }
    *result_length=count;
    return copy;
}
#endif
