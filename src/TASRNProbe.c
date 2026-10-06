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
       HOOK_COUNT };
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
static void classify(id data,bool js,bool outbound) {
    if (!kind(data,"NSString")) { if (!js && !outbound) INC(received_other);return; }
    if (!js && !outbound) INC(received_text);
    U chars=((U (*)(id,SEL))objc_msgSend)(data,sel_registerName("length"));
    if (chars>65536) { INC(oversized_text);return; }
    const char *s=utf8(data);if (!s) return;
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
        if (outbound) { if (priv) INC(outbound_privmsg); }
        else if (js) { if (priv) INC(js_privmsg);if (priv && emotes) INC(js_emote_tag); }
        else { if (priv) INC(incoming_privmsg);if (room) INC(incoming_roomstate);if (priv && emotes) INC(incoming_emote_tag); }
        if (!*end) break;
        s=end+1;
    }
}
static void surface_name(id value) {
    const char *s=utf8(value);if (!s) return;
    size_t n=strnlen(s,96);if (!n || n>=96) return;
    for (size_t i=0;i<n;i++) if (!((s[i]>='a' && s[i]<='z') || (s[i]>='A' && s[i]<='Z') ||
        (s[i]>='0' && s[i]<='9') || s[i]=='_' || s[i]=='-' || s[i]=='.')) return;
    pthread_mutex_lock(&lock);
    for (unsigned i=0;i<surface_count;i++) if (!strcmp(surfaces[i],s)) { pthread_mutex_unlock(&lock);return; }
    if (surface_count<8) snprintf(surfaces[surface_count++],96,"%s",s);else INC(surface_overflow);
    pthread_mutex_unlock(&lock);
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
    HIT(SEND);if (irc_url(m0(self,"url"))) classify(text,false,true);
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
VOID_ONE(emote_map_hook,EMOTE_MAP,if (kind(value,"NSDictionary")) { U n=count(value);ADD(map_entries,n);if (n) INC(maps_nonempty); })
VOID_ONE(token_map_hook,TOKEN_MAP,if (kind(value,"NSDictionary")) { U n=count(value);ADD(token_entries,n);if (n) INC(token_maps_nonempty); })
VOID_ONE(template_hook,TEMPLATE,(void)value)
VOID_ONE(value_hook,VALUE,(void)value)
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
    HIT(HTTP_REQUEST);if (kind(request,"NSURLRequest") && emote_url(m0(request,"URL"))) INC(http_emote_requests);
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
    append(buffer,capacity,&used,"Hook calls / installation / first receiver / first native caller image+offset:\n");
    for (unsigned i=0;i<HOOK_COUNT;i++) {
        Hook *h=&hooks[i];append(buffer,capacity,&used,"  %s.%s: %llu %s receiver=%s caller=%s+0x%llx\n",h->class_name,h->selector,
            (unsigned long long)GET(h->calls),h->original ? "installed" : h->rejected ? "ABI-rejected" : "missing",
            h->receiver[0] ? h->receiver : "unobserved",h->caller[0] ? h->caller : "unobserved",(unsigned long long)h->caller_offset);
    }
    append(buffer,capacity,&used,"No JS parser/token/local-echo callback is instrumented. Surface names and bundle bytes identify owners; static JS call paths still require runtime confirmation.\n\n");
    pthread_mutex_unlock(&lock);pthread_mutex_unlock(&install_lock);
}
#else
void tas_rn_probe_retry_hooks(void) {}
void tas_rn_probe_status(char *buffer,size_t capacity) { if (buffer && capacity) buffer[0]=0; }
#endif
