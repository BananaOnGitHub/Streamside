/* Temporary read-only image provenance. All identities are weak, bounded and
 * private. Neither bytes nor fingerprints nor native addresses enter reports. */
#include "TASEmoteImageProbe.h"
#if TAS_EMOTE_DIAGNOSTIC
#include <objc/message.h>
#include <pthread.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
extern id objc_storeWeak(id *,id);
extern id objc_loadWeakRetained(id *);
extern void objc_release(id);
enum { ORIGINS=1024, ATTEMPTS=256, BODIES=64, IDS=32, EXPIRY=600, MAX_BYTES=8*1024*1024 };
typedef struct { uint64_t a,b; size_t bytes; } BodyKey;
typedef struct {
    id weak;
    uint64_t serial,frames,uses,object,number,parent;
    time_t time,seen,assigned;
    BodyKey key;
    const char *kind,*creator;
    bool construction,cache_file;
} Origin;
/* A borrowed CGImage identity is valid only while its UIImage owner is live.
 * These weak owners never retain a raster or an animated image. */
static struct { id weak; void *cg; uint64_t object; time_t time; } rasters[256];
static unsigned raster_next;
typedef struct { uint64_t serial,frames; time_t time; BodyKey key; const char *kind; bool success; } Attempt;
typedef struct { BodyKey key; time_t time; uint64_t ids[IDS]; unsigned count; } Body;
static Origin origins[ORIGINS];
static Attempt attempts[ATTEMPTS];
static Body bodies[BODIES];
static unsigned origin_next,attempt_next,body_next;
static uint64_t serial,calls,unmatched,evictions,oversize,object_serial,cg_calls,cg_shared,response_calls,unknown_assignments,weak_reuses;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static IMP gif_init,ui_init,ui_scale,poster_get;
static IMP cg_init,cg_scale,cg_get,response_init,response_get;
static _Thread_local unsigned ui_depth,gif_depth;
static const char *creator(void *address);
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
        if (!origins[i].object || t-origins[i].seen>=EXPIRY) continue;
        id live=objc_loadWeakRetained(&origins[i].weak); bool same=live==image;
        if (live) objc_release(live);
        if (same) return &origins[i];
    }
    return NULL;
}
static Origin *put_locked(id image,Attempt a,const char *kind) {
    if (!image) return NULL;
    time_t observed=now();
    Origin *existing=find_locked(image,observed);
    if (existing) {
        /* A nested CG constructor does not hide the outer data decoder's
         * stronger response-body provenance. Preserve the object ordinal. */
        if (a.key.bytes && !existing->key.bytes) { existing->serial=a.serial;existing->frames=a.frames;existing->key=a.key;existing->kind=kind;existing->time=a.time;existing->construction=true; }
        existing->seen=observed;
        return existing;
    }
    unsigned slot=ORIGINS;
    for (unsigned i=0;i<ORIGINS;i++) {
        unsigned j=(origin_next+i)%ORIGINS;
        if (!origins[j].object || observed-origins[j].seen>=EXPIRY) { slot=j;break; }
        id live=objc_loadWeakRetained(&origins[j].weak);
        if (live) objc_release(live);
        else { slot=j;break; }
    }
    /* Protect results assigned to provider chat from unrelated UIKit traffic.
     * If every slot is protected, the oldest protected result is still bounded. */
    if (slot==ORIGINS) {
        for (unsigned i=0;i<ORIGINS;i++) if (!origins[i].number && (slot==ORIGINS || origins[i].seen<origins[slot].seen)) slot=i;
        if (slot==ORIGINS) for (unsigned i=0;i<ORIGINS;i++) if (slot==ORIGINS || origins[i].seen<origins[slot].seen) slot=i;
    }
    origin_next=(slot+1)%ORIGINS;Origin *o=&origins[slot];
    if (o->object) evictions++;
    objc_storeWeak(&o->weak,nil);
    memset(o,0,sizeof(*o));
    o->serial=a.serial; o->frames=a.frames; o->time=a.time; o->seen=observed; o->key=a.key; o->kind=kind;
    o->object=++object_serial;o->creator="unknown";o->construction=a.serial!=0;
    objc_storeWeak(&o->weak,image);
    return o;
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
    if (!gif_depth) {
        decoded(data,result,"GIF",integer(result,"frameCount"));
        /* posterImage is a verified cached ivar getter, not lazy frame decode. */
        if (result && poster_get) m0(result,"posterImage");
    }
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
    if (o) { uint64_t parent=o->object;Attempt a={o->serial,o->frames,o->time,o->key,o->kind,true}; Origin *p=put_locked(result,a,"GIF-poster"); if (p) { p->parent=parent;p->construction=true;p->creator="GIF-poster-getter"; } }
    pthread_mutex_unlock(&lock); return result;
}
static void describe_locked(Origin *o,char *buffer,size_t capacity) {
    if (!o) { snprintf(buffer,capacity,"decode=unknown reuse=unknown source=unknown"); return; }
    char decode[32];if (o->serial) snprintf(decode,sizeof(decode),"%llu",(unsigned long long)o->serial);else snprintf(decode,sizeof(decode),"unknown");
    snprintf(buffer,capacity,"object=%llu decode=%s decoder=%s frames=%llu age=%llds reuse=%s source=%s creator=%s parent=%llu file=%d",
        (unsigned long long)o->object,decode,o->kind,(unsigned long long)o->frames,(long long)(now()-o->time),o->uses>1 ? "reused" : "first-observed",
        o->construction ? "observed-construction" : !strcmp(o->kind,"native-response") ? "native-response-observed" : "first-seen-at-handoff",o->creator,(unsigned long long)o->parent,o->cache_file);
}
void tas_image_probe_origin(id image,char *buffer,size_t capacity) {
    pthread_mutex_lock(&lock);time_t t=now();Origin *o=find_locked(image,t);
    if (o && o->number) o->seen=t;
    describe_locked(o,buffer,capacity);pthread_mutex_unlock(&lock);
}
void tas_image_probe_assignment(uint64_t number,unsigned layer,id image,const char *decision) {
    if (number<9000000000ULL) return;
    char provenance[320],state[576],creation[384]; time_t t=now();bool first=false;
    pthread_mutex_lock(&lock); Origin *o=find_locked(image,t);
    if (image && !o) { Attempt a={.time=t};o=put_locked(image,a,"unobserved");unknown_assignments++; }
    if (o) {
        first=!o->uses;o->uses++;if (o->uses>1) weak_reuses++;
        o->number=number;o->seen=o->assigned=t;
    }
    describe_locked(o,provenance,sizeof(provenance));
    if (first) {
        uint64_t ids[IDS];unsigned count=response_ids_locked(o->key,t,ids);bool matched=false;
        for (unsigned i=0;i<count;i++) if (ids[i]==number) matched=true;
        snprintf(creation,sizeof(creation),"layer=%u %s body=%s cache-hit=unknown",layer,provenance,matched ? "matched-response" : o->key.bytes ? "decoded-bytes-only" : "unknown");
    }
    /* A GIF result for the same body is context, not proof that this assigned
     * object passed through that decoder. Only preceding attempts qualify. */
    Attempt latest={0};
    if (o) for (unsigned i=0;i<ATTEMPTS;i++) if (!strcmp(attempts[i].kind ?: "","GIF") &&
        equal(attempts[i].key,o->key) && attempts[i].serial<=o->serial && t-attempts[i].time<EXPIRY && attempts[i].serial>latest.serial) latest=attempts[i];
    pthread_mutex_unlock(&lock);
    if (first) tas_emote_probe_record(number,layer,"result-origin",creation,false);
    snprintf(state,sizeof(state),"layer=%u decision=%s input=%d %s",layer,decision,image!=nil,provenance);
    tas_emote_probe_record(number,layer,"decode-handoff",state,false);
    if (latest.serial) { snprintf(state,sizeof(state),"decode=%llu decoder=GIF result=%s frames=%llu evidence=assigned-body-prior-attempt",
        (unsigned long long)latest.serial,latest.success ? "image" : "nil",(unsigned long long)latest.frames);
        tas_emote_probe_record(number,layer,"decode-context",state,false); }
}
static Origin *raster_source_locked(void *cg,time_t t) {
    if (!cg) return NULL;
    for (unsigned i=0;i<256;i++) {
        if (rasters[i].cg!=cg || t-rasters[i].time>=EXPIRY) continue;
        id owner=objc_loadWeakRetained(&rasters[i].weak);
        Origin *o=owner ? find_locked(owner,t) : NULL;
        if (owner) objc_release(owner);
        if (o && o->object==rasters[i].object) return o;
    }
    return NULL;
}
static void remember_raster_locked(id owner,void *cg,Origin *o,time_t t) {
    if (!owner || !cg || !o) return;
    unsigned slot=256;
    for (unsigned i=0;i<256;i++) if (rasters[i].cg==cg && rasters[i].object==o->object) { slot=i;break; }
    if (slot==256) slot=raster_next++%256;
    objc_storeWeak(&rasters[slot].weak,owner);rasters[slot].cg=cg;rasters[slot].object=o->object;rasters[slot].time=t;
}
static void constructed(id result,void *cg,const char *callsite) {
    if (!result) return;
    time_t t=now();pthread_mutex_lock(&lock);cg_calls++;
    Origin *parent=raster_source_locked(cg,t);Attempt a={.time=t};
    Origin *existing=find_locked(result,t);
    if (parent && existing && parent->object==existing->object) parent=NULL;
    /* A shared CGImage can establish a copy relationship; it does not imply
     * that a multi-frame GIF became a still or that a cache lookup occurred. */
    if (parent) { a.serial=parent->serial;a.key=parent->key; }
    uint64_t parent_object=parent ? parent->object : 0;
    Origin *o=put_locked(result,a,"UIImage-CGImage");
    if (o) {
        o->construction=true;
        if (strcmp(callsite,"unknown") || !strcmp(o->creator,"unknown")) o->creator=callsite;
        if (parent_object) o->parent=parent_object;
        remember_raster_locked(result,cg,o,t);
    }
    if (parent_object) cg_shared++;
    pthread_mutex_unlock(&lock);
}
static id hook_cg(id self,SEL sel,void *cg) {
    const char *site=creator(__builtin_return_address(0));
    id result=((id (*)(id,SEL,void *))cg_init)(self,sel,cg);
    constructed(result,cg,site);return result;
}
static id hook_cg_scale(id self,SEL sel,void *cg,double scale,long orientation) {
    const char *site=creator(__builtin_return_address(0));
    id result=((id (*)(id,SEL,void *,double,long))cg_scale)(self,sel,cg,scale,orientation);
    constructed(result,cg,site);return result;
}
static void *hook_cg_get(id self,SEL sel) {
    void *cg=((void *(*)(id,SEL))cg_get)(self,sel);
    time_t t=now();pthread_mutex_lock(&lock);remember_raster_locked(self,cg,find_locked(self,t),t);pthread_mutex_unlock(&lock);return cg;
}
static void response_observed(id image,bool file) {
    if (!image) return;
    time_t t=now();pthread_mutex_lock(&lock);response_calls++;
    Origin *o=find_locked(image,t);
    if (!o) { Attempt a={.time=t};o=put_locked(image,a,"native-response"); }
    if (o) o->cache_file|=file;
    pthread_mutex_unlock(&lock);
}
static id hook_response_init(id self,SEL sel,id image,id url) {
    id result=((id (*)(id,SEL,id,id))response_init)(self,sel,image,url);
    if (result) response_observed(image,url!=nil);return result;
}
static id hook_response_get(id self,SEL sel) {
    id image=((id (*)(id,SEL))response_get)(self,sel);response_observed(image,false);return image;
}
/* Only label donor-native callers after verifying the complete Mach-O UUID. */
static bool uuid_matches(const unsigned char *base,const unsigned char uuid[16]) {
    uint32_t magic,n,size; memcpy(&magic,base,4); if (magic!=0xfeedfacf) return false;
    memcpy(&n,base+16,4); memcpy(&size,base+20,4); if (size>65536 || n>1024) return false;
    size_t p=32,end=32+size;
    for (unsigned i=0;i<n;i++) { if (p+8>end) return false; uint32_t cmd,bytes; memcpy(&cmd,base+p,4); memcpy(&bytes,base+p+4,4);
        if (bytes<8 || p+bytes>end) return false;
        if (cmd==0x1b) return bytes==24 && !memcmp(base+p+8,uuid,16);
        p+=bytes;
    }
    return false;
}
static bool donor(const unsigned char *base) {
    static const unsigned char uuid[16]={0x96,0x0f,0x52,0x32,0x0e,0xb5,0x3e,0xcc,0x80,0x00,0x15,0x74,0x6c,0xb1,0xe3,0x7b};
    return uuid_matches(base,uuid);
}
static const char *creator(void *address) {
    static const unsigned char uuid[16]={0xd2,0x20,0x69,0x02,0xf3,0xa0,0x3d,0xde,0x84,0xd5,0x4b,0x6a,0x7a,0x7c,0xeb,0x60};
    Dl_info info;if (!address || !dladdr(address,&info) || !info.dli_fbase || !uuid_matches(info.dli_fbase,uuid)) return "unknown";
    uintptr_t offset=(uintptr_t)address-(uintptr_t)info.dli_fbase;
    if (offset==0x13ff4) return "native-static-imageio";
    if (offset==0x17994) return "native-task-static-imageio";
    return "unknown";
}
const char *tas_image_probe_caller(void *address) {
    Dl_info info; if (!address || !dladdr(address,&info) || !info.dli_fbase || !donor(info.dli_fbase)) return "unknown";
    uintptr_t offset=(uintptr_t)address-(uintptr_t)info.dli_fbase;
    switch (offset) { case 0x2ccdf94: return "chat-static-result"; case 0x2ccfb84: return "chat-task-static-result";
        case 0x2cd052c: return "chat-animated-result"; case 0x2ccfb00: return "chat-task-animated-result"; default: return "unknown"; }
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
    install(objc_getClass("UIImage"),"initWithCGImage:","@24@0:8^{CGImage=}16",(IMP)hook_cg,&cg_init);
    install(objc_getClass("UIImage"),"initWithCGImage:scale:orientation:","@40@0:8^{CGImage=}16d24q32",(IMP)hook_cg_scale,&cg_scale);
    install(objc_getClass("UIImage"),"CGImage","^{CGImage=}16@0:8",(IMP)hook_cg_get,&cg_get);
    Class response=objc_getClass("_TtCC9TwitchKit21NetworkImageRequester29NetworkImageRequesterResponse");
    install(response,"initWithImage:cacheFileURL:","@32@0:8@16@24",(IMP)hook_response_init,&response_init);
    install(response,"image","@16@0:8",(IMP)hook_response_get,&response_get);
}
void tas_image_probe_status(char *buffer,size_t capacity) {
    pthread_mutex_lock(&lock);
    snprintf(buffer,capacity,"Decode hooks (GIF/UIImage/UIImage scale/poster): %s/%s/%s/%s\nDecode provenance: 1024 weak results, 256 attempts, 64 response bodies, 256 weak raster owners; 600s observation expiry; live provider results protected from unrelated image traffic\nDecode calls/unmatched bodies/result evictions/oversize inputs: %llu/%llu/%llu/%llu\nResult hooks (CGImage/CGImage scale/CGImage getter/native response init/image): %s/%s/%s/%s/%s\nResult observations (CG constructors/shared raster/native response/unobserved assignment/repeated identity): %llu/%llu/%llu/%llu/%llu\nCache hits remain unknown; file presence and repeated identity do not establish cache retrieval\n",
        gif_init ? "installed" : "missing",ui_init ? "installed" : "missing",ui_scale ? "installed" : "missing",poster_get ? "installed" : "missing",
        (unsigned long long)calls,(unsigned long long)unmatched,(unsigned long long)evictions,(unsigned long long)__atomic_load_n(&oversize,__ATOMIC_RELAXED),
        cg_init ? "installed" : "missing",cg_scale ? "installed" : "missing",cg_get ? "installed" : "missing",response_init ? "installed" : "missing",response_get ? "installed" : "missing",
        (unsigned long long)cg_calls,(unsigned long long)cg_shared,(unsigned long long)response_calls,(unsigned long long)unknown_assignments,(unsigned long long)weak_reuses);
    pthread_mutex_unlock(&lock);
}
#endif
