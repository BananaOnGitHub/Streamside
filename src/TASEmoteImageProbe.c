/* Temporary read-only image provenance. All identities are weak, bounded and
 * private. Neither bytes nor fingerprints nor native addresses enter reports. */
#include "TASEmoteImageProbe.h"
#if TAS_EMOTE_DIAGNOSTIC
#include <objc/message.h>
#include <pthread.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
extern id objc_storeWeak(id *,id);
extern id objc_loadWeakRetained(id *);
extern void objc_release(id);
enum { ORIGINS=256, ATTEMPTS=256, BODIES=64, IDS=32, EXPIRY=600, MAX_BYTES=8*1024*1024 };
typedef struct { uint64_t a,b; size_t bytes; } BodyKey;
typedef struct { id weak; uint64_t serial,frames,uses; time_t time; BodyKey key; const char *kind; } Origin;
typedef struct { uint64_t serial,frames; time_t time; BodyKey key; const char *kind; bool success; } Attempt;
typedef struct { BodyKey key; time_t time; uint64_t ids[IDS]; unsigned count; } Body;
static Origin origins[ORIGINS];
static Attempt attempts[ATTEMPTS];
static Body bodies[BODIES];
static unsigned origin_next,attempt_next,body_next;
static uint64_t serial,calls,unmatched,evictions,oversize;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static IMP gif_init,ui_init,ui_scale,poster_get;
static _Thread_local unsigned ui_depth,gif_depth;
static id m0(id o,const char *s) { return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static bool responds(id o,const char *s) { return o && ((BOOL (*)(id,SEL,SEL))objc_msgSend)(o,sel_registerName("respondsToSelector:"),sel_registerName(s)); }
static uint64_t integer(id o,const char *s) { return responds(o,s) ? ((unsigned long (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)) : 0; }
static time_t now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec; }
static bool equal(BodyKey a,BodyKey b) { return a.bytes && a.bytes==b.bytes && a.a==b.a && a.b==b.b; }
static BodyKey fingerprint(id data) {
    BodyKey k={0}; size_t length=(size_t)integer(data,"length");
    if (!length) return k;
    if (length>MAX_BYTES) { __atomic_add_fetch(&oversize,1,__ATOMIC_RELAXED); return k; }
    const unsigned char *bytes=(const unsigned char *)m0(data,"bytes");
    if (!bytes) return k;
    k=(BodyKey){1469598103934665603ULL,7809847782465536322ULL,length};
    for (size_t i=0;i<length;i++) { k.a=(k.a^bytes[i])*1099511628211ULL; k.b=(k.b+bytes[i]+1)*14029467366897019727ULL; k.b^=k.b>>29; }
    return k;
}
static unsigned response_ids_locked(BodyKey key,time_t t,uint64_t out[IDS]) {
    for (unsigned i=0;i<BODIES;i++) if (equal(bodies[i].key,key) && t-bodies[i].time<EXPIRY) {
        memcpy(out,bodies[i].ids,bodies[i].count*sizeof(*out)); return bodies[i].count;
    }
    return 0;
}
void tas_image_probe_response(uint64_t number,id data) {
    if (number<9000000000ULL) return;
    BodyKey key=fingerprint(data); if (!key.bytes) return;
    time_t t=now(); pthread_mutex_lock(&lock);
    unsigned slot=BODIES;
    for (unsigned i=0;i<BODIES;i++) if (equal(bodies[i].key,key) && t-bodies[i].time<EXPIRY) { slot=i; break; }
    if (slot==BODIES) { slot=body_next++%BODIES; memset(&bodies[slot],0,sizeof(bodies[slot])); bodies[slot].key=key; }
    Body *body=&bodies[slot]; body->time=t;
    unsigned i=0; for (;i<body->count;i++) if (body->ids[i]==number) break;
    if (i==body->count && body->count<IDS) body->ids[body->count++]=number;
    pthread_mutex_unlock(&lock);
}
static Origin *find_locked(id image,time_t t) {
    if (!image) return NULL;
    for (unsigned i=0;i<ORIGINS;i++) {
        if (!origins[i].serial || t-origins[i].time>=EXPIRY) continue;
        id live=objc_loadWeakRetained(&origins[i].weak); bool same=live==image;
        if (live) objc_release(live);
        if (same) return &origins[i];
    }
    return NULL;
}
static void put_locked(id image,Attempt a,const char *kind) {
    if (!image || find_locked(image,a.time)) return;
    Origin *o=&origins[origin_next++%ORIGINS];
    if (o->serial) evictions++;
    objc_storeWeak(&o->weak,nil);
    o->serial=a.serial; o->frames=a.frames; o->uses=0; o->time=a.time; o->key=a.key; o->kind=kind;
    objc_storeWeak(&o->weak,image);
}
static void decoded(id data,id image,const char *kind,uint64_t frames) {
    BodyKey key=fingerprint(data); time_t t=now(); uint64_t ids[IDS];
    pthread_mutex_lock(&lock);
    Attempt a={++serial,frames,t,key,kind,image!=nil}; calls++;
    attempts[attempt_next++%ATTEMPTS]=a;
    put_locked(image,a,kind);
    unsigned count=response_ids_locked(key,t,ids); if (!count) unmatched++;
    pthread_mutex_unlock(&lock);
    char state[192]; snprintf(state,sizeof(state),"decode=%llu decoder=%s result=%s frames=%llu bytes=%zu evidence=response-body-match decode-age=0s",
        (unsigned long long)a.serial,kind,image ? "image" : "nil",(unsigned long long)frames,key.bytes);
    for (unsigned i=0;i<count;i++) tas_emote_probe_record(ids[i],0,"decode-result",state,false);
}
static id hook_gif(id self,SEL sel,id data,unsigned long optimal,BOOL predraw) {
    gif_depth++;
    id result=((id (*)(id,SEL,id,unsigned long,BOOL))gif_init)(self,sel,data,optimal,predraw);
    gif_depth--;
    if (!gif_depth) decoded(data,result,"GIF",integer(result,"frameCount"));
    return result;
}
static id hook_ui(id self,SEL sel,id data) {
    ui_depth++; id result=((id (*)(id,SEL,id))ui_init)(self,sel,data); ui_depth--;
    if (!ui_depth && !gif_depth) decoded(data,result,"UIImage",integer(m0(result,"images"),"count"));
    return result;
}
static id hook_ui_scale(id self,SEL sel,id data,double scale) {
    ui_depth++; id result=((id (*)(id,SEL,id,double))ui_scale)(self,sel,data,scale); ui_depth--;
    if (!ui_depth && !gif_depth) decoded(data,result,"UIImage-scale",integer(m0(result,"images"),"count"));
    return result;
}
static id hook_poster(id self,SEL sel) {
    id result=((id (*)(id,SEL))poster_get)(self,sel);
    time_t t=now(); pthread_mutex_lock(&lock); Origin *o=find_locked(self,t);
    if (o) { Attempt a={o->serial,o->frames,o->time,o->key,o->kind,true}; put_locked(result,a,"GIF-poster"); }
    pthread_mutex_unlock(&lock); return result;
}
static void describe_locked(Origin *o,char *buffer,size_t capacity) {
    if (!o) { snprintf(buffer,capacity,"decode=unknown reuse=unknown source=unknown"); return; }
    snprintf(buffer,capacity,"decode=%llu decoder=%s decoded-frames=%llu decode-age=%llds reuse=%s source=observed-object",
        (unsigned long long)o->serial,o->kind,(unsigned long long)o->frames,(long long)(now()-o->time),o->uses>1 ? "reused" : "first-observed");
}
void tas_image_probe_origin(id image,char *buffer,size_t capacity) {
    pthread_mutex_lock(&lock); describe_locked(find_locked(image,now()),buffer,capacity); pthread_mutex_unlock(&lock);
}
void tas_image_probe_assignment(uint64_t number,unsigned layer,id image,const char *decision) {
    if (number<9000000000ULL) return;
    char provenance[256],state[448]; time_t t=now();
    pthread_mutex_lock(&lock); Origin *o=find_locked(image,t); if (o) o->uses++;
    describe_locked(o,provenance,sizeof(provenance));
    /* A GIF result for the same body is context, not proof that this assigned
     * object passed through that decoder. Only preceding attempts qualify. */
    Attempt latest={0};
    if (o) for (unsigned i=0;i<ATTEMPTS;i++) if (!strcmp(attempts[i].kind ?: "","GIF") &&
        equal(attempts[i].key,o->key) && attempts[i].serial<=o->serial && t-attempts[i].time<EXPIRY && attempts[i].serial>latest.serial) latest=attempts[i];
    pthread_mutex_unlock(&lock);
    snprintf(state,sizeof(state),"layer=%u decision=%s input=%d %s",layer,decision,image!=nil,provenance);
    tas_emote_probe_record(number,layer,"decode-handoff",state,false);
    if (latest.serial) { snprintf(state,sizeof(state),"decode=%llu decoder=GIF result=%s frames=%llu evidence=assigned-body-prior-attempt",
        (unsigned long long)latest.serial,latest.success ? "image" : "nil",(unsigned long long)latest.frames);
        tas_emote_probe_record(number,layer,"decode-context",state,false); }
}
/* Return-site labels require a fresh, UUID-validated map for each donor.
 * No current map is installed; never apply historical executable offsets to
 * a different app build. This entire probe remains absent from normal builds. */
const char *tas_image_probe_caller(void *address) {
    (void)address;
    return "unknown";
}
static void install(Class cls,const char *name,const char *encoding,IMP replacement,IMP *original) {
    Method method=cls ? class_getInstanceMethod(cls,sel_registerName(name)) : NULL;
    if (method && !strcmp(method_getTypeEncoding(method),encoding) && !*original) *original=method_setImplementation(method,replacement);
}
void tas_image_probe_install(void) {
    install(objc_getClass("FLAnimatedImage"),"initWithAnimatedGIFData:optimalFrameCacheSize:predrawingEnabled:","@36@0:8@16Q24B32",(IMP)hook_gif,&gif_init);
    install(objc_getClass("UIImage"),"initWithData:","@24@0:8@16",(IMP)hook_ui,&ui_init);
    install(objc_getClass("UIImage"),"initWithData:scale:","@32@0:8@16d24",(IMP)hook_ui_scale,&ui_scale);
    install(objc_getClass("FLAnimatedImage"),"posterImage","@16@0:8",(IMP)hook_poster,&poster_get);
}
void tas_image_probe_status(char *buffer,size_t capacity) {
    pthread_mutex_lock(&lock);
    snprintf(buffer,capacity,"Decode hooks (GIF/UIImage/UIImage scale/poster): %s/%s/%s/%s\nDecode provenance: 256 weak results, 256 attempts, 64 response bodies; 600s expiry; cache origin unknown unless separately observed\nDecode calls/unmatched bodies/result evictions/oversize inputs: %llu/%llu/%llu/%llu\n",
        gif_init ? "installed" : "missing",ui_init ? "installed" : "missing",ui_scale ? "installed" : "missing",poster_get ? "installed" : "missing",
        (unsigned long long)calls,(unsigned long long)unmatched,(unsigned long long)evictions,(unsigned long long)__atomic_load_n(&oversize,__ATOMIC_RELAXED));
    pthread_mutex_unlock(&lock);
}
#endif
