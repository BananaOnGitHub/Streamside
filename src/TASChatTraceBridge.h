#ifndef TAS_CHAT_TRACE_BRIDGE_H
#define TAS_CHAT_TRACE_BRIDGE_H
#include "TASChatTrace.h"
#if TAS_CHAT_TRACE_DIAGNOSTIC
#ifndef TAS_CHAT_TRACE_BOX
#define TAS_CHAT_TRACE_BOX(n) ((id (*)(id,SEL,int))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithInt:"),(n))
#endif
/* Included after TASRNMethodInfo and module kind/text helpers. */
static id rn_chat_trace(id self,SEL command,id packet) {
    (void)self;(void)command;
    if(!tas_diag_wants(TAS_DIAG_CHAT,TAS_DIAG_DETAILED))return TAS_CHAT_TRACE_BOX(0);
    bool accepted=kind(packet,"NSString") && tas_chat_trace_packet(text(packet));
    return TAS_CHAT_TRACE_BOX(accepted?1:0);
}
static const TASRNMethodInfo *rn_chat_trace_export(id self,SEL command) {
    (void)self;(void)command;
    static const TASRNMethodInfo info={"trace","trace:(NSString *)packet",YES};return &info;
}
#endif
#endif
