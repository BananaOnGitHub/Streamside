#ifndef TAS_RN_WIDTH_PATCH_H
#define TAS_RN_WIDTH_PATCH_H

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Private incoming presentation namespace. All integers remain exact in JS.
 * Low four digits carry round(aspect * 1000), bounded to 0.125..5.
 * The remaining eight digits derive from the existing persistent image ID.
 * Registry admission still checks collisions; this is NOT a native-ID rule. */
#define TAS_RN_WIDTH_BASE 860000000000000ULL
#define TAS_RN_WIDTH_END  861000000000000ULL
static inline uint64_t tas_rn_width_id(uint64_t image_id, double aspect) {
    if (!(aspect > 0)) aspect = 1;
    if (aspect < .125) aspect = .125;
    if (aspect > 5) aspect = 5;
    unsigned ratio = (unsigned)(aspect * 1000 + .5);
    return TAS_RN_WIDTH_BASE + (image_id % 100000000ULL) * 10000 + ratio;
}

typedef unsigned char *(*TASRNSHA1)(const void *, uint32_t, unsigned char *);
#define TAS_RN_BODY_SIZE 27786480U
#define TAS_RN_FUNCTION_OFFSET 21568121U
#define TAS_RN_FUNCTION_SIZE 947U
#define TAS_RN_LARGE_HEADER 26954740U
#define TAS_RN_SMALL_HEADER (128U + 19127U * 12U)

static inline uint32_t tas_rn_u32(const unsigned char *p) {
    uint32_t v; memcpy(&v,p,4); return v;
}
static inline void tas_rn_put32(unsigned char *p, uint32_t v) { memcpy(p,&v,4); }
static inline void tas_rn_double(unsigned char *p, double v) { memcpy(p,&v,8); }

/* Hermes-98 instructions. Only r18..r21 are scratch, in the donor's existing
 * Value-register bank; no frame/call layout, constant pool or cache is changed.
 * Runs AFTER the memoized style selection, on every render (including reuse).
 * For provider IDs: style = [style, {width: baseHeight * encodedAspect}].
 * Unknown/native/old synthetic IDs preserve the exact original style object.
 * r10 is emoteId; r11 is gigantified at BOTH donor insertion boundaries. */
static inline size_t tas_rn_width_code(unsigned char *out, unsigned style) {
    unsigned char *p=out;
#define RN_BYTES(...) do { const unsigned char b[]={__VA_ARGS__}; memcpy(p,b,sizeof(b)); p+=sizeof(b); } while (0)
#define RN_DOUBLE(r,v) do { RN_BYTES(141,r); tas_rn_double(p,v); p+=8; } while (0)
#define RN_INT(r,v) do { RN_BYTES(140,r); tas_rn_put32(p,v); p+=4; } while (0)
    unsigned char *jumps[4];
    RN_BYTES(154,18,10);                         /* ToNumber r18,r10 */
    RN_DOUBLE(19,860000000000000.0);
    RN_BYTES(27,20,19,18);                      /* LessEq r20,r19,r18 */
    jumps[0]=p; RN_BYTES(179,0,0,0,0,20);        /* JmpFalseLong done,r20 */
    RN_DOUBLE(19,861000000000000.0);
    RN_BYTES(26,20,18,19);                      /* Less r20,r18,r19 */
    jumps[1]=p; RN_BYTES(179,0,0,0,0,20);
    RN_INT(19,10000);
    RN_BYTES(37,18,18,19);                      /* Mod r18,r18,r19 */
    RN_BYTES(139,19,125,27,20,19,18);
    jumps[2]=p; RN_BYTES(179,0,0,0,0,20);
    RN_INT(19,5000);
    RN_BYTES(27,20,18,19);
    jumps[3]=p; RN_BYTES(179,0,0,0,0,20);
    RN_INT(19,1000);
    RN_BYTES(35,18,18,19,139,19,24);            /* aspect; inline height */
    RN_BYTES(178,6,11,139,19,56);               /* JmpFalse +6,r11 */
    RN_BYTES(33,18,18,19,4,19);                 /* width; NewObject r19 */
    RN_BYTES(144,20,179,0,96,19,20,18);         /* "width"; PutByValLoose */
    RN_BYTES(8,21,2,0,90,21,style,0,90,21,19,1,16,style,21);
    for (unsigned i=0;i<4;i++) tas_rn_put32(jumps[i]+1,(uint32_t)(p-jumps[i]));
#undef RN_INT
#undef RN_DOUBLE
#undef RN_BYTES
    return (size_t)(p-out);
}

