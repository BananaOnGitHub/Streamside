/* Passive observation only. No provider lookup, message rewrite, prop mutation,
 * request redirect, geometry adjustment, or callback replacement. Each wrapper
 * invokes its saved IMP exactly once with the original arguments and result.
 * This file is compiled only into the isolated RN diagnostic build. */
#include "TASRNProbe.h"
#ifndef TAS_RN_CHAT_DIAGNOSTIC
#define TAS_RN_CHAT_DIAGNOSTIC 0
#endif
#if TAS_RN_CHAT_DIAGNOSTIC
#include <objc/runtime.h>
#include <objc/message.h>
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <stdarg.h>

typedef unsigned long U;
typedef long I;
typedef struct { double width, height; } Size;
typedef struct { double x, y; } Point;
typedef struct { Point origin; Size size; } Rect;
typedef struct { U location, length; } Range;
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_storeWeak(id *, id);
extern id objc_loadWeakRetained(id *);
#define ADD(x,n) ((void)__atomic_add_fetch(&(x),(n),__ATOMIC_RELAXED))
#define INC(x) ADD(x,1)
#define GET(x) __atomic_load_n(&(x),__ATOMIC_RELAXED)
#define INPUT "_TtC21twitch_rn_emote_input20TwitchEmoteInputView"
#define ATTACHMENT "_TtC21twitch_rn_emote_input21TwitchEmoteAttachment"
enum { CONNECT, SOCKET_OPEN, DELEGATE, RECEIVE, EVENT, SEND,
       SURFACE, ROOT, FABRIC, SOURCE, BUNDLE, HOST_BUNDLE,
       EMOTE_MAP, TOKEN_MAP, TEMPLATE, VALUE, CHANGE, EDIT, INPUT_LAYOUT,
       ATTACH_BOUNDS, IMAGE_REQUEST, HTTP_REQUEST, HTTP_DONE,
       IMAGE_RECEIVE, IMAGE_SET, ANIMATION_SET, ANIMATION_START, DECODE,
       HOST_SURFACE_MODE, HOST_SURFACE, FABRIC_INIT, FABRIC_START, HOSTING_WINDOW,
       HOST_JS, INSTANCE_JS, CALLABLE_JS, DISPATCH_EVENT, INPUT_SELECTION,
       INPUT_BEGIN, INPUT_END, SUBMIT_SET, SOCKET_SEND, SOCKET_SEND_DATA,
       NETWORK_BUILD, HOOK_COUNT };
typedef struct {
    const char *class_name, *selector, *encoding;
    bool meta;
    IMP replacement, original;
    uint64_t calls;
    char receiver[128], caller[64];
    uintptr_t caller_offset;
    bool rejected;
} Hook;
static Hook hooks[HOOK_COUNT];
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t install_lock=PTHREAD_MUTEX_INITIALIZER;
static _Thread_local unsigned delivery_depth;
static uint64_t irc_connects, irc_opens, rn_delegates, received_text, received_other;
static uint64_t irc_deliveries, js_deliveries, js_in_receive, outbound_privmsg;
static uint64_t incoming_privmsg, incoming_roomstate, incoming_emote_tag, js_privmsg, js_emote_tag;
static uint64_t oversized_text, newline_edits, maps_nonempty, token_maps_nonempty;
static uint64_t map_entries, token_entries, input_square, input_wide;
static uint64_t image_emote_requests, http_emote_requests, image_square, image_wide;
static uint64_t animated_results, http_errors;
static char delegate_class[128], session_class[128], task_class[128], image_class[128];
static char surfaces[8][96];
static unsigned surface_count;
static uint64_t surface_overflow;
static id bundle_data[4]; /* Weak identity only; never retains a bundle body. */
static uint64_t bundle_hash[4], bundle_bytes[4];
static unsigned bundle_kind[4], bundle_version[4], next_bundle;
static uint64_t bundle_oversize, bundle_unreadable;
static uint64_t bundle_locations[4];
/* Only fixed categories and numeric observations are retained by build 52. */
static uint64_t js_module_other, js_module_device, js_module_app, js_socket_handoff;
static uint64_t input_values_empty, input_values_nonempty, input_values_other;
static uint64_t map_shapes[2][5], map_samples[2][4];
static uint64_t native_events[6], gql_operations[6], gql_oversize, gql_unreadable;
static uint64_t legacy_send_privmsg, data_send_privmsg;
enum { TRACE_SURFACE, TRACE_MAP, TRACE_VALUE_EMPTY, TRACE_VALUE_NONEMPTY,
       TRACE_INPUT_CHANGE, TRACE_INPUT_SELECTION, TRACE_SUBMIT, TRACE_IRC_SEND,
       TRACE_GQL_SEND, TRACE_GQL_CATALOG, TRACE_KIND_COUNT };
static const char *trace_names[]={"surface", "catalog-map", "value-empty", "value-nonempty",
    "input-change", "input-selection", "submit-event", "IRC-send", "GQL-send", "GQL-catalog"};
static struct { uint64_t sequence; unsigned kind; } trace_rows[48];
static uint64_t trace_sequence;
static unsigned trace_next, trace_count;
static void trace(unsigned category) {
    pthread_mutex_lock(&lock);
    trace_rows[trace_next].sequence=++trace_sequence;trace_rows[trace_next].kind=category;
    trace_next=(trace_next+1)%48;if (trace_count<48) trace_count++;
    pthread_mutex_unlock(&lock);
}

