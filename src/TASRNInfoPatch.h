#ifndef TAS_RN_INFO_PATCH_H
#define TAS_RN_INFO_PATCH_H
#include "TASRNComposerPatch.h"

/* Diagnostic-only exact-donor seams, in presentation order. No props, token,
 * text or URL crosses the bridge: only seam number, emote ID and tap presence.
 * IDs are classified synchronously and discarded by the native recorder.
 * A prefix leaves every existing branch/environment/hook instruction intact.
 */
typedef struct {
    uint32_t index, info, offset, size, frame, parent_key, id_key;
} TASRNInfoTarget;
static const TASRNInfoTarget tas_rn_info_targets[]={
    {19127,26954740,27786460,1207,41,0,52778}, /* working width body */
    {43823,27646672,25975179,36,14,0,52778}, /* actual EmotePart tap */
    {19174,26956232,21605078,771,28,61502,31772}, /* openCard.emoteID */
    {19172,26956192,21602246,2832,46,0,31772}, /* emote sheet */
    {19704,26969964,21761043,5745,95,26897,156}, /* EmoteCard content */
};
#define TAS_RN_INFO_TARGETS 5U

static inline size_t tas_rn_info_code(unsigned char *out,unsigned seam) {
    if (seam>=TAS_RN_INFO_TARGETS) return 0;
    const TASRNInfoTarget *t=&tas_rn_info_targets[seam];
    unsigned char *p=out,*jumps[8];unsigned n=0;
#define INFO_BYTES(...) do { const unsigned char b[]={__VA_ARGS__};memcpy(p,b,sizeof(b));p+=sizeof(b); } while (0)
#define INFO_KEY(reg,key) INFO_BYTES(144,reg,(key)&255,(key)>>8)
#define INFO_FALSE(reg) do { jumps[n++]=p;INFO_BYTES(179,0,0,0,0,reg); } while (0)
    INFO_BYTES(61,0); /* global */
    INFO_KEY(2,18843);INFO_BYTES(93,1,0,2);INFO_FALSE(1); /* __r */
    INFO_BYTES(147,0,139,2,16,110,1,1,0,2);INFO_FALSE(1); /* __r(16) */
    INFO_KEY(2,110);INFO_BYTES(93,1,1,2);INFO_FALSE(1);
    INFO_KEY(2,20058);INFO_BYTES(93,1,1,2);INFO_FALSE(1);
    INFO_KEY(2,26600);INFO_BYTES(93,3,1,2);INFO_FALSE(3); /* trace */
    INFO_BYTES(148,5,148,6); /* default null ID/flag */
    if (seam==1) {
        INFO_BYTES(52,4,0,59,4,4,0); /* tap closure env: part */
    } else {
        INFO_BYTES(137,4,1); /* props */
        if (t->parent_key) {
            INFO_KEY(2,t->parent_key);INFO_BYTES(93,4,4,2);
        }
    }
    /* Missing host/card data is still a recorded boundary invocation. */
    unsigned char *missing=p;INFO_BYTES(179,0,0,0,0,4);
    INFO_KEY(2,t->id_key);INFO_BYTES(93,5,4,2);
    /* Undefined is not a supported native argument. Normalize to null. */
    INFO_BYTES(176,5,5,148,5);
    if (seam==0) {
        INFO_KEY(2,194); /* onPress, exact donor pool */
        INFO_BYTES(93,6,4,2,19,6,6,19,6,6); /* !!onPress */
    }
    tas_rn_put32(missing+1,(uint32_t)(p-missing));
    INFO_BYTES(139,7,seam,112,0,3,1,7,5,6);
    /* All faults resume the untouched original body; no return override. */
    INFO_BYTES(175,7,0,0,0,119,0);
    for (unsigned i=0;i<n;i++) tas_rn_put32(jumps[i]+1,(uint32_t)(p-jumps[i]));
#undef INFO_FALSE
#undef INFO_KEY
#undef INFO_BYTES
    return (size_t)(p-out);
}

/* Invoked only after width/local/composer admission. All five targets are
 * validated before allocation. No partial instrumentation on a mismatch. */
static inline unsigned char *tas_rn_info_patch(const unsigned char *body,
        size_t length,TASRNSHA1 sha1,size_t *result_length) {
    if (result_length) *result_length=0;
    if (!body || !sha1 || !result_length || length<TAS_RN_BODY_SIZE+7000 ||
        length>TAS_RN_BODY_SIZE+16384 || tas_rn_u32(body+32)!=length) return NULL;
    unsigned char digest[20];
    if (!sha1(body,(uint32_t)length-20,digest) || memcmp(digest,body+length-20,20)) return NULL;
    size_t starts[TAS_RN_INFO_TARGETS],infos[TAS_RN_INFO_TARGETS],extras[TAS_RN_INFO_TARGETS];
    unsigned char codes[TAS_RN_INFO_TARGETS][256];size_t cursor=length-20;
    for (unsigned i=0;i<TAS_RN_INFO_TARGETS;i++) {
        const TASRNInfoTarget *t=&tas_rn_info_targets[i];
        const unsigned char *small=body+128+t->index*12;
        uint32_t info=(tas_rn_u32(small)&0xffffffU)|((tas_rn_u32(small+4)>>14)<<24);
        if (small[11]!=0x20 || info!=t->info ||
            tas_rn_u32(body+info)!=t->offset || tas_rn_u32(body+info+12)!=t->size ||
            tas_rn_u32(body+info+28)!=t->frame || body[info+36]!=(i==1 ? 1:2)) return NULL;
        extras[i]=tas_rn_info_code(codes[i],i);starts[i]=cursor;
        infos[i]=(cursor+t->size+extras[i]+3)&~(size_t)3;
        cursor=infos[i]+40+16;
    }
    size_t total=cursor+20;unsigned char *copy=calloc(1,total);
    if (!copy) return NULL;
    memcpy(copy,body,length-20);
    for (unsigned i=0;i<TAS_RN_INFO_TARGETS;i++) {
        const TASRNInfoTarget *t=&tas_rn_info_targets[i];
        memcpy(copy+starts[i],codes[i],extras[i]);
        memcpy(copy+starts[i]+extras[i],body+t->offset,t->size);
        unsigned char *small=copy+128+t->index*12,*info=copy+infos[i];
        memset(small,0,12);tas_rn_put32(small,(uint32_t)infos[i]&0xffffffU);
        tas_rn_put32(small+4,((uint32_t)infos[i]>>24)<<14);small[11]=0x20;
        memcpy(info,body+t->info,40);tas_rn_put32(info,(uint32_t)starts[i]);
        tas_rn_put32(info+12,(uint32_t)(t->size+extras[i]));info[36]|=8;
        /* Tap's original frame has only r3..13 Call4 staging: enlarge that
         * frame so the diagnostic r0..7 are never clobbered before native entry.
         * Its original Call3 has explicit operands, no implicit staging moves. */
        if (i==1) tas_rn_put32(info+28,24);
        tas_rn_put32(info+40,1);tas_rn_put32(info+44,0);
        tas_rn_put32(info+48,(uint32_t)extras[i]-7);
        tas_rn_put32(info+52,(uint32_t)extras[i]-2);
    }
    tas_rn_put32(copy+32,(uint32_t)total);
    if (!sha1(copy,(uint32_t)total-20,copy+total-20)) { free(copy);return NULL; }
    *result_length=total;return copy;
}
#endif
