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
#include <stdlib.h>
#include "TASEmoteWire.h"
extern int backtrace(void **,int);
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
    uint64_t cache_lookup,cache_number,cache_key;
    time_t cache_time;
    const char *cache_slot;
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
static IMP cache_get,request_imps[6];
static uint64_t cache_calls,cache_unmapped,cache_payloads,request_calls,lookup_serial,key_serial,cache_serial;
static struct { BodyKey key; uint64_t ordinal; time_t time; } url_keys[256];
static unsigned url_next,cache_next;
static struct { id weak; uint64_t ordinal; time_t time; } cache_ids[64];
static _Thread_local unsigned decision_depth;
static _Thread_local unsigned ui_depth,gif_depth;
static const char *creator(void *address);
static uintptr_t kit_offset(void *address);
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
    TASWireInfo wire=tas_wire_info((const void *)m0(data,"bytes"),key.bytes);char state[144];
    snprintf(state,sizeof(state),"wire=%s container-frames=%d animated=%d complete=%s evidence=container-metadata-not-decode",
        wire.kind,wire.frames,wire.animated,wire.complete ? "yes" : "no");
    tas_emote_probe_record(number,0,"image-wire-metadata",state,false);
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
    /* An exact weak result match is stronger than temporal proximity, but a
     * raw cache value still does not establish native expiry/type acceptance. */
    pthread_mutex_lock(&lock);o=find_locked(image,t);
    uint64_t lookup=o && o->cache_number==number && t-o->cache_time<EXPIRY ? o->cache_lookup : 0;
    if (lookup) snprintf(state,sizeof(state),"lookup=%llu key=%llu slot=%s object=%llu lookup-age=%llds evidence=prior-cache-payload-identity accepted=unknown",
        (unsigned long long)lookup,(unsigned long long)o->cache_key,o->cache_slot,(unsigned long long)o->object,(long long)(t-o->cache_time));
    pthread_mutex_unlock(&lock);
    if (lookup) tas_emote_probe_record(number,layer,"decision-handoff-cache",state,false);
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
    uintptr_t offset=kit_offset(address);
    if (offset==0x13ff4) return "native-static-imageio";
    if (offset==0x17994) return "native-task-static-imageio";
    return "unknown";
}
static uintptr_t kit_offset(void *address) {
    static const unsigned char uuid[16]={0xd2,0x20,0x69,0x02,0xf3,0xa0,0x3d,0xde,0x84,0xd5,0x4b,0x6a,0x7a,0x7c,0xeb,0x60};
    Dl_info info;if (!address || !dladdr(address,&info) || !info.dli_fbase || !uuid_matches(info.dli_fbase,uuid)) return 0;
    return (uintptr_t)address-(uintptr_t)info.dli_fbase;
}
const char *tas_image_probe_caller(void *address) {
    Dl_info info; if (!address || !dladdr(address,&info) || !info.dli_fbase || !donor(info.dli_fbase)) return "unknown";
    uintptr_t offset=(uintptr_t)address-(uintptr_t)info.dli_fbase;
    switch (offset) { case 0x2ccdf94: return "chat-static-result"; case 0x2ccfb84: return "chat-task-static-result";
        case 0x2cd052c: return "chat-animated-result"; case 0x2ccfb00: return "chat-task-animated-result"; default: return "unknown"; }
}
typedef struct { uint64_t number; BodyKey key; const char *kind; } RequestKey;
static const char *utf8(id object) { return responds(object,"UTF8String") ? (const char *)m0(object,"UTF8String") : NULL; }
static RequestKey request_key(id url) {
    RequestKey r={.kind="unknown"};
    if (!responds(url,"host") || !responds(url,"path")) return r;
    const char *host=utf8(m0(url,"host"));
    if (!host || strcmp(host,"static-cdn.jtvnw.net")) return r;
    const char *path=utf8(m0(url,"path"));
    if (!path || strncmp(path,"/emoticons/v2/",14)) return r;
    const char *p=path+14;uint64_t n=0;
    if (*p<'0' || *p>'9') return r;
    while (*p>='0' && *p<='9') { unsigned digit=*p++-'0';if (n>(UINT64_MAX-digit)/10) return r;n=n*10+digit; }
    if (*p!='/' || n<9000000000ULL) return r;
    r.number=n;
    r.kind=!strncmp(p,"/static/",8) ? "static" : !strncmp(p,"/animated/",10) ? "animated" : !strncmp(p,"/default/",9) ? "default" : "unknown";
    /* Full URL equality includes size/theme/query. The private hash is never
     * exported, only a launch-local ordinal; no URL or string is retained. */
    const char *s=responds(url,"absoluteString") ? utf8(m0(url,"absoluteString")) : NULL;
    size_t length=s ? strnlen(s,4097) : 0;
    if (length && length<=4096) {
        r.key=(BodyKey){1469598103934665603ULL,7809847782465536322ULL,length};
        for (size_t i=0;i<length;i++) { r.key.a=(r.key.a^(unsigned char)s[i])*1099511628211ULL;r.key.b=(r.key.b+(unsigned char)s[i]+1)*14029467366897019727ULL;r.key.b^=r.key.b>>29; }
    }
    return r;
}
static uint64_t key_ordinal_locked(BodyKey key,time_t t) {
    if (!key.bytes) return 0;
    for (unsigned i=0;i<256;i++) if (equal(url_keys[i].key,key) && t-url_keys[i].time<EXPIRY) { url_keys[i].time=t;return url_keys[i].ordinal; }
    unsigned s=url_next++%256;url_keys[s].key=key;url_keys[s].time=t;return url_keys[s].ordinal=++key_serial;
}
static uint64_t cache_ordinal_locked(id cache,time_t t) {
    for (unsigned i=0;i<64;i++) if (cache_ids[i].ordinal && t-cache_ids[i].time<EXPIRY) {
        id live=objc_loadWeakRetained(&cache_ids[i].weak);bool same=live==cache;if (live) objc_release(live);
        if (same) { cache_ids[i].time=t;return cache_ids[i].ordinal; }
    }
    unsigned s=cache_next++%64;objc_storeWeak(&cache_ids[s].weak,cache);cache_ids[s].time=t;return cache_ids[s].ordinal=++cache_serial;
}
/* These are returns from the inspected donor's two typed cache accessors.
 * The animated requester checks GIF storage first, then UIImage storage at
 * 0x29415c. Other static checks are not labeled animated fallback. */