static id m0(id o,const char *s) { return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static id m1(id o,const char *s,id a) { return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a); }
static id str(const char *s) { return m1((id)objc_getClass("NSString"),"stringWithUTF8String:",(id)s); }
static bool kind(id o,const char *name) {
    Class c=objc_getClass(name);
    return o && c && ((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),c);
}
static bool equals(id o,const char *s) {
    return kind(o,"NSString") && ((BOOL (*)(id,SEL,id))objc_msgSend)(o,sel_registerName("isEqualToString:"),str(s));
}
static U count(id o) { return ((U (*)(id,SEL))objc_msgSend)(o,sel_registerName("count")); }
static const char *utf8(id o) { return kind(o,"NSString") ? (const char *)m0(o,"UTF8String") : NULL; }
static bool irc_url(id url) { return kind(url,"NSURL") && equals(m0(url,"host"),"irc-ws.chat.twitch.tv"); }
static bool emote_url(id url) {
    if (!kind(url,"NSURL") || !equals(m0(url,"host"),"static-cdn.jtvnw.net")) return false;
    const char *p=utf8(m0(url,"path"));
    return p && !strncmp(p,"/emoticons/v2/",14);
}
static unsigned url_kind(id url) {
    if (!kind(url,"NSURL")) return 0;
    if (!((BOOL (*)(id,SEL))objc_msgSend)(url,sel_registerName("isFileURL"))) return 3;
    id main=m0((id)objc_getClass("NSBundle"),"mainBundle");
    id embedded=((id (*)(id,SEL,id,id))objc_msgSend)(main,sel_registerName("URLForResource:withExtension:"),str("index.ios"),str("bundle"));
    return embedded && ((BOOL (*)(id,SEL,id))objc_msgSend)(url,sel_registerName("isEqual:"),embedded) ? 1 : 2;
}
static void copy_class(char *dst,size_t n,id object) {
    snprintf(dst,n,"%s",object ? class_getName(object_getClass(object)) : "nil");
}
static void hit(unsigned slot,id self,void *caller) {
    uint64_t n=__atomic_add_fetch(&hooks[slot].calls,1,__ATOMIC_RELAXED);
    if (n!=1) return;
    /* Capture first call only. No stack walking on per-message/image paths. */
    pthread_mutex_lock(&lock);
    if (!hooks[slot].receiver[0]) {
        copy_class(hooks[slot].receiver,sizeof(hooks[slot].receiver),self);
        Dl_info info;
        if (dladdr(caller,&info) && info.dli_fname) {
            const char *base=strrchr(info.dli_fname,'/');base=base ? base+1 : info.dli_fname;
            /* Never persist an arbitrary path, even after truncation. */
            const char *allowed[]={"Twitch","React","ReactNativeDependencies","twitch_rn_emote_input",
                "twitch_rn_animated_image","HotUpdater","ReactCodegen","hermes"};
            const char *owner="other";
            for (unsigned i=0;i<sizeof(allowed)/sizeof(*allowed);i++) if (!strcmp(base,allowed[i])) owner=allowed[i];
            snprintf(hooks[slot].caller,sizeof(hooks[slot].caller),"%s",owner);
            hooks[slot].caller_offset=(uintptr_t)caller-(uintptr_t)info.dli_fbase;
        }
    }
    pthread_mutex_unlock(&lock);
}
#define HIT(slot) hit(slot,self,__builtin_return_address(0))

/* Examine IRC headers transiently. Only command/category counts leave this
 * function; no words, IDs, tags, string hashes, or message objects are saved. */
static U classify(id data,bool js,bool outbound) {
    U privmsg_count=0;
    if (!kind(data,"NSString")) { if (!js && !outbound) INC(received_other);return 0; }
    if (!js && !outbound) INC(received_text);
    U chars=((U (*)(id,SEL))objc_msgSend)(data,sel_registerName("length"));
    if (chars>65536) { INC(oversized_text);return 0; }
    const char *s=utf8(data);if (!s) return 0;
    while (*s) {
        const char *end=strchr(s,'\n');if (!end) end=s+strlen(s);
        const char *p=s;bool emotes=false;
        if (p<end && *p=='@') {
            const char *tag_end=memchr(p,' ',(size_t)(end-p));
            if (!tag_end) break;
            for (const char *t=p+1;t<tag_end;t++) {
                if ((t==p+1 || t[-1]==';') && tag_end-t>=8 && !strncmp(t,"emotes=",7) && t[7]!=';' && t[7]!=' ') emotes=true;
            }
            p=tag_end+1;
        }
        if (p<end && *p==':') { const char *space=memchr(p,' ',(size_t)(end-p));if (!space) break;p=space+1; }
        while (p<end && *p==' ') p++;
        bool priv=end-p>=8 && !strncmp(p,"PRIVMSG ",8);
        bool room=end-p>=10 && !strncmp(p,"ROOMSTATE ",10);
        if (priv) privmsg_count++;
        if (outbound) { if (priv) INC(outbound_privmsg); }
        else if (js) { if (priv) INC(js_privmsg);if (priv && emotes) INC(js_emote_tag); }
        else { if (priv) INC(incoming_privmsg);if (room) INC(incoming_roomstate);if (priv && emotes) INC(incoming_emote_tag); }
        if (!*end) break;
        s=end+1;
    }
    return privmsg_count;
}
static void surface_name(id value) {
    trace(TRACE_SURFACE);
    const char *s=utf8(value);if (!s) return;
    size_t n=strnlen(s,96);if (!n || n>=96) return;
    for (size_t i=0;i<n;i++) if (!((s[i]>='a' && s[i]<='z') || (s[i]>='A' && s[i]<='Z') ||
        (s[i]>='0' && s[i]<='9') || s[i]=='_' || s[i]=='-' || s[i]=='.')) return;
    pthread_mutex_lock(&lock);
    for (unsigned i=0;i<surface_count;i++) if (!strcmp(surfaces[i],s)) { pthread_mutex_unlock(&lock);return; }
    if (surface_count<8) snprintf(surfaces[surface_count++],96,"%s",s);else INC(surface_overflow);
    pthread_mutex_unlock(&lock);
}
/* Never inspect catalog keys or retain IDs/tokens/URLs. Bounded value-type
 * samples distinguish a string-ID map from a structured-object map. */
