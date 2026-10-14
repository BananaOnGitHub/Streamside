#ifndef TAS_RN_CHAT_TRACE_PATCH_H
#define TAS_RN_CHAT_TRACE_PATCH_H
#include "TASRNStripPatch.h"
#include "TASRNChatTracePayload.h"
/* Diagnostic-only sixth graft. Exact predecessor, factory 4900 export join.
 * r4=original memoized list, r1=undefined, r6 dead; r2/RN and r3/environment
 * survive. Extra frame space keeps Call2 staging away from original live regs.
 * Catch retains the original export. No donor function body is repository data. */
static inline unsigned char *tas_rn_chat_trace_patch(const unsigned char *body,
        size_t length,TASRNSHA1 sha1,size_t *result_length) {
    if(result_length)*result_length=0;
    const size_t prior_delta=(TAS_RN_POPUP_FUNCTIONS+TAS_RN_STRIP_FUNCTIONS)*12U;
    const size_t table_end=128U+TAS_RN_CHAT_BASE*12U,delta=TAS_RN_CHAT_FUNCTIONS*12U;
    const size_t join=0x116,fh=128U+4900U*12U;
    const size_t old_info=TAS_RN_CHAT_FACTORY_INFO+prior_delta,old_start=TAS_RN_CHAT_FACTORY_OFFSET+prior_delta;
    if(!body || !sha1 || !result_length || length!=28723880U ||
        tas_rn_u32(body+32)!=length || tas_rn_u32(body+40)!=TAS_RN_CHAT_BASE ||
        body[fh+11]!=32 || ((tas_rn_u32(body+fh)&0x00ffffffU)|((tas_rn_u32(body+fh+4)>>14)<<24))!=old_info ||
        tas_rn_u32(body+old_info)!=old_start || tas_rn_u32(body+old_info+12)!=TAS_RN_CHAT_FACTORY_SIZE ||
        tas_rn_u32(body+old_info+28)!=22 || (body[old_info+36]&24) ||
        body[old_start+join]!=74)return NULL;
    unsigned char digest[20];
    const unsigned char predecessor[20]={32,203,234,238,194,160,133,7,120,202,115,193,172,119,244,200,182,184,149,138};
    if(!sha1(body,(uint32_t)length-20,digest) || memcmp(digest,body+length-20,20) || memcmp(digest,predecessor,20))return NULL;
    const unsigned char code[]={132,6,1,TAS_RN_CHAT_BASE&255,TAS_RN_CHAT_BASE>>8,
        110,6,6,1,4,16,4,6,174,4,119,6};
    const size_t prefix=length-20+delta,payload_start=(prefix+3)&~(size_t)3;
    const size_t factory_start=payload_start+sizeof(tas_rn_chat_payload);
    const size_t factory_info=(factory_start+TAS_RN_CHAT_FACTORY_SIZE+sizeof(code)+3)&~(size_t)3;
    const size_t count=factory_info+40+16+20;
    unsigned char *copy=calloc(1,count);if(!copy)return NULL;
    memcpy(copy,body,table_end);memcpy(copy+table_end+delta,body+table_end,length-20-table_end);
    for(unsigned i=0;i<TAS_RN_CHAT_BASE;i++) {
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
    tas_rn_put32(copy+TAS_RN_CHAT_DEBUG_FIELD,tas_rn_u32(body+TAS_RN_CHAT_DEBUG_FIELD)+(uint32_t)delta);
    memcpy(copy+payload_start,tas_rn_chat_payload,sizeof(tas_rn_chat_payload));
    for(unsigned i=0;i<TAS_RN_CHAT_FUNCTIONS;i++) {
        uint32_t info=(uint32_t)payload_start+tas_rn_chat_infos[i];unsigned char *header=copy+table_end+i*12U;
        tas_rn_put32(header,info&0x00ffffffU);tas_rn_put32(header+4,(info>>24)<<14);header[11]=32;
        tas_rn_put32(copy+info,tas_rn_u32(copy+info)+(uint32_t)payload_start);
    }
    unsigned char *fn=copy+factory_start;
    memcpy(fn,body+old_start,join);memcpy(fn+join,code,sizeof(code));
    memcpy(fn+join+sizeof(code),body+old_start+join,TAS_RN_CHAT_FACTORY_SIZE-join);
    unsigned char *info=copy+factory_info;memcpy(info,body+old_info,40);
    tas_rn_put32(info,(uint32_t)factory_start);tas_rn_put32(info+12,TAS_RN_CHAT_FACTORY_SIZE+sizeof(code));
    tas_rn_put32(info+28,33);info[36]|=8;
    tas_rn_put32(info+40,1);tas_rn_put32(info+44,(uint32_t)join);
    tas_rn_put32(info+48,(uint32_t)(join+10));tas_rn_put32(info+52,(uint32_t)(join+15));
    memset(copy+fh,0,12);tas_rn_put32(copy+fh,(uint32_t)factory_info&0x00ffffffU);
    tas_rn_put32(copy+fh+4,((uint32_t)factory_info>>24)<<14);copy[fh+11]=32;
    tas_rn_put32(copy+40,TAS_RN_CHAT_BASE+TAS_RN_CHAT_FUNCTIONS);tas_rn_put32(copy+32,(uint32_t)count);
    if(!sha1(copy,(uint32_t)count-20,copy+count-20))goto refused;
    *result_length=count;return copy;
refused:
    free(copy);return NULL;
}
#endif
