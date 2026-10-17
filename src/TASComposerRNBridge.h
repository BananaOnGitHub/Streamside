#ifndef TAS_COMPOSER_RN_BRIDGE_H
#define TAS_COMPOSER_RN_BRIDGE_H
#include "TASComposerTrace.h"
#include "TASDiagnosticPolicy.h"
#include <math.h>
#if TAS_RN_COMPOSER_DIAGNOSTIC
#ifndef TAS_CT_RN_DOUBLE
#define TAS_CT_RN_DOUBLE(o) ((double (*)(id,SEL))objc_msgSend)(o,sel_registerName("doubleValue"))
#endif
/* Uses an existing donor property spelling; no new donor string admission. */
static id rn_composer_trace(id self,SEL command,id event,id session,id x,id y,id width,id height){
    (void)self;(void)command;
    if(!tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED))return nil;
    id packet[]={event,session,x,y,width,height};double values[6];
    for(unsigned i=0;i<6;i++){
        if(!kind(packet[i],"NSNumber"))return nil;
        values[i]=TAS_CT_RN_DOUBLE(packet[i]);
        if(!isfinite(values[i])||fabs(values[i])>100000)return nil;
    }
    if(values[0]<20||values[0]>24||floor(values[0])!=values[0]||values[1]<1||floor(values[1])!=values[1])return nil;
    tas_composer_trace_js((unsigned)values[0],(unsigned)values[1],values[2],values[3],values[4],values[5]);return nil;
}
static const TASRNMethodInfo *rn_composer_trace_export(id self,SEL command){
    (void)self;(void)command;
    static const TASRNMethodInfo info={"onLayout","composerTrace:(NSNumber *)event session:(NSNumber *)session x:(NSNumber *)x y:(NSNumber *)y width:(NSNumber *)width height:(NSNumber *)height",YES};return &info;
}
#endif
#endif