static void map_shape(id value,unsigned slot) {
    unsigned shape=!value ? 0 : kind(value,"NSDictionary") ? 1 : kind(value,"NSArray") ? 2 : kind(value,"NSString") ? 3 : 4;
    INC(map_shapes[slot][shape]);
    if (shape!=1) return;
    trace(TRACE_MAP);id enumerator=m0(value,"objectEnumerator");
    for (unsigned i=0;i<32;i++) {
        id entry=m0(enumerator,"nextObject");if (!entry) break;
        unsigned t=kind(entry,"NSString") ? 0 : kind(entry,"NSNumber") ? 1 : kind(entry,"NSDictionary") ? 2 : 3;
        INC(map_samples[slot][t]);
    }
}
static void value_shape(id value) {
    if (!kind(value,"NSString")) { INC(input_values_other);return; }
    U n=((U (*)(id,SEL))objc_msgSend)(value,sel_registerName("length"));
    if (n) { INC(input_values_nonempty);trace(TRACE_VALUE_NONEMPTY); }
    else { INC(input_values_empty);trace(TRACE_VALUE_EMPTY); }
}
static id array_at(id array,U index) { return ((id (*)(id,SEL,U))objc_msgSend)(array,sel_registerName("objectAtIndex:"),index); }
static void js_handoff(id module,id method,id args) {
    if (equals(module,"RCTDeviceEventEmitter") && equals(method,"emit")) {
        INC(js_module_device);
        if (kind(args,"NSArray") && count(args)>=2 && equals(array_at(args,0),"websocketMessage")) INC(js_socket_handoff);
    } else if (equals(module,"AppRegistry") && equals(method,"runApplication")) INC(js_module_app);
    else INC(js_module_other);
    /* No arbitrary module/method names or JS arguments are stored. This is
     * native scheduling of JS work, not observation of a JS function executing. */
}
static void observe_native_event(id event) {
    if (!event || !((BOOL (*)(id,SEL,SEL))objc_msgSend)(event,sel_registerName("respondsToSelector:"),sel_registerName("eventName"))) return;
    id name=m0(event,"eventName");
    const char *names[]={"topChange","topSelectionChange","topEmoteSubmitEditing","topEmoteFocus","topEmoteBlur","topEmoteContentSizeChange"};
    for (unsigned i=0;i<6;i++) if (equals(name,names[i])) {
        INC(native_events[i]);
        if (i==0) trace(TRACE_INPUT_CHANGE);else if (i==1) trace(TRACE_INPUT_SELECTION);else if (i==2) trace(TRACE_SUBMIT);
        return;
    }
}
/* Parse only GraphQL operationName, never variables, response bodies or query
 * text. Counts are fixed donor operation categories, not stored payloads. */
static void gql_object(id object) {
    if (!kind(object,"NSDictionary")) return;
    id name=m1(object,"objectForKey:",str("operationName"));
    const char *names[]={"SendChatMessage","SendSubsOnlyMessage","ChatEmoteSets","ChatEmoteUnlock","ChatChannelLockedEmotes","ChatHistory"};
    for (unsigned i=0;i<6;i++) if (equals(name,names[i])) {
        INC(gql_operations[i]);if (i<2) trace(TRACE_GQL_SEND);else if (i<5) trace(TRACE_GQL_CATALOG);return;
    }
}
static void gql_request(id request) {
    if (!kind(request,"NSURLRequest")) return;
    id url=m0(request,"URL");
    if (!kind(url,"NSURL") || !equals(m0(url,"host"),"gql.twitch.tv") || !equals(m0(url,"path"),"/gql")) return;
    id data=m0(request,"HTTPBody");
    if (!kind(data,"NSData")) { INC(gql_unreadable);return; }
    U n=((U (*)(id,SEL))objc_msgSend)(data,sel_registerName("length"));
    if (n>256*1024) { INC(gql_oversize);return; }
    id object=((id (*)(id,SEL,id,U,id *))objc_msgSend)((id)objc_getClass("NSJSONSerialization"),sel_registerName("JSONObjectWithData:options:error:"),data,0,NULL);
    if (kind(object,"NSDictionary")) gql_object(object);
    else if (kind(object,"NSArray")) { U size=count(object);if (size>32) size=32;for (U i=0;i<size;i++) gql_object(array_at(object,i)); }
    else INC(gql_unreadable);
}
static void fingerprint(id source,id data) {
    if (!kind(data,"NSData")) { INC(bundle_unreadable);return; }
    U length=((U (*)(id,SEL))objc_msgSend)(data,sel_registerName("length"));
    if (length>64*1024*1024) { INC(bundle_oversize);return; }
    /* Reserve an identity before hashing so concurrent getter hits hash once. */
    pthread_mutex_lock(&lock);
    for (unsigned i=0;i<4;i++) {
        id old=objc_loadWeakRetained(&bundle_data[i]);bool same=old && old==data;objc_release(old);
        if (same) { pthread_mutex_unlock(&lock);return; }
    }
    unsigned slot=next_bundle++%4;objc_storeWeak(&bundle_data[slot],data);
    const unsigned char *bytes=(const unsigned char *)m0(data,"bytes");
    uint64_t hash=14695981039346656037ULL;
    if (!bytes && length) { pthread_mutex_unlock(&lock);INC(bundle_unreadable);return; }
    for (U i=0;i<length;i++) hash=(hash^bytes[i])*1099511628211ULL;
    bundle_hash[slot]=hash;bundle_bytes[slot]=length;
    const unsigned char magic[]={0xc6,0x1f,0xbc,0x03,0xc1,0x03,0x19,0x1f};
    unsigned version=0;
    if (length>=12 && !memcmp(bytes,magic,8)) memcpy(&version,bytes+8,4);
    bundle_version[slot]=version;bundle_kind[slot]=url_kind(m0(source,"url"));
    pthread_mutex_unlock(&lock);
}
static void image_observed(id image,id view) {
    pthread_mutex_lock(&lock);copy_class(image_class,sizeof(image_class),image);pthread_mutex_unlock(&lock);
    if (kind(image,"TwitchAnimatedImage")) INC(animated_results);
    if (kind(view,"UIView")) {
        Rect bounds=((Rect (*)(id,SEL))objc_msgSend)(view,sel_registerName("bounds"));
        if (bounds.size.width>0 && bounds.size.height>0) {
            if (bounds.size.width>bounds.size.height*1.2) INC(image_wide);
            else if (bounds.size.width>=bounds.size.height*.95 && bounds.size.width<=bounds.size.height*1.05) INC(image_square);
        }
    }
}