static const char *cache_slot_for(uintptr_t offset) {
    switch (offset) {
    case 0x294094: case 0x295420: return "animated";
    case 0x291654: case 0x291ba4: case 0x292cac: case 0x29415c:
    case 0x29542c: case 0x2964cc: case 0x296b48: case 0x2971d0:
    case 0x2978a8: case 0x3b5ae0: case 0x3b62b4: return "static";
    default:return "unknown";
    }
}
static void cache_observed(id self,RequestKey r,id result,const char *slot,const char *path,bool typed_site) {
    if (!r.number) return;
    /* No guessed Swift calls. At the UUID-verified StoredItem boundary only,
     * a recognized specialization permits reading its pointer-sized value at
     * +16. Never message/store a candidate pointer: match existing live weak
     * origins instead. Unknown boxes, layouts and callers remain unknown. */
    id candidate=nil;
    if (result && typed_site) {
        Class cls=object_getClass(result);const char *name=class_getName(cls);
        if (name && strstr(name,"9TwitchKit17NetworkImageCache10StoredItem") &&
            (strstr(name,"So7UIImageC") || strstr(name,"So15FLAnimatedImageC")) && class_getInstanceSize(cls)>=24)
            memcpy(&candidate,(const char *)result+16,sizeof(candidate));
    }
    char state[320];time_t t=now();pthread_mutex_lock(&lock);cache_calls++;
    uint64_t lookup=++lookup_serial,key=key_ordinal_locked(r.key,t),cache=cache_ordinal_locked(self,t);
    Origin *o=find_locked(candidate,t);uint64_t object=o ? o->object : 0;
    if (!strcmp(slot,"unknown")) cache_unmapped++;
    if (o) { cache_payloads++;o->cache_lookup=lookup;o->cache_number=r.number;o->cache_key=key;o->cache_time=t;o->cache_slot=slot; }
    snprintf(state,sizeof(state),"lookup=%llu cache=%llu key=%llu url-kind=%s native-slot=%s path=%s raw=%s payload-object=%llu payload-decoder=%s accepted=unknown",
        (unsigned long long)lookup,(unsigned long long)cache,(unsigned long long)key,r.kind,slot,path,result ? "nonempty" : "empty",
        (unsigned long long)object,o ? o->kind : "unknown");
    pthread_mutex_unlock(&lock);tas_emote_probe_record(r.number,0,"decision-cache-lookup",state,false);
}
static id hook_cache_get(id self,SEL sel,id key) {
    uintptr_t site=kit_offset(__builtin_return_address(0));
    /* Filter the shared native cache read before parsing any key or unwinding.
     * Every other application's NSCache lookup stays a direct pass-through. */
    if (decision_depth || (site!=0x13978 && site!=0x169b0 && site!=0x2922d4))
        return ((id (*)(id,SEL,id))cache_get)(self,sel,key);
    decision_depth++;RequestKey r=request_key(key);
    bool typed_site=site!=0x169b0;
    const char *slot=site==0x169b0 ? "image-enum" : site==0x2922d4 ? "static" : "unknown";
    const char *path=site==0x169b0 ? "task-cache-check" : site==0x2922d4 ? "batch-static-cache-check" : "unknown";
    /* The task cache bridges a Swift image enum, not StoredItem. Observe only
     * empty/nonempty at that boundary; never interpret its box or enum ABI. */
    if (r.number && site==0x13978) {
        void *frames[32];int count=backtrace(frames,32);
        for (int i=0;i<count;i++) {
            uintptr_t offset=kit_offset(frames[i]);const char *found=cache_slot_for(offset);
            if (strcmp(found,"unknown")) { slot=found;path=offset==0x29415c ? "animated-request-static-fallback" : offset==0x294094 ? "animated-request-first-check" : "other-native-check";break; }
        }
    }
    id result=((id (*)(id,SEL,id))cache_get)(self,sel,key);
    cache_observed(self,r,result,slot,path,typed_site);decision_depth--;return result;
}
static void request_observed(id url,const char *entry,bool store_known,BOOL store,bool user_known,BOOL user) {
    RequestKey r=request_key(url);if (!r.number) return;
    time_t t=now();char state[192];pthread_mutex_lock(&lock);request_calls++;uint64_t key=key_ordinal_locked(r.key,t);pthread_mutex_unlock(&lock);
    snprintf(state,sizeof(state),"entry=%s key=%llu url-kind=%s store-memory=%s user-initiated=%s",
        entry,(unsigned long long)key,r.kind,store_known ? store ? "yes" : "no" : "default",user_known ? user ? "yes" : "no" : "default");
    tas_emote_probe_record(r.number,0,"decision-request-entry",state,false);
}
#define REQUEST_BASIC(name,index,label) \
static id name(id self,SEL sel,id url,double scale,double persist) { \
    request_observed(url,label,false,NO,false,NO); \
    return ((id (*)(id,SEL,id,double,double))request_imps[index])(self,sel,url,scale,persist); }
