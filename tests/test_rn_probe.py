"""Passive boundary forwarding, IRC header classification and ABI refusal."""
import os
import shutil
import unittest
import test_composer

HARNESS = r'''
#define _GNU_SOURCE
#define TAS_RN_CHAT_DIAGNOSTIC 1
/* The host runtime supplies this standard ObjC runtime declaration. */
#include <objc/runtime.h>
const char *class_getName(Class);
#include "TASRNProbe.c"
#include <assert.h>
struct Fake { const char *cls,*text; id inner; U chars; };
static struct Fake classes[]={ {"NSString",0,0,0},{"NSURL",0,0,0},
    {"SRWebSocket",0,0,0},{"RCTWebSocketModule",0,0,0},{"NSDictionary",0,0,0} };
static struct Fake host={"NSString","irc-ws.chat.twitch.tv",0,0};
static struct Fake url={"NSURL",0,&host,0},socket={"SRWebSocket",0,&url,0};
static struct Fake receiver={"RCTWebSocketModule",0,0,0},event={"NSString","websocketMessage",0,0};
static struct Fake message={"NSString","@emotes=25:0-4;room-id=private :private!private PRIVMSG #private :Kappa private body\r\n",0,0};
static struct Fake body={"NSDictionary",0,&message,0},string={"NSString",0,0,0};
Class objc_getClass(const char *s) {
    for(U i=0;i<sizeof(classes)/sizeof(*classes);i++) if(!strcmp(s,classes[i].cls)) return &classes[i];
    return nil;
}
Class object_getClass(id o) { return o; }
const char *class_getName(Class c) { return c->cls; }
SEL sel_registerName(const char *s) { return s; }
static id dispatch(id o,SEL sel,...) {
    if(!o) return nil;
    va_list ap;va_start(ap,sel);id result=nil;
    if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(ap,Class);result=(id)(uintptr_t)(c && !strcmp(o->cls,c->cls)); }
    else if(!strcmp(sel,"stringWithUTF8String:")) { string.text=va_arg(ap,const char *);result=&string; }
    else if(!strcmp(sel,"isEqualToString:")) { id value=va_arg(ap,id);result=(id)(uintptr_t)!strcmp(o->text,value->text); }
    else if(!strcmp(sel,"host") || !strcmp(sel,"url") || !strcmp(sel,"objectForKey:")) result=o->inner;
    else if(!strcmp(sel,"length")) result=(id)(uintptr_t)(o->chars ? o->chars : strlen(o->text));
    else if(!strcmp(sel,"UTF8String")) result=(id)o->text;
    else assert(!"unexpected dispatch");
    va_end(ap);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_storeWeak(id *slot,id o) { *slot=o;return o; }
id objc_loadWeakRetained(id *slot) { return *slot; }
static unsigned delivered,emitted,sent,connected,bounded,replaced;
static void native_event(id self,SEL sel,id name,id payload) {
    assert(self==&receiver && !strcmp(sel,"sendEventWithName:body:") && name==&event && payload==&body);emitted++;
}
static void native_receive(id self,SEL sel,id sock,id text) {
    assert(self==&receiver && !strcmp(sel,"webSocket:didReceiveMessage:") && sock==&socket && text==&message);delivered++;
    event_hook(self,"sendEventWithName:body:",&event,&body);
}
static BOOL native_send(id self,SEL sel,id text,id *error) {
    assert(self==&socket && !strcmp(sel,"sendString:error:") && text==&message && error && *error==&host);sent++;*error=&url;return NO;
}
static void native_connect(id self,SEL sel,id u,id protocols,const void *options,double socket_id) {
    assert(self==&receiver && !strcmp(sel,"connect:protocols:options:socketID:") && u==&url && protocols==&body && options==&host && socket_id==47.5);connected++;
}
static Rect native_bounds(id self,SEL sel,id container,Rect line,Point glyph,I index) {
    assert(self==&receiver && !strcmp(sel,"bounds") && container==&body && line.size.width==321 && glyph.y==42 && index==9);bounded++;
    return (Rect){{1,2},{72,24}};
}
static const char *encoding="wrong";
Method class_getInstanceMethod(Class c,SEL s) { assert(c && s);return (Method)&encoding; }
const char *method_getTypeEncoding(Method m) { (void)m;return encoding; }
IMP method_getImplementation(Method m) { (void)m;return (IMP)native_connect; }
BOOL class_addMethod(Class c,SEL s,IMP i,const char *e) { (void)c;(void)s;(void)i;(void)e;return NO; }
IMP method_setImplementation(Method m,IMP i) { (void)m;assert(i==(IMP)connect_hook);replaced++;return (IMP)native_connect; }
int main(void) {
    hooks[RECEIVE].original=(IMP)native_receive;hooks[EVENT].original=(IMP)native_event;
    receive_hook(&receiver,"webSocket:didReceiveMessage:",&socket,&message);
    assert(delivered==1 && emitted==1 && irc_deliveries==1 && incoming_privmsg==1 && incoming_emote_tag==1);
    assert(js_deliveries==1 && js_in_receive==1 && js_privmsg==1 && js_emote_tag==1 && !delivery_depth);
    struct Fake text={"NSString",":x PRIVMSG #x :body contains ROOMSTATE and emotes=25:0-4\n@emotes=;other=1 :x PRIVMSG #x :text\n:x ROOMSTATE #x\r\n",0,0};
    classify(&text,false,false);
    assert(incoming_privmsg==3 && incoming_roomstate==1 && incoming_emote_tag==1);
    text.chars=65537;classify(&text,false,false);assert(oversized_text==1 && incoming_privmsg==3);
    hooks[SEND].original=(IMP)native_send;id error=&host;
    assert(!send_hook(&socket,"sendString:error:",&message,&error) && error==&url && sent==1 && outbound_privmsg==1);
    hooks[CONNECT].original=(IMP)native_connect;
    connect_hook(&receiver,"connect:protocols:options:socketID:",&url,&body,&host,47.5);
    assert(connected==1 && irc_connects==1);
    hooks[ATTACH_BOUNDS].original=(IMP)native_bounds;
    Rect r=bounds_hook(&receiver,"bounds",&body,(Rect){{0,0},{321,12}},(Point){0,42},9);
    assert(bounded==1 && r.origin.x==1 && r.origin.y==2 && r.size.width==72 && r.size.height==24 && input_wide==1 && !input_square);
    /* ABI mismatch must leave the native method intact. */
    for(unsigned i=0;i<HOOK_COUNT;i++) hooks[i].original=(IMP)native_connect;
    hooks[CONNECT].original=NULL;tas_rn_probe_retry_hooks();assert(!hooks[CONNECT].original && hooks[CONNECT].rejected && !replaced);
    encoding=hooks[CONNECT].encoding;tas_rn_probe_retry_hooks();assert(hooks[CONNECT].original==(IMP)native_connect && replaced==1);
    tas_rn_probe_retry_hooks();assert(replaced==1);
    return 0;
}
'''


class RNProbeTests(unittest.TestCase):
    def test_forwarding_header_privacy_and_abi_refusal(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        test_composer.ComposerTests().compile_run(
            HARNESS, [zig, "cc", "-fblocks", "-fsanitize=address,undefined"], runtime=True)


if __name__ == "__main__":
    unittest.main()