static void connect_hook(id self,SEL sel,id url,id protocols,const void *options,double socket_id) {
    HIT(CONNECT);
    if (irc_url(kind(url,"NSURL") ? url : m1((id)objc_getClass("NSURL"),"URLWithString:",url))) INC(irc_connects);
    ((void (*)(id,SEL,id,id,const void *,double))hooks[CONNECT].original)(self,sel,url,protocols,options,socket_id);
}
static void socket_open_hook(id self,SEL sel) {
    HIT(SOCKET_OPEN);if (irc_url(m0(self,"url"))) INC(irc_opens);
    ((void (*)(id,SEL))hooks[SOCKET_OPEN].original)(self,sel);
}
static void delegate_hook(id self,SEL sel,id delegate) {
    HIT(DELEGATE);
    if (irc_url(m0(self,"url"))) {
        pthread_mutex_lock(&lock);copy_class(delegate_class,sizeof(delegate_class),delegate);pthread_mutex_unlock(&lock);
        if (kind(delegate,"RCTWebSocketModule")) INC(rn_delegates);
    }
    ((void (*)(id,SEL,id))hooks[DELEGATE].original)(self,sel,delegate);
}
static void receive_hook(id self,SEL sel,id socket,id message) {
    HIT(RECEIVE);bool irc=kind(socket,"SRWebSocket") && irc_url(m0(socket,"url"));
    if (irc) { INC(irc_deliveries);classify(message,false,false);delivery_depth++; }
    ((void (*)(id,SEL,id,id))hooks[RECEIVE].original)(self,sel,socket,message);
    if (irc) delivery_depth--;
}
static void event_hook(id self,SEL sel,id name,id body) {
    HIT(EVENT);
    /* RCTEventEmitter also carries non-chat events; count only socket messages. */
    if (kind(self,"RCTWebSocketModule") && equals(name,"websocketMessage")) {
        INC(js_deliveries);
        if (delivery_depth) { INC(js_in_receive);if (kind(body,"NSDictionary")) classify(m1(body,"objectForKey:",str("data")),true,false); }
    }
    ((void (*)(id,SEL,id,id))hooks[EVENT].original)(self,sel,name,body);
}
static BOOL send_hook(id self,SEL sel,id text,id *error) {
    HIT(SEND);if (irc_url(m0(self,"url"))) { if (classify(text,false,true)) trace(TRACE_IRC_SEND); }
    return ((BOOL (*)(id,SEL,id,id *))hooks[SEND].original)(self,sel,text,error);
}
static id surface_hook(id self,SEL sel,id bridge,id name,id props) {
    HIT(SURFACE);surface_name(name);
    return ((id (*)(id,SEL,id,id,id))hooks[SURFACE].original)(self,sel,bridge,name,props);
}
static id root_hook(id self,SEL sel,id bridge,id name,id props) {
    HIT(ROOT);surface_name(name);
    return ((id (*)(id,SEL,id,id,id))hooks[ROOT].original)(self,sel,bridge,name,props);
}
static id fabric_hook(id self,SEL sel,id name,id props) {
    HIT(FABRIC);surface_name(name);
    return ((id (*)(id,SEL,id,id))hooks[FABRIC].original)(self,sel,name,props);
}
static id source_hook(id self,SEL sel) {
    HIT(SOURCE);id data=((id (*)(id,SEL))hooks[SOURCE].original)(self,sel);fingerprint(self,data);return data;
}
static void bundle_hook(id self,SEL sel,id url,id progress,id completion) {
    HIT(BUNDLE);INC(bundle_locations[url_kind(url)]);
    ((void (*)(id,SEL,id,id,id))hooks[BUNDLE].original)(self,sel,url,progress,completion);
}
static void host_bundle_hook(id self,SEL sel,id url,id progress,id completion) {
    HIT(HOST_BUNDLE);INC(bundle_locations[url_kind(url)]);
    ((void (*)(id,SEL,id,id,id))hooks[HOST_BUNDLE].original)(self,sel,url,progress,completion);
}
#define VOID_ONE(fn,slot,observe) static void fn(id self,SEL sel,id value) { HIT(slot);observe;((void (*)(id,SEL,id))hooks[slot].original)(self,sel,value); }
VOID_ONE(emote_map_hook,EMOTE_MAP,map_shape(value,0);if (kind(value,"NSDictionary")) { U n=count(value);ADD(map_entries,n);if (n) INC(maps_nonempty); })
VOID_ONE(token_map_hook,TOKEN_MAP,map_shape(value,1);if (kind(value,"NSDictionary")) { U n=count(value);ADD(token_entries,n);if (n) INC(token_maps_nonempty); })
VOID_ONE(template_hook,TEMPLATE,(void)value)
VOID_ONE(value_hook,VALUE,value_shape(value))
VOID_ONE(change_hook,CHANGE,(void)value)
static BOOL edit_hook(id self,SEL sel,id view,Range range,id replacement) {
    HIT(EDIT);if (equals(replacement,"\n")) INC(newline_edits);
    return ((BOOL (*)(id,SEL,id,Range,id))hooks[EDIT].original)(self,sel,view,range,replacement);
}
static void input_layout_hook(id self,SEL sel) { HIT(INPUT_LAYOUT);((void (*)(id,SEL))hooks[INPUT_LAYOUT].original)(self,sel); }
static Rect bounds_hook(id self,SEL sel,id container,Rect line,Point glyph,I index) {
    HIT(ATTACH_BOUNDS);
    Rect result=((Rect (*)(id,SEL,id,Rect,Point,I))hooks[ATTACH_BOUNDS].original)(self,sel,container,line,glyph,index);
    if (result.size.width>0 && result.size.height>0) {
        if (result.size.width>result.size.height*1.2) INC(input_wide);
        else if (result.size.width>=result.size.height*.95 && result.size.width<=result.size.height*1.05) INC(input_square);
    }
    return result;
}
static id image_request_hook(id self,SEL sel,id request,id progress,id completion) {
    HIT(IMAGE_REQUEST);if (kind(request,"NSURLRequest") && emote_url(m0(request,"URL"))) INC(image_emote_requests);
    return ((id (*)(id,SEL,id,id,id))hooks[IMAGE_REQUEST].original)(self,sel,request,progress,completion);
}
static id http_request_hook(id self,SEL sel,id request,id delegate) {
    HIT(HTTP_REQUEST);gql_request(request);if (kind(request,"NSURLRequest") && emote_url(m0(request,"URL"))) INC(http_emote_requests);
    id task=((id (*)(id,SEL,id,id))hooks[HTTP_REQUEST].original)(self,sel,request,delegate);
    pthread_mutex_lock(&lock);copy_class(task_class,sizeof(task_class),task);pthread_mutex_unlock(&lock);
    return task;
}
static void http_done_hook(id self,SEL sel,id session,id task,id error) {
    HIT(HTTP_DONE);if (error) INC(http_errors);
    pthread_mutex_lock(&lock);copy_class(session_class,sizeof(session_class),session);copy_class(task_class,sizeof(task_class),task);pthread_mutex_unlock(&lock);
    ((void (*)(id,SEL,id,id,id))hooks[HTTP_DONE].original)(self,sel,session,task,error);
}
static void image_receive_hook(id self,SEL sel,id image,id metadata,const void *observer) {
    HIT(IMAGE_RECEIVE);image_observed(image,self);
    ((void (*)(id,SEL,id,id,const void *))hooks[IMAGE_RECEIVE].original)(self,sel,image,metadata,observer);
}
VOID_ONE(image_set_hook,IMAGE_SET,image_observed(value,self))
VOID_ONE(animation_set_hook,ANIMATION_SET,image_observed(value,self))
static void animation_start_hook(id self,SEL sel) { HIT(ANIMATION_START);((void (*)(id,SEL))hooks[ANIMATION_START].original)(self,sel); }
static id decode_hook(id self,SEL sel,id data,Size size,double scale,I mode,id completion) {
    HIT(DECODE);
    return ((id (*)(id,SEL,id,Size,double,I,id))hooks[DECODE].original)(self,sel,data,size,scale,mode,completion);
}

