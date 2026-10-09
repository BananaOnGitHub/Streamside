#ifndef TAS_DEMAND_RN_BRIDGE_H
#define TAS_DEMAND_RN_BRIDGE_H
#include "TASImageDemand.h"
#include <math.h>
/* Included after the module's kind()/text() helpers and TASRNMethodInfo.
 * Host validation invokes this same handler through a Hermes JSI host function;
 * platform object boxing is the host adapter, not a second packet parser. */
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
#ifndef TAS_DEMAND_RN_UINT
#define TAS_DEMAND_RN_UINT(o) ((unsigned (*)(id,SEL))objc_msgSend)(o,sel_registerName("unsignedIntValue"))
#define TAS_DEMAND_RN_DOUBLE(o) ((double (*)(id,SEL))objc_msgSend)(o,sel_registerName("doubleValue"))
#define TAS_DEMAND_RN_BOX(n) ((id (*)(id,SEL,int))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithInt:"),n)
#endif
static id rn_demand_observe(id self,SEL command,id event,id scope,id asset,id a,id b) {
    (void)self;(void)command;
    if(!kind(event,"NSNumber") || !kind(scope,"NSNumber") || !kind(a,"NSNumber") || !kind(b,"NSNumber"))return nil;
    unsigned e=TAS_DEMAND_RN_UINT(event),s=TAS_DEMAND_RN_UINT(scope);
    const char *value=kind(asset,"NSString") ? text(asset):NULL;
    double x=TAS_DEMAND_RN_DOUBLE(a),y=TAS_DEMAND_RN_DOUBLE(b);
    if(!isfinite(x) || !isfinite(y))return nil;
    if(e==27 && s==0) {
        bool accepted=tas_demand_snapshot(value,x);
        return TAS_DEMAND_RN_BOX(accepted?1:0);
    }
    tas_demand_event(e,s,value,x,y);return nil;
}
static const TASRNMethodInfo *rn_demand_export(id self,SEL command) {
    (void)self;(void)command;
    static const TASRNMethodInfo info={"observe","observe:(NSNumber *)event scope:(NSNumber *)scope asset:(NSString *)asset a:(NSNumber *)a b:(NSNumber *)b",YES};return &info;
}
#endif
#endif
