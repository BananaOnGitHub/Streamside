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

void call_personal(PersonalRequest fn,void *out,id self,uintptr_t set) { fn(out,0,0,0,set,self); }
uintptr_t call_sections(SectionsGetter fn,uintptr_t a,uintptr_t b) { return fn(a,b); }
void call_item(ItemGetter fn,void *out,const void *type,const void *value) { fn(out,type,value); }
void call_thumbnails(ThumbnailsGetter fn,void *out,const void *value) { *(Words3*)out=fn(value); }
void call_thumbnail_url(ThumbnailGetter fn,void *out,uintptr_t a,uintptr_t b,uintptr_t c) { fn(out,2,a,b,c); }
intptr_t call_integer(IntegerGetter fn,const void *value) { return fn(value); }

Words2 call_client(ApolloClientGetter fn,id graph) { return fn(graph); }
uintptr_t call_playback_params(PlaybackParamsInit fn) { return fn(0,2,2,0,0,0,0,11,22,0,0,33,44,0,1); }
uintptr_t call_playback_query(PlaybackQueryInit fn,const void *type) { return fn(11,22,33,type); }
void call_playback_fetch(PlaybackFetch fn,void *out,const void *type,const void *witness) { fn(out,11,1,22,33,type,witness); }
uintptr_t call_playback_field(PlaybackField fn,uintptr_t value) { return fn(value); }
Words2 call_playback_string(PlaybackString fn,uintptr_t value) { return fn(value); }
