#ifndef TAS_RN_LOCAL_ECHO_PATCH_H
#define TAS_RN_LOCAL_ECHO_PATCH_H
#include "TASRNWidthPatch.h"

#define TAS_RN_LOCAL_INDEX 34222U
#define TAS_RN_LOCAL_OFFSET 25042626U
#define TAS_RN_LOCAL_SIZE 684U
#define TAS_RN_LOCAL_HEADER (128U + TAS_RN_LOCAL_INDEX * 12U)

/* Runs only on buildLocalEcho's completed, private preview string (r3).
 * Uses Twitch's existing Metro NativeModules loader (module 16, factory 20),
 * which selects the native proxy OR the classic bridge configuration.
 * The distinct Streamside-owned module/export both use "buildLocalEcho" to
 * avoid changing the donor constant pools. No socket/send code is patched.
 * r4..r7 are dead Value registers after the donor's final concat Call.
 * Missing loader/exports/module/method leaves the original preview in r3.
 */
static inline size_t tas_rn_local_code(unsigned char *out) {
    unsigned char *p=out, *jumps[5];
#define LOCAL_BYTES(...) do { const unsigned char b[]={__VA_ARGS__}; memcpy(p,b,sizeof(b)); p+=sizeof(b); } while (0)
    LOCAL_BYTES(61,4);                         /* GetGlobalObject r4 */
    LOCAL_BYTES(144,5,0x9b,0x49);              /* __r (18843) */
    LOCAL_BYTES(93,5,4,5);                    /* GetByVal r5,r4,r5 */
    jumps[0]=p; LOCAL_BYTES(179,0,0,0,0,5);
    LOCAL_BYTES(139,6,16);                    /* NativeModules module ID */
    LOCAL_BYTES(110,5,5,4,6);                 /* Call2 r5,require,global,16 */
    jumps[1]=p; LOCAL_BYTES(179,0,0,0,0,5);
    LOCAL_BYTES(144,7,110,0);                 /* default (110) */
    LOCAL_BYTES(93,5,5,7);
    jumps[2]=p; LOCAL_BYTES(179,0,0,0,0,5);
    LOCAL_BYTES(144,7,0x5a,0x4e);              /* buildLocalEcho (20058) */
    LOCAL_BYTES(93,5,5,7);
    jumps[3]=p; LOCAL_BYTES(179,0,0,0,0,5);
    LOCAL_BYTES(93,6,5,7);
    jumps[4]=p; LOCAL_BYTES(179,0,0,0,0,6);
    LOCAL_BYTES(110,3,6,5,3);                 /* Call2 r3,method,module,line */
    for (unsigned i=0;i<5;i++) tas_rn_put32(jumps[i]+1,(uint32_t)(p-jumps[i]));
#undef LOCAL_BYTES
    return (size_t)(p-out);
}

/* Internal second stage: accepts ONLY the output of the exact width patch.
 * The caller must first admit the original complete donor SHA-1. Retains all
 * width code, original function/data offsets and the original local function.
 */
static inline unsigned char *tas_rn_local_patch(const unsigned char *body,
        size_t length, TASRNSHA1 sha1, size_t *result_length) {
    static const unsigned char header[12]={0xc2,0x1e,0x7e,7,0xac,2,0x3e,0x18,0x22,0x15,1,2};
    if (result_length) *result_length=0;
    if (!body || !sha1 || !result_length || length!=TAS_RN_BODY_SIZE+1207 ||
        tas_rn_u32(body+32)!=length ||
        memcmp(body+TAS_RN_LOCAL_HEADER,header,12)) return NULL;
    unsigned char digest[20];
    if (!sha1(body,(uint32_t)length-20,digest) || memcmp(digest,body+length-20,20)) return NULL;
    unsigned char code[96]; size_t extra=tas_rn_local_code(code);
    size_t count=length+TAS_RN_LOCAL_SIZE+extra;
    unsigned char *copy=malloc(count);
    if (!copy) return NULL;
    memcpy(copy,body,length-20);
    unsigned char *fn=copy+length-20;
    memcpy(fn,body+TAS_RN_LOCAL_OFFSET,0x2a6);
    memcpy(fn+0x2a6,code,extra);
    memcpy(fn+0x2a6+extra,body+TAS_RN_LOCAL_OFFSET+0x2a6,TAS_RN_LOCAL_SIZE-0x2a6);
    /* The two anonymous/missing-login gates jump past the inserted block to
     * the original null return. Every other original branch stays unchanged. */
    tas_rn_put32(fn+0x09,tas_rn_u32(fn+0x09)+(uint32_t)extra);
    tas_rn_put32(fn+0x14,tas_rn_u32(fn+0x14)+(uint32_t)extra);
    tas_rn_put32(copy+TAS_RN_LOCAL_HEADER,
        (tas_rn_u32(body+TAS_RN_LOCAL_HEADER)&0xfe000000U)|(uint32_t)(length-20));
    uint16_t size=(uint16_t)(TAS_RN_LOCAL_SIZE+extra);
    memcpy(copy+TAS_RN_LOCAL_HEADER+4,&size,2);
    tas_rn_put32(copy+32,(uint32_t)count);
    if (!sha1(copy,(uint32_t)count-20,copy+count-20)) { free(copy); return NULL; }
    *result_length=count;
    return copy;
}
#endif
