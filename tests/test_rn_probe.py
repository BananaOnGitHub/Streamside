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
    {"SRWebSocket",0,0,0},{"RCTWebSocketModule",0,0,0},{"NSDictionary",0,0,0},
    {"NSArray",0,0,0},{"NSNumber",0,0,0},{"NSData",0,0,0},{"NSURLRequest",0,0,0},{"NSJSONSerialization",0,0,0} };
static struct Fake host={"NSString","irc-ws.chat.twitch.tv",0,0};
static struct Fake url={"NSURL",0,&host,0},socket={"SRWebSocket",0,&url,0};
static struct Fake receiver={"RCTWebSocketModule",0,0,0},event={"NSString","websocketMessage",0,0};
static struct Fake message={"NSString","@emotes=25:0-4;room-id=private :private!private PRIVMSG #private :Kappa private body\r\n",0,0};
static id decoded,test_request,test_url,test_data,test_gqlhost,test_path;
static unsigned json_calls;
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
    else if(o==test_request && !strcmp(sel,"URL")) result=test_url;
    else if(o==test_request && !strcmp(sel,"HTTPBody")) result=test_data;
    else if(o==test_url && !strcmp(sel,"host")) result=test_gqlhost;
    else if(o==test_url && !strcmp(sel,"path")) result=test_path;
    else if(!strcmp(sel,"host") || !strcmp(sel,"url") || !strcmp(sel,"objectForKey:") || !strcmp(sel,"URL") || !strcmp(sel,"HTTPBody") || !strcmp(sel,"path") || !strcmp(sel,"eventName")) result=o->inner;
    else if(!strcmp(sel,"count")) result=(id)(uintptr_t)o->chars;
    else if(!strcmp(sel,"respondsToSelector:")) result=(id)(uintptr_t)1;
    else if(!strcmp(sel,"objectAtIndex:")) { U i=va_arg(ap,U);assert(i<o->chars);result=((id *)o->inner)[i]; }
    else if(!strcmp(sel,"objectEnumerator")) result=o;
    else if(!strcmp(sel,"nextObject")) { if(o->chars) { o->chars--;result=o->inner; } }
    else if(!strcmp(sel,"JSONObjectWithData:options:error:")) { json_calls++;result=decoded; }
    else if(!strcmp(sel,"length")) result=(id)(uintptr_t)(o->chars || !o->text ? o->chars : strlen(o->text));
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
static unsigned surface_calls,js_calls,network_calls,dispatch_calls;
static id expected_args,expected_completion;
static id native_surface(id self,SEL sel,id name,int mode,id props) {
    assert(self==&receiver && !strcmp(sel,"surface") && !strcmp(name->text,"Candlelight") && mode==2 && props==&body);surface_calls++;return &socket;
}
static void native_js(id self,SEL sel,id module,id method,id args,id completion) {
    assert(self==&receiver && !strcmp(sel,"js") && !strcmp(module->text,"RCTDeviceEventEmitter") && !strcmp(method->text,"emit") && args==expected_args && completion==expected_completion);js_calls++;
}
static id native_network(id self,SEL sel,id query,id devtools,id completion) {
    assert(self==&receiver && !strcmp(sel,"network") && query==&body && devtools==&host && completion==expected_completion);network_calls++;return &socket;
}
static void native_dispatch(id self,SEL sel,id value) { assert(self==&receiver && !strcmp(sel,"dispatch") && value==&body);dispatch_calls++; }
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
    struct Fake name={"NSString","Candlelight",0,0};hooks[HOST_SURFACE_MODE].original=(IMP)native_surface;
    assert(host_surface_mode_hook(&receiver,"surface",&name,2,&body)==&socket && surface_calls==1 && surface_count==1);
    struct Fake unsafe_name={"NSString","private channel / secret",0,0};surface_name(&unsafe_name);assert(surface_count==1);
    struct Fake module={"NSString","RCTDeviceEventEmitter",0,0},method={"NSString","emit",0,0};
    id entries[]={&event,&body};struct Fake args={"NSArray",0,(id)entries,2};expected_args=&args;expected_completion=&host;
    hooks[CALLABLE_JS].original=(IMP)native_js;callable_js_hook(&receiver,"js",&module,&method,&args,&host);
    assert(js_calls==1 && js_module_device==1 && js_socket_handoff==1);
    hooks[NETWORK_BUILD].original=(IMP)native_network;assert(network_build_hook(&receiver,"network",&body,&host,&host)==&socket && network_calls==1);
    struct Fake event_name={"NSString","topEmoteSubmitEditing",0,0};id old=body.inner;body.inner=&event_name;
    hooks[DISPATCH_EVENT].original=(IMP)native_dispatch;dispatch_event_hook(&receiver,"dispatch",&body);assert(dispatch_calls==1 && native_events[2]==1);body.inner=old;
    struct Fake empty={"NSString","",0,0};value_shape(&empty);value_shape(&message);value_shape(nil);
    assert(input_values_empty==1 && input_values_nonempty==1 && input_values_other==1);
    struct Fake map={"NSDictionary",0,&name,70};map_shape(&map,0);assert(map.chars==38 && map_samples[0][0]==32);
    map_shape(nil,1);assert(map_shapes[1][0]==1);
    struct Fake op={"NSString","SendChatMessage",0,0},obj={"NSDictionary",0,&op,0};gql_object(&obj);assert(gql_operations[0]==1);
    op.text="secret SendChatMessage secret";gql_object(&obj);assert(gql_operations[0]==1);
    struct Fake data={"NSData",0,0,262145},gqlhost={"NSString","gql.twitch.tv",0,0};
    struct Fake path={"NSString","/gql",0,0},gqlurl={"NSURL",0,0,0},request={"NSURLRequest",0,0,0};
    test_request=&request;test_url=&gqlurl;test_data=&data;test_gqlhost=&gqlhost;test_path=&path;
    gql_request(&request);assert(gql_oversize==1 && !json_calls);
    data.chars=12;decoded=&obj;op.text="SendChatMessage";gql_request(&request);assert(json_calls==1 && gql_operations[0]==2);
    decoded=nil;gql_request(&request);assert(json_calls==2 && gql_unreadable==1);
    gqlhost.text="unrelated.test";gql_request(&request);assert(json_calls==2);id batch_entries[]={&obj,&obj};struct Fake batch={"NSArray",0,(id)batch_entries,2};
    op.text="ChatEmoteSets";for(U i=0;i<count(&batch);i++) gql_object(array_at(&batch,i));assert(gql_operations[2]==2);
    for(unsigned i=0;i<60;i++) trace(TRACE_GQL_SEND);
    assert(trace_count==48 && trace_rows[(trace_next+47)%48].sequence==trace_sequence);
    /* ABI mismatch must leave the native method intact. */
    for(unsigned i=0;i<HOOK_COUNT;i++) hooks[i].original=(IMP)native_connect;
    hooks[CONNECT].original=NULL;tas_rn_probe_retry_hooks();assert(!hooks[CONNECT].original && hooks[CONNECT].rejected && !replaced);
    encoding=hooks[CONNECT].encoding;tas_rn_probe_retry_hooks();assert(hooks[CONNECT].original==(IMP)native_connect && replaced==1);
    tas_rn_probe_retry_hooks();assert(replaced==1);
    char report[24576];tas_rn_probe_status(report,sizeof(report));
    assert(strstr(report,"Build 52 native handoffs") && strstr(report,"NETWORK") == NULL);
    assert(!strstr(report,"private channel") && !strstr(report,"Kappa") && !strstr(report,"room-id") && !strstr(report,"private body"));
    assert(strstr(report,"No JS parser/token/local-echo callback"));
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
