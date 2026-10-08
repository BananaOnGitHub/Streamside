#ifndef TAS_RN_STRIP_PATCH_H
#define TAS_RN_STRIP_PATCH_H
#include "TASRNPopupPatch.h"
#include "TASRNStripPayload.h"

/* Second owned function graft, after the confirmed info-card graft. Only the
 * ChatComposerBar export starts the scoped input/library adapters. All existing functions, including
 * preview clocks and provider sheets, retain their bodies and relative data. */
static inline unsigned char *tas_rn_strip_patch(const unsigned char *body,
        size_t length,TASRNSHA1 sha1,size_t *result_length) {
    if(result_length)*result_length=0;
    const size_t prior_delta=TAS_RN_POPUP_FUNCTIONS*12U;
    const size_t table_end=128U+TAS_RN_STRIP_BASE*12U;
    const size_t delta=TAS_RN_STRIP_FUNCTIONS*12U;
    const size_t join=0x46,fh=128U+4869U*12U;
    const size_t old_info=TAS_RN_STRIP_FACTORY_INFO+prior_delta;
    const size_t old_start=TAS_RN_STRIP_FACTORY_OFFSET+prior_delta;
    if(!body || !sha1 || !result_length || length!=27797044U || tas_rn_u32(body+32)!=length ||
        tas_rn_u32(body+40)!=TAS_RN_STRIP_BASE || body[fh+11]!=32 ||
        ((tas_rn_u32(body+fh)&0x00ffffffU)|((tas_rn_u32(body+fh+4)>>14)<<24))!=old_info ||
        tas_rn_u32(body+old_info)!=old_start || tas_rn_u32(body+old_info+12)!=TAS_RN_STRIP_FACTORY_SIZE ||
        tas_rn_u32(body+old_info+28)!=22 || (body[old_info+36]&24))return NULL;
    unsigned char digest[20];
    if(!sha1(body,(uint32_t)length-20,digest) || memcmp(digest,body+length-20,20))return NULL;
    /* r2=original component; r1=undefined; r0/r8 dead. Keep frame 22 and
     * restore r2 only on a successful installer. Catch preserves the export. */
    const unsigned char code[]={132,0,1,TAS_RN_STRIP_BASE&255,TAS_RN_STRIP_BASE>>8,
        110,8,0,1,2,178,6,8,16,2,8,174,4,119,0};
    const size_t prefix=length-20+delta,payload_start=(prefix+3)&~(size_t)3;
    const size_t factory_start=payload_start+sizeof(tas_rn_strip_payload);
    const size_t factory_info=(factory_start+TAS_RN_STRIP_FACTORY_SIZE+sizeof(code)+3)&~(size_t)3;
    const size_t count=factory_info+40+16+20;
    unsigned char *copy=calloc(1,count);if(!copy)return NULL;
    memcpy(copy,body,table_end);memcpy(copy+table_end+delta,body+table_end,length-20-table_end);
    for(unsigned i=0;i<TAS_RN_STRIP_BASE;i++) {
        const unsigned char *old=body+128U+i*12U;unsigned char *header=copy+128U+i*12U;
        uint32_t word=tas_rn_u32(old),offset=word&0x01ffffffU;
        if(old[11]&32) {
            uint32_t info=(word&0x00ffffffU)|((tas_rn_u32(old+4)>>14)<<24);
            if(info<table_end || info>length-60)goto refused;
            uint32_t start=tas_rn_u32(body+info),size=tas_rn_u32(body+info+12);
            if(start<table_end || start>length-20 || size>length-20-start)goto refused;
            tas_rn_put32(copy+info+delta,start+(uint32_t)delta);
            uint32_t moved=info+(uint32_t)delta;
            tas_rn_put32(header,moved&0x00ffffffU);tas_rn_put32(header+4,(moved>>24)<<14);
        } else {
            if(offset<table_end || offset>length-20 || offset+delta>=0x02000000U)goto refused;
            tas_rn_put32(header,(word&0xfe000000U)|(offset+(uint32_t)delta));
        }
    }
    tas_rn_put32(copy+TAS_RN_STRIP_DEBUG_FIELD,tas_rn_u32(body+TAS_RN_STRIP_DEBUG_FIELD)+(uint32_t)delta);
    memcpy(copy+payload_start,tas_rn_strip_payload,sizeof(tas_rn_strip_payload));
    for(unsigned i=0;i<TAS_RN_STRIP_FUNCTIONS;i++) {
        uint32_t info=(uint32_t)payload_start+tas_rn_strip_infos[i];unsigned char *header=copy+table_end+i*12U;
        tas_rn_put32(header,info&0x00ffffffU);tas_rn_put32(header+4,(info>>24)<<14);header[11]=32;
        tas_rn_put32(copy+info,tas_rn_u32(copy+info)+(uint32_t)payload_start);
    }
    unsigned char *fn=copy+factory_start;
    memcpy(fn,body+old_start,join);memcpy(fn+join,code,sizeof(code));
    memcpy(fn+join+sizeof(code),body+old_start+join,TAS_RN_STRIP_FACTORY_SIZE-join);
    unsigned char *info=copy+factory_info;memcpy(info,body+old_info,40);
    tas_rn_put32(info,(uint32_t)factory_start);tas_rn_put32(info+12,TAS_RN_STRIP_FACTORY_SIZE+sizeof(code));info[36]|=8;
    tas_rn_put32(info+40,1);tas_rn_put32(info+44,(uint32_t)join);
    tas_rn_put32(info+48,(uint32_t)(join+10));tas_rn_put32(info+52,(uint32_t)(join+sizeof(code)-2));
    memset(copy+fh,0,12);tas_rn_put32(copy+fh,(uint32_t)factory_info&0x00ffffffU);
    tas_rn_put32(copy+fh+4,((uint32_t)factory_info>>24)<<14);copy[fh+11]=32;
    tas_rn_put32(copy+40,TAS_RN_STRIP_BASE+TAS_RN_STRIP_FUNCTIONS);tas_rn_put32(copy+32,(uint32_t)count);
    if(!sha1(copy,(uint32_t)count-20,copy+count-20))goto refused;
    *result_length=count;return copy;
refused:
    free(copy);return NULL;
}
#endif
