#ifndef TAS_RN_COMPOSER_PATCH_H
#define TAS_RN_COMPOSER_PATCH_H
#include "TASRNLocalEchoPatch.h"

#define TAS_RN_COMPOSER_INDEX 22083U
#define TAS_RN_COMPOSER_OFFSET 22793824U
#define TAS_RN_COMPOSER_SIZE 6240U
#define TAS_RN_COMPOSER_HEADER (128U + TAS_RN_COMPOSER_INDEX * 12U)
#define TAS_RN_COMPOSER_INFO 27033284U
#define TAS_RN_COMPOSER_JOIN 0xa7U

/* Scoped chat composer: r49=draft, r75=channelID, r47=native emoteMap.
 * r0/r1/r2/r9/r10 are dead here (r2's undefined is restored). The existing
 * frame 97 already puts Call4 staging in r86..96; no frame growth, remapping,
 * hooks, draft/selection/props mutation or outgoing-message rewrite.
 * Every original branch is after this straight-line prefix, so appending an
 * insertion here preserves every original relative branch byte verbatim.
 */
static inline size_t tas_rn_composer_code(unsigned char *out) {
    unsigned char *p=out,*jumps[6]; unsigned n=0;
#define COM_BYTES(...) do { const unsigned char b[]={__VA_ARGS__}; memcpy(p,b,sizeof(b)); p+=sizeof(b); } while (0)
#define COM_KEY(reg,key) COM_BYTES(144,reg,(key)&255,(key)>>8)
#define COM_FALSE(reg) do { jumps[n++]=p; COM_BYTES(179,0,0,0,0,reg); } while (0)
    COM_BYTES(61,9);
    COM_KEY(10,18843); COM_BYTES(93,10,9,10); /* __r */
    COM_FALSE(10);
    COM_BYTES(139,1,16,110,10,10,9,1); /* NativeModules */
    COM_FALSE(10);
    COM_KEY(1,110); COM_BYTES(93,10,10,1); /* default */
    COM_FALSE(10);
    COM_KEY(1,20058); COM_BYTES(93,10,10,1); /* separate module */
    COM_FALSE(10);
    COM_KEY(1,46459); COM_BYTES(93,9,10,1); /* emoteMap method */
    COM_FALSE(9);
    COM_BYTES(112,0,9,10,49,75,47);
    COM_FALSE(0);
    COM_BYTES(16,47,0); /* update local preview map only */
    COM_BYTES(175,7,0,0,0,119,0); /* skip Catch */
    for (unsigned i=0;i<n;i++) tas_rn_put32(jumps[i]+1,(uint32_t)(p-jumps[i]));
    COM_BYTES(147,2); /* original undefined */
#undef COM_FALSE
#undef COM_KEY
#undef COM_BYTES
    return (size_t)(p-out);
}

/* Called only after original donor admission and the working width/local
 * patches. Reject changed composer headers; preserve all original bytes and
 * redirect only its overflow header to an appended full header + handler. */
static inline unsigned char *tas_rn_composer_patch(const unsigned char *body,
        size_t length,TASRNSHA1 sha1,size_t *result_length) {
    static const unsigned char small[12]={0xc4,0x7e,0x9c,0,0,0x40,0,0,0,0,0,0x20};
    if (result_length) *result_length=0;
    if (!body || !sha1 || !result_length || length<TAS_RN_BODY_SIZE+1207 ||
        length>TAS_RN_BODY_SIZE+4096 || tas_rn_u32(body+32)!=length ||
        memcmp(body+TAS_RN_COMPOSER_HEADER,small,12) ||
        tas_rn_u32(body+TAS_RN_COMPOSER_INFO)!=TAS_RN_COMPOSER_OFFSET ||
        tas_rn_u32(body+TAS_RN_COMPOSER_INFO+12)!=TAS_RN_COMPOSER_SIZE ||
        tas_rn_u32(body+TAS_RN_COMPOSER_INFO+28)!=97 || body[TAS_RN_COMPOSER_INFO+36]!=2) return NULL;
    unsigned char digest[20];
    if (!sha1(body,(uint32_t)length-20,digest) || memcmp(digest,body+length-20,20)) return NULL;
    unsigned char code[256]; size_t extra=tas_rn_composer_code(code);
    size_t large=(length-20+TAS_RN_COMPOSER_SIZE+extra+3)&~(size_t)3;
    size_t count=large+40+16+20;
    unsigned char *copy=calloc(1,count);
    if (!copy) return NULL;
    memcpy(copy,body,length-20);
    unsigned char *fn=copy+length-20;
    memcpy(fn,body+TAS_RN_COMPOSER_OFFSET,TAS_RN_COMPOSER_JOIN);
    memcpy(fn+TAS_RN_COMPOSER_JOIN,code,extra);
    memcpy(fn+TAS_RN_COMPOSER_JOIN+extra,body+TAS_RN_COMPOSER_OFFSET+TAS_RN_COMPOSER_JOIN,
        TAS_RN_COMPOSER_SIZE-TAS_RN_COMPOSER_JOIN);
    unsigned char *header=copy+TAS_RN_COMPOSER_HEADER;
    memset(header,0,12);
    tas_rn_put32(header,(uint32_t)large&0x00ffffffU);
    tas_rn_put32(header+4,((uint32_t)large>>24)<<14); header[11]=0x20;
    unsigned char *info=copy+large;
    memcpy(info,body+TAS_RN_COMPOSER_INFO,40);
    tas_rn_put32(info,(uint32_t)(length-20));
    tas_rn_put32(info+12,(uint32_t)(TAS_RN_COMPOSER_SIZE+extra)); info[36]|=8;
    tas_rn_put32(info+40,1);
    tas_rn_put32(info+44,TAS_RN_COMPOSER_JOIN);
    tas_rn_put32(info+48,(uint32_t)(TAS_RN_COMPOSER_JOIN+extra-9));
    tas_rn_put32(info+52,(uint32_t)(TAS_RN_COMPOSER_JOIN+extra-4));
    tas_rn_put32(copy+32,(uint32_t)count);
    if (!sha1(copy,(uint32_t)count-20,copy+count-20)) { free(copy); return NULL; }
    *result_length=count; return copy;
}
#endif