REQUEST_BASIC(hook_request_static,0,"static")
REQUEST_BASIC(hook_request_file,2,"static-with-file")
REQUEST_BASIC(hook_request_animated,4,"animated")
#define REQUEST_FLAGS(name,index,label) \
static id name(id self,SEL sel,id url,double scale,double persist,BOOL store,BOOL user) { \
    request_observed(url,label,true,store,true,user); \
    return ((id (*)(id,SEL,id,double,double,BOOL,BOOL))request_imps[index])(self,sel,url,scale,persist,store,user); }
REQUEST_FLAGS(hook_request_static_flags,1,"static")
REQUEST_FLAGS(hook_request_file_flags,3,"static-with-file")
static id hook_request_animated_flags(id self,SEL sel,id url,double scale,double persist,BOOL user) {
    request_observed(url,"animated",false,NO,true,user);
    return ((id (*)(id,SEL,id,double,double,BOOL))request_imps[5])(self,sel,url,scale,persist,user);
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
    install(objc_getClass("NSCache"),"objectForKey:","@24@0:8@16",(IMP)hook_cache_get,&cache_get);
    Class requester=objc_getClass("_TtC9TwitchKit21NetworkImageRequester");
    install(requester,"imageAtURL:withScale:persistingFor:","@40@0:8@16d24d32",(IMP)hook_request_static,&request_imps[0]);
    install(requester,"imageAtURL:withScale:persistingFor:storeInMemoryCache:userInitiated:","@48@0:8@16d24d32B40B44",(IMP)hook_request_static_flags,&request_imps[1]);
    install(requester,"imageWithCacheFileURLAtURL:withScale:persistingFor:","@40@0:8@16d24d32",(IMP)hook_request_file,&request_imps[2]);
    install(requester,"imageWithCacheFileURLAtURL:withScale:persistingFor:storeInMemoryCache:userInitiated:","@48@0:8@16d24d32B40B44",(IMP)hook_request_file_flags,&request_imps[3]);
    install(requester,"animatedImageAtURL:withStaticScale:persistingFor:","@40@0:8@16d24d32",(IMP)hook_request_animated,&request_imps[4]);
    install(requester,"animatedImageAtURL:withStaticScale:persistingFor:userInitiated:","@44@0:8@16d24d32B40",(IMP)hook_request_animated_flags,&request_imps[5]);
}
void tas_image_probe_status(char *buffer,size_t capacity) {
    pthread_mutex_lock(&lock);
    snprintf(buffer,capacity,"Decode hooks (GIF/UIImage/UIImage scale/poster): %s/%s/%s/%s\nDecode provenance: 1024 weak results, 256 attempts, 64 response bodies, 256 weak raster owners; 600s observation expiry; live provider results protected from unrelated image traffic\nDecode calls/unmatched bodies/result evictions/oversize inputs: %llu/%llu/%llu/%llu\nResult hooks (CGImage/CGImage scale/CGImage getter/native response init/image): %s/%s/%s/%s/%s\nResult observations (CG constructors/shared raster/native response/unobserved assignment/repeated identity): %llu/%llu/%llu/%llu/%llu\nCache hits remain unknown; file presence and repeated identity do not establish cache retrieval\n",
        gif_init ? "installed" : "missing",ui_init ? "installed" : "missing",ui_scale ? "installed" : "missing",poster_get ? "installed" : "missing",
        (unsigned long long)calls,(unsigned long long)unmatched,(unsigned long long)evictions,(unsigned long long)__atomic_load_n(&oversize,__ATOMIC_RELAXED),
        cg_init ? "installed" : "missing",cg_scale ? "installed" : "missing",cg_get ? "installed" : "missing",response_init ? "installed" : "missing",response_get ? "installed" : "missing",
        (unsigned long long)cg_calls,(unsigned long long)cg_shared,(unsigned long long)response_calls,(unsigned long long)unknown_assignments,(unsigned long long)weak_reuses);
    size_t used=strnlen(buffer,capacity);
    if (used<capacity) snprintf(buffer+used,capacity-used,
        "Decision hooks (native cache/static requests/file requests/animated requests): %s/%s/%s/%s\nDecision observations (cache reads/unknown slots/matched payloads/request entries): %llu/%llu/%llu/%llu\nDecision identities: 256 private URL keys, 64 weak caches; 600s expiry. Raw nonempty cache values may fail native type/expiry checks. Direct Swift request entries can bypass Objective-C hooks; zero entries are not proof of no request.\n",
        cache_get ? "installed" : "missing",request_imps[0] && request_imps[1] ? "installed" : "missing",request_imps[2] && request_imps[3] ? "installed" : "missing",request_imps[4] && request_imps[5] ? "installed" : "missing",
        (unsigned long long)cache_calls,(unsigned long long)cache_unmapped,(unsigned long long)cache_payloads,(unsigned long long)request_calls);
    pthread_mutex_unlock(&lock);
}
#endif