static id host_surface_mode_hook(id self,SEL sel,id name,int mode,id props) {
    HIT(HOST_SURFACE_MODE);surface_name(name);
    return ((id (*)(id,SEL,id,int,id))hooks[HOST_SURFACE_MODE].original)(self,sel,name,mode,props);
}
static id host_surface_hook(id self,SEL sel,id name,id props) {
    HIT(HOST_SURFACE);surface_name(name);
    return ((id (*)(id,SEL,id,id))hooks[HOST_SURFACE].original)(self,sel,name,props);
}
static id fabric_init_hook(id self,SEL sel,id presenter,id name,id props) {
    HIT(FABRIC_INIT);surface_name(name);
    return ((id (*)(id,SEL,id,id,id))hooks[FABRIC_INIT].original)(self,sel,presenter,name,props);
}
static void fabric_start_hook(id self,SEL sel) {
    HIT(FABRIC_START);surface_name(m0(self,"moduleName"));
    ((void (*)(id,SEL))hooks[FABRIC_START].original)(self,sel);
}
static void hosting_window_hook(id self,SEL sel) {
    HIT(HOSTING_WINDOW);id surface=m0(self,"surface");if (kind(surface,"RCTFabricSurface")) surface_name(m0(surface,"moduleName"));
    ((void (*)(id,SEL))hooks[HOSTING_WINDOW].original)(self,sel);
}
#define JS_CALL(fn,slot) static void fn(id self,SEL sel,id module,id method,id args) { HIT(slot);js_handoff(module,method,args);((void (*)(id,SEL,id,id,id))hooks[slot].original)(self,sel,module,method,args); }
JS_CALL(host_js_hook,HOST_JS)
JS_CALL(instance_js_hook,INSTANCE_JS)
static void callable_js_hook(id self,SEL sel,id module,id method,id args,id completion) {
    HIT(CALLABLE_JS);js_handoff(module,method,args);
    ((void (*)(id,SEL,id,id,id,id))hooks[CALLABLE_JS].original)(self,sel,module,method,args,completion);
}
VOID_ONE(dispatch_event_hook,DISPATCH_EVENT,observe_native_event(value))
VOID_ONE(input_selection_hook,INPUT_SELECTION,(void)value)
VOID_ONE(input_begin_hook,INPUT_BEGIN,(void)value)
VOID_ONE(input_end_hook,INPUT_END,(void)value)
VOID_ONE(submit_set_hook,SUBMIT_SET,(void)value)
static void socket_send_hook(id self,SEL sel,id value) {
    HIT(SOCKET_SEND);if (irc_url(m0(self,"url"))) {
        U n=classify(value,false,true);if (n) { ADD(legacy_send_privmsg,n);trace(TRACE_IRC_SEND); }
    }
    ((void (*)(id,SEL,id))hooks[SOCKET_SEND].original)(self,sel,value);
}
static BOOL socket_send_data_hook(id self,SEL sel,id data,id *error) {
    HIT(SOCKET_SEND_DATA);
    /* Data is decoded transiently only for IRC sockets, bounded as in receive. */
    if (irc_url(m0(self,"url")) && kind(data,"NSData") && ((U (*)(id,SEL))objc_msgSend)(data,sel_registerName("length"))<=65536) {
        id text=((id (*)(id,SEL,id,U))objc_msgSend)(m0((id)objc_getClass("NSString"),"alloc"),sel_registerName("initWithData:encoding:"),data,4);
        U n=classify(text,false,true);if (n) { ADD(data_send_privmsg,n);trace(TRACE_IRC_SEND); }objc_release(text);
    }
    return ((BOOL (*)(id,SEL,id,id *))hooks[SOCKET_SEND_DATA].original)(self,sel,data,error);
}
static id network_build_hook(id self,SEL sel,id query,id devtools,id completion) {
    HIT(NETWORK_BUILD);
    /* Count request construction only; concrete HTTP requests are categorized
     * separately. The query object and completion block are forwarded untouched. */
    return ((id (*)(id,SEL,id,id,id))hooks[NETWORK_BUILD].original)(self,sel,query,devtools,completion);
}

