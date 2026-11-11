#include "SSNSwiftABI.h"
void call_current(CurrentRequest fn,void *out,id self) { fn(out,self); }
void call_follows(FollowRequest fn,void *out,id self,uintptr_t a,uintptr_t b,uintptr_t d,uintptr_t set) {
    fn(out,50,a,b,d,set,self);
}
id call_promise(PromiseObjC fn,const void *value,Map success,Map failure,const void *type,const void *objc) {
    return fn(success,0,failure,0,type,objc,objc,value);
}
id call_map(Map fn,const void *value,void *context) { return fn(value,context); }
Words2 call_string(StringGetter fn,const void *value) { return fn(value); }
void call_getter(Getter fn,void *out,const void *value) { fn(out,value); }