/* Allocate a new HBC body, never alter the donor or caller's NSData.
 * Admission validates the entire exact body using its expected SHA-1 footer,
 * plus format, original function headers and bytecode extent. Returns NULL on
 * EVERY mismatch or failure. No approximate offsets/ABI/object storage reads.
 * Append the modified function immediately before a new footer; all original
 * function/data/debug offsets stay valid. Only its existing large header's
 * offset/size and the file length change. The original function is retained.
 */
static inline unsigned char *tas_rn_width_patch(const unsigned char *body,
        size_t length, TASRNSHA1 sha1, size_t *result_length) {
    static const unsigned char digest[20]={0x5f,0x22,0x11,0x97,0x49,0x24,0x27,0x17,0xf3,0x78,
        0x87,0x97,0xcf,0x50,0xa7,0x7f,0x0e,0xdc,0x07,0x15};
    static const unsigned char small[12]={0xf4,0x4b,0x9b,0,0,0x40,0,0,0,0,0,0x20};
    static const unsigned char large[36]={0x79,0x1a,0x49,1,2,0,0,0,0,0,0,0,0xb3,3,0,0,
        0x37,0x41,0,0,2,0,0,0,2,0,0,0,0x29,0,0,0,0x1b,0,0,0};
    if (result_length) *result_length=0;
    if (!body || length!=TAS_RN_BODY_SIZE || !sha1 || !result_length ||
        tas_rn_u32(body)!=0x03bc1fc6 || tas_rn_u32(body+4)!=0x1f1903c1 ||
        tas_rn_u32(body+8)!=98 || tas_rn_u32(body+32)!=length ||
        memcmp(body+length-20,digest,20) ||
        memcmp(body+TAS_RN_SMALL_HEADER,small,12) ||
        memcmp(body+TAS_RN_LARGE_HEADER,large,36)) return NULL;
    unsigned char check[20];
    if (!sha1(body,(uint32_t)length-20,check) || memcmp(check,digest,20)) return NULL;
    unsigned char wrapper[192],image[192];
    size_t a=tas_rn_width_code(wrapper,13), b=tas_rn_width_code(image,14);
    size_t count=length+a+b+TAS_RN_FUNCTION_SIZE;
    unsigned char *copy=malloc(count);
    if (!copy) return NULL;
    memcpy(copy,body,length-20);
    unsigned char *p=copy+length-20;
    const unsigned char *fn=body+TAS_RN_FUNCTION_OFFSET;
    memcpy(p,fn,0xd0); p+=0xd0;
    memcpy(p,wrapper,a); p+=a;
    memcpy(p,fn+0xd0,0x238-0xd0); p+=0x238-0xd0;
    memcpy(p,image,b); p+=b;
    memcpy(p,fn+0x238,TAS_RN_FUNCTION_SIZE-0x238); p+=TAS_RN_FUNCTION_SIZE-0x238;
    /* Every original branch stays in one region or targets an insertion START.
     * No original displacement changes. Exhaustively verified against donor. */
    tas_rn_put32(copy+32,(uint32_t)count);
    tas_rn_put32(copy+TAS_RN_LARGE_HEADER,(uint32_t)length-20);
    tas_rn_put32(copy+TAS_RN_LARGE_HEADER+12,(uint32_t)(TAS_RN_FUNCTION_SIZE+a+b));
    if (!sha1(copy,(uint32_t)(p-copy),p)) { free(copy); return NULL; }
    *result_length=count;
    return copy;
}
#endif