/* Exact donor encodings, including structs, C++ pointers, blocks and floats.
 * An incompatible/missing method is reported; it is never approximated. */
#define SPEC(slot,cls,sel,type,fn,is_meta) [slot]={cls,sel,type,is_meta,(IMP)fn,NULL,0,{0},{0},0,false}
static Hook hooks[HOOK_COUNT]={
    SPEC(CONNECT,"RCTWebSocketModule","connect:protocols:options:socketID:","v48@0:8@16@24^{SpecConnectOptions=@}32d40",connect_hook,false),
    SPEC(SOCKET_OPEN,"SRWebSocket","open","v16@0:8",socket_open_hook,false),
    SPEC(DELEGATE,"SRWebSocket","setDelegate:","v24@0:8@16",delegate_hook,false),
    SPEC(RECEIVE,"RCTWebSocketModule","webSocket:didReceiveMessage:","v32@0:8@16@24",receive_hook,false),
    SPEC(EVENT,"RCTEventEmitter","sendEventWithName:body:","v32@0:8@16@24",event_hook,false),
    SPEC(SEND,"SRWebSocket","sendString:error:","B32@0:8@16^@24",send_hook,false),
    SPEC(SURFACE,"RCTSurface","initWithBridge:moduleName:initialProperties:","@40@0:8@16@24@32",surface_hook,false),
    SPEC(ROOT,"RCTRootView","initWithBridge:moduleName:initialProperties:","@40@0:8@16@24@32",root_hook,false),
    SPEC(FABRIC,"RCTSurfacePresenter","createFabricSurfaceForModuleName:initialProperties:","@32@0:8@16@24",fabric_hook,false),
    SPEC(SOURCE,"RCTSource","data","@16@0:8",source_hook,false),
    SPEC(BUNDLE,"RCTJavaScriptLoader","loadBundleAtURL:onProgress:onComplete:","v40@0:8@16@?24@?32",bundle_hook,true),
    SPEC(HOST_BUNDLE,"RCTHost","loadBundleAtURL:onProgress:onComplete:","v40@0:8@16@?24@?32",host_bundle_hook,false),
    SPEC(EMOTE_MAP,INPUT,"setEmoteMap:","v24@0:8@16",emote_map_hook,false),
    SPEC(TOKEN_MAP,INPUT,"setTokenImageMap:","v24@0:8@16",token_map_hook,false),
    SPEC(TEMPLATE,INPUT,"setEmoteUrlTemplate:","v24@0:8@16",template_hook,false),
    SPEC(VALUE,INPUT,"setValue:","v24@0:8@16",value_hook,false),
    SPEC(CHANGE,INPUT,"textViewDidChange:","v24@0:8@16",change_hook,false),
    SPEC(EDIT,INPUT,"textView:shouldChangeTextInRange:replacementText:","B48@0:8@16{_NSRange=QQ}24@40",edit_hook,false),
    SPEC(INPUT_LAYOUT,INPUT,"layoutSubviews","v16@0:8",input_layout_hook,false),
    SPEC(ATTACH_BOUNDS,ATTACHMENT,"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:","{CGRect={CGPoint=dd}{CGSize=dd}}80@0:8@16{CGRect={CGPoint=dd}{CGSize=dd}}24{CGPoint=dd}56q72",bounds_hook,false),
    SPEC(IMAGE_REQUEST,"RCTImageLoader","_loadURLRequest:progressBlock:completionBlock:","@?40@0:8@16@?24@?32",image_request_hook,false),
    SPEC(HTTP_REQUEST,"RCTHTTPRequestHandler","sendRequest:withDelegate:","@32@0:8@16@24",http_request_hook,false),
    SPEC(HTTP_DONE,"RCTHTTPRequestHandler","URLSession:task:didCompleteWithError:","v40@0:8@16@24@32",http_done_hook,false),
    SPEC(IMAGE_RECEIVE,"RCTImageComponentView","didReceiveImage:metadata:fromObserver:","v40@0:8@16@24r^v32",image_receive_hook,false),
    SPEC(IMAGE_SET,"RCTUIImageViewAnimated","setImage:","v24@0:8@16",image_set_hook,false),
    SPEC(ANIMATION_SET,"RCTUIImageViewAnimated","setAnimatedImage:","v24@0:8@16",animation_set_hook,false),
    SPEC(ANIMATION_START,"RCTUIImageViewAnimated","start","v16@0:8",animation_start_hook,false),
    SPEC(DECODE,"TwitchAnimatedImageDecoder","decodeImageData:size:scale:resizeMode:completionHandler:","@?64@0:8@16{CGSize=dd}24d40q48@?56",decode_hook,false),
    SPEC(HOST_SURFACE_MODE,"RCTHost","createSurfaceWithModuleName:mode:initialProperties:","@36@0:8@16i24@28",host_surface_mode_hook,false),
    SPEC(HOST_SURFACE,"RCTHost","createSurfaceWithModuleName:initialProperties:","@32@0:8@16@24",host_surface_hook,false),
    SPEC(FABRIC_INIT,"RCTFabricSurface","initWithSurfacePresenter:moduleName:initialProperties:","@40@0:8@16@24@32",fabric_init_hook,false),
    SPEC(FABRIC_START,"RCTFabricSurface","start","v16@0:8",fabric_start_hook,false),
    SPEC(HOSTING_WINDOW,"RCTSurfaceHostingView","didMoveToWindow","v16@0:8",hosting_window_hook,false),
    SPEC(HOST_JS,"RCTHost","callFunctionOnJSModule:method:args:","v40@0:8@16@24@32",host_js_hook,false),
    SPEC(INSTANCE_JS,"RCTInstance","callFunctionOnJSModule:method:args:","v40@0:8@16@24@32",instance_js_hook,false),
    SPEC(CALLABLE_JS,"RCTCallableJSModules","invokeModule:method:withArgs:onComplete:","v48@0:8@16@24@32@?40",callable_js_hook,false),
    SPEC(DISPATCH_EVENT,"RCTEventDispatcher","sendEvent:","v24@0:8@16",dispatch_event_hook,false),
    SPEC(INPUT_SELECTION,INPUT,"textViewDidChangeSelection:","v24@0:8@16",input_selection_hook,false),
    SPEC(INPUT_BEGIN,INPUT,"textViewDidBeginEditing:","v24@0:8@16",input_begin_hook,false),
    SPEC(INPUT_END,INPUT,"textViewDidEndEditing:","v24@0:8@16",input_end_hook,false),
    SPEC(SUBMIT_SET,INPUT,"setOnEmoteSubmitEditing:","v24@0:8@?16",submit_set_hook,false),
    SPEC(SOCKET_SEND,"SRWebSocket","send:","v24@0:8@16",socket_send_hook,false),
    SPEC(SOCKET_SEND_DATA,"SRWebSocket","sendData:error:","B32@0:8@16^@24",socket_send_data_hook,false),
    SPEC(NETWORK_BUILD,"RCTNetworking","buildRequest:devToolsRequestId:completionBlock:","@?40@0:8@16@24@?32",network_build_hook,false),
};
void tas_rn_probe_retry_hooks(void) {
    pthread_mutex_lock(&install_lock);
    for (unsigned i=0;i<HOOK_COUNT;i++) {
        Hook *h=&hooks[i];if (h->original) continue;
        Class c=objc_getClass(h->class_name);if (!c) continue;
        if (h->meta) c=object_getClass((id)c);
        SEL sel=sel_registerName(h->selector);Method method=class_getInstanceMethod(c,sel);
        if (!method) continue;
        const char *encoding=method_getTypeEncoding(method);
        if (!encoding || strcmp(encoding,h->encoding)) { h->rejected=true;continue; }
        h->original=method_getImplementation(method);
        /* Localize inherited methods so the saved superclass implementation
         * and unrelated receiver classes are left intact. */
        if (!class_addMethod(c,sel,h->replacement,encoding)) method_setImplementation(method,h->replacement);
    }
    pthread_mutex_unlock(&install_lock);
}
static void append(char *buffer,size_t capacity,size_t *used,const char *fmt,...) {
    if (*used>=capacity) return;
    va_list args;va_start(args,fmt);int n=vsnprintf(buffer+*used,capacity-*used,fmt,args);va_end(args);
    if (n>0) *used+=(size_t)n<capacity-*used ? (size_t)n : capacity-*used-1;
}
void tas_rn_probe_status(char *buffer,size_t capacity) {
    if (!buffer || !capacity) return;
    tas_rn_probe_retry_hooks();size_t used=0;buffer[0]=0;
    pthread_mutex_lock(&install_lock);pthread_mutex_lock(&lock);
    append(buffer,capacity,&used,"\nRN boundary probe (passive; this launch)\n"
        "No RN emote implementation changes; legacy counters above remain separate.\n"
        "IRC connect/open/RN delegate/delivery: %llu/%llu/%llu/%llu\n"
        "IRC received text/other/oversize: %llu/%llu/%llu\n"
        "IRC PRIVMSG/ROOMSTATE/native-emote-tag: %llu/%llu/%llu\n"
        "JS socket events/events inside IRC receive/PRIVMSG/native-emote-tag: %llu/%llu/%llu/%llu\n"
        "IRC outbound PRIVMSG: %llu (not evidence of local echo rendering)\n"
        "IRC delegate class: %s\n"
        "Input nonempty emote/token maps, cumulative entries: %llu/%llu, %llu/%llu\n"
        "Input newline edits/attachment square/wide: %llu/%llu/%llu\n"
        "Image loader/HTTP Twitch emote URL requests: %llu/%llu\n"
        "RN image view square/wide/animated-object observations: %llu/%llu/%llu (all RN images, not emote-specific)\n"
        "HTTP completions with error: %llu; session/task: %s/%s\n"
        "Last image result class: %s\n"
        "Bundle load location unknown/embedded/other-local/remote: %llu/%llu/%llu/%llu\n"
        "Bundle hash oversize/unreadable: %llu/%llu; FNV64 is an identity fingerprint, not a security digest.\n"
        "Observed surface module names (%u; overflow=%llu):",
        (unsigned long long)GET(irc_connects),(unsigned long long)GET(irc_opens),(unsigned long long)GET(rn_delegates),(unsigned long long)GET(irc_deliveries),
        (unsigned long long)GET(received_text),(unsigned long long)GET(received_other),(unsigned long long)GET(oversized_text),
        (unsigned long long)GET(incoming_privmsg),(unsigned long long)GET(incoming_roomstate),(unsigned long long)GET(incoming_emote_tag),
        (unsigned long long)GET(js_deliveries),(unsigned long long)GET(js_in_receive),(unsigned long long)GET(js_privmsg),(unsigned long long)GET(js_emote_tag),
        (unsigned long long)GET(outbound_privmsg),delegate_class[0] ? delegate_class : "unobserved",
        (unsigned long long)GET(maps_nonempty),(unsigned long long)GET(token_maps_nonempty),(unsigned long long)GET(map_entries),(unsigned long long)GET(token_entries),
        (unsigned long long)GET(newline_edits),(unsigned long long)GET(input_square),(unsigned long long)GET(input_wide),
        (unsigned long long)GET(image_emote_requests),(unsigned long long)GET(http_emote_requests),
        (unsigned long long)GET(image_square),(unsigned long long)GET(image_wide),(unsigned long long)GET(animated_results),
        (unsigned long long)GET(http_errors),session_class[0] ? session_class : "unobserved",task_class[0] ? task_class : "unobserved",image_class[0] ? image_class : "unobserved",
        (unsigned long long)GET(bundle_locations[0]),(unsigned long long)GET(bundle_locations[1]),(unsigned long long)GET(bundle_locations[2]),(unsigned long long)GET(bundle_locations[3]),
        (unsigned long long)GET(bundle_oversize),(unsigned long long)GET(bundle_unreadable),surface_count,(unsigned long long)GET(surface_overflow));
    for (unsigned i=0;i<surface_count;i++) append(buffer,capacity,&used," %s",surfaces[i]);
    append(buffer,capacity,&used,"\nConsumed RCTSource bundles (up to 4; getter may be bypassed):\n");
    for (unsigned i=0;i<4;i++) if (bundle_hash[i]) append(buffer,capacity,&used,"  kind=%u bytes=%llu fnv64=%016llx Hermes=%u\n",bundle_kind[i],(unsigned long long)bundle_bytes[i],(unsigned long long)bundle_hash[i],bundle_version[i]);
    append(buffer,capacity,&used,"Build 52 native handoffs (calls may traverse multiple observed boundaries):\n"
        "  JS scheduling device/app/other/socket-event: %llu/%llu/%llu/%llu\n"
        "  Input value sets empty/nonempty/other: %llu/%llu/%llu\n"
        "  Native input events change/selection/submit/focus/blur/size: %llu/%llu/%llu/%llu/%llu/%llu (not chat-exclusive)\n"
        "  IRC PRIVMSG via legacy send/data send: %llu/%llu (nested send methods may double-count)\n"
        "  HTTP GQL SendChatMessage/SendSubsOnlyMessage/ChatEmoteSets/ChatEmoteUnlock/ChatChannelLockedEmotes/ChatHistory: %llu/%llu/%llu/%llu/%llu/%llu\n"
        "  GQL body oversize/unreadable: %llu/%llu (no variables/query/response retained)\n",
        (unsigned long long)GET(js_module_device),(unsigned long long)GET(js_module_app),(unsigned long long)GET(js_module_other),(unsigned long long)GET(js_socket_handoff),
        (unsigned long long)GET(input_values_empty),(unsigned long long)GET(input_values_nonempty),(unsigned long long)GET(input_values_other),
        (unsigned long long)GET(native_events[0]),(unsigned long long)GET(native_events[1]),(unsigned long long)GET(native_events[2]),(unsigned long long)GET(native_events[3]),(unsigned long long)GET(native_events[4]),(unsigned long long)GET(native_events[5]),
        (unsigned long long)GET(legacy_send_privmsg),(unsigned long long)GET(data_send_privmsg),
        (unsigned long long)GET(gql_operations[0]),(unsigned long long)GET(gql_operations[1]),(unsigned long long)GET(gql_operations[2]),(unsigned long long)GET(gql_operations[3]),(unsigned long long)GET(gql_operations[4]),(unsigned long long)GET(gql_operations[5]),
        (unsigned long long)GET(gql_oversize),(unsigned long long)GET(gql_unreadable));
    for (unsigned i=0;i<2;i++) append(buffer,capacity,&used,"  %s map shapes nil/dict/array/string/other: %llu/%llu/%llu/%llu/%llu; sampled values string/number/dict/other: %llu/%llu/%llu/%llu (up to 32 per setter)\n",i ? "Token" : "Emote",
        (unsigned long long)GET(map_shapes[i][0]),(unsigned long long)GET(map_shapes[i][1]),(unsigned long long)GET(map_shapes[i][2]),(unsigned long long)GET(map_shapes[i][3]),(unsigned long long)GET(map_shapes[i][4]),
        (unsigned long long)GET(map_samples[i][0]),(unsigned long long)GET(map_samples[i][1]),(unsigned long long)GET(map_samples[i][2]),(unsigned long long)GET(map_samples[i][3]));
    append(buffer,capacity,&used,"  Recent native category order (up to 48; no text/IDs/timestamps):");
    for (unsigned i=0;i<trace_count;i++) {
        unsigned j=(trace_next+48-trace_count+i)%48;
        append(buffer,capacity,&used," %llu:%s",(unsigned long long)trace_rows[j].sequence,trace_names[trace_rows[j].kind]);
    }
    append(buffer,capacity,&used,"\n");
    append(buffer,capacity,&used,"Hook calls / installation / first receiver / first native caller image+offset:\n");
    for (unsigned i=0;i<HOOK_COUNT;i++) {
        Hook *h=&hooks[i];append(buffer,capacity,&used,"  %s.%s: %llu %s receiver=%s caller=%s+0x%llx\n",h->class_name,h->selector,
            (unsigned long long)GET(h->calls),h->original ? "installed" : h->rejected ? "ABI-rejected" : "missing",
            h->receiver[0] ? h->receiver : "unobserved",h->caller[0] ? h->caller : "unobserved",(unsigned long long)h->caller_offset);
    }
    append(buffer,capacity,&used,"No JS parser/token/local-echo callback is instrumented. Native JS scheduling and send observations do not prove JS execution or local echo rendering.\n\n");
    pthread_mutex_unlock(&lock);pthread_mutex_unlock(&install_lock);
}
#else
void tas_rn_probe_retry_hooks(void) {}
void tas_rn_probe_status(char *buffer,size_t capacity) { if (buffer && capacity) buffer[0]=0; }
#endif
