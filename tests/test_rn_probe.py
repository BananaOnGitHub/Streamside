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
    {"NSArray",0,0,0},{"NSNumber",0,0,0},{"NSData",0,0,0},{"NSURLRequest",0,0,0},{"NSJSONSerialization",0,0,0},
    {"UIView",0,0,0},{"RCTSurfaceHostingView",0,0,0},
    {ATTACHMENT,0,0,0},{"NSTextAttachment",0,0,0},{"NSAttributedString",0,0,0},
    {"UIImage",0,0,0},{"TwitchAnimatedImage",0,0,0},{"RCTParagraphComponentView",0,0,0} };
static int on_main=1;
int pthread_main_np(void) { return on_main; }
static id paragraph_value, attribute_attachment;
static bool invalid_attribute_range, tiny_attribute_runs;
static unsigned attribute_calls;
static struct Fake identifier_result={"NSString",0,0,0};
static struct Fake host={"NSString","irc-ws.chat.twitch.tv",0,0};
static struct Fake url={"NSURL",0,&host,0},socket={"SRWebSocket",0,&url,0};
static struct Fake receiver={"RCTWebSocketModule",0,0,0},event={"NSString","websocketMessage",0,0};
static struct Fake message={"NSString","@emotes=25:0-4;room-id=private :private!private PRIVMSG #private :Kappa private body\r\n",0,0};
static id decoded,test_request,test_url,test_data,test_gqlhost,test_path;
static unsigned json_calls;
static id catalog_test, catalog_keys[8], catalog_values[8];
static U catalog_cursor,catalog_value_cursor;
static struct Fake catalog_value_enumerator={"enumerator",0,0,0};
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
    if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(ap,Class);result=(id)(uintptr_t)(c && (!strcmp(o->cls,c->cls) || (!strcmp(c->cls,"UIView") && (!strcmp(o->cls,"RCTSurfaceHostingView") || !strcmp(o->cls,"RCTParagraphComponentView"))) || (!strcmp(c->cls,"NSTextAttachment") && !strcmp(o->cls,ATTACHMENT)))); }
    else if(!strcmp(sel,"stringWithUTF8String:")) { string.text=va_arg(ap,const char *);result=&string; }
    else if(!strcmp(sel,"isEqualToString:")) { id value=va_arg(ap,id);result=(id)(uintptr_t)!strcmp(o->text,value->text); }
    else if(!strcmp(sel,"accessibilityIdentifier")) { if(o->text) { identifier_result.text=o->text;result=&identifier_result; } }
    else if(!strcmp(sel,"attributedText")) result=paragraph_text_hook(o,sel);
    else if(!strcmp(sel,"image")) result=o->inner;
    else if(!strcmp(sel,"attribute:atIndex:effectiveRange:")) {
        id key=va_arg(ap,id);U at=va_arg(ap,U);Range *range=va_arg(ap,Range *);
        assert(!strcmp(key->text,"NSAttachment") && at<o->chars);attribute_calls++;
        *range=invalid_attribute_range ? (Range){at,0} : tiny_attribute_runs ? (Range){at,1} : (Range){0,o->chars};
        result=attribute_attachment;
    }
    else if(o==test_request && !strcmp(sel,"URL")) result=test_url;
    else if(o==test_request && !strcmp(sel,"HTTPBody")) result=test_data;
    else if(o==test_url && !strcmp(sel,"host")) result=test_gqlhost;
    else if(o==test_url && !strcmp(sel,"path")) result=test_path;
    else if(o==catalog_test && !strcmp(sel,"keyEnumerator")) { catalog_cursor=0;result=o; }
    else if(o==catalog_test && !strcmp(sel,"objectEnumerator")) { catalog_value_cursor=0;result=&catalog_value_enumerator; }
    else if(o==&catalog_value_enumerator && !strcmp(sel,"nextObject")) { if(catalog_value_cursor<catalog_test->chars) result=catalog_values[catalog_value_cursor++]; }
    else if(o==catalog_test && !strcmp(sel,"nextObject")) { if(catalog_cursor<o->chars) result=catalog_keys[catalog_cursor++]; }
    else if(o==catalog_test && !strcmp(sel,"objectForKey:")) { id key=va_arg(ap,id);for(U i=0;i<o->chars;i++) if(key==catalog_keys[i]) result=catalog_values[i]; }
    else if(!strcmp(sel,"host") || !strcmp(sel,"url") || !strcmp(sel,"objectForKey:") || !strcmp(sel,"URL") || !strcmp(sel,"HTTPBody") || !strcmp(sel,"path") || !strcmp(sel,"eventName") || !strcmp(sel,"superview") || !strcmp(sel,"surface") || !strcmp(sel,"moduleName")) result=o->inner;
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
static unsigned map_forwarded,getter_forwarded,url_forwarded,template_forwarded,layout_forwarded,factory_forwarded,template_get_forwarded;
static void native_map(id self,SEL sel,id value) { assert(self==&receiver && !strcmp(sel,"map") && value==catalog_test && input_consumer_depth==1);map_forwarded++; }
static id native_getter(id self,SEL sel) { assert(self==&receiver && !strcmp(sel,"map-get"));getter_forwarded++;return catalog_test; }
static id native_url(id self,SEL sel,id value,id base) { assert(self==&url && !strcmp(sel,"init-url") && value==&message && base==&host);url_forwarded++;return &socket; }
static id native_factory(id self,SEL sel,id value) { assert(self==&url && !strcmp(sel,"factory-url") && value==&message);factory_forwarded++;return &socket; }
static id native_template_get(id self,SEL sel) { assert(self==&receiver && !strcmp(sel,"template-get"));template_get_forwarded++;return &host; }
static void native_template(id self,SEL sel,id value) { assert(self==&receiver && !strcmp(sel,"template") && value==&host && input_consumer_depth==1);template_forwarded++; }
static void native_layout(id self,SEL sel) { assert(self==&receiver && !strcmp(sel,"layout") && input_consumer_depth==1);layout_forwarded++; }
static const char *encoding="wrong";
static bool diagnostic_abi, reject_attribute_abi, reject_view_abi;
static const char *selected_encoding;
Method class_getInstanceMethod(Class c,SEL s) {
    assert(c && s);selected_encoding=encoding;
    if(diagnostic_abi) {
        if(!strcmp(s,"accessibilityIdentifier") || !strcmp(s,"superview") || !strcmp(s,"attributedText") || !strcmp(s,"image")) selected_encoding=reject_view_abi ? "wrong" : "@16@0:8";
        else if(!strcmp(s,"length")) selected_encoding="Q16@0:8";
        else if(!strcmp(s,"attribute:atIndex:effectiveRange:")) selected_encoding=reject_attribute_abi ? "wrong" : "@40@0:8@16Q24^{_NSRange=QQ}32";
    }
    return (Method)&selected_encoding;
}
const char *method_getTypeEncoding(Method m) { return *(const char **)m; }
IMP method_getImplementation(Method m) { (void)m;return (IMP)native_connect; }
BOOL class_addMethod(Class c,SEL s,IMP i,const char *e) { (void)c;(void)s;(void)i;(void)e;return NO; }
IMP method_setImplementation(Method m,IMP i) { (void)m;assert(i==(IMP)connect_hook);replaced++;return (IMP)native_connect; }
static unsigned init_calls,base_init_calls,image_set_calls,state_calls,paragraph_layout_calls,paragraph_get_calls;
static id init_result,expected_image;
static id native_attach_init(id self,SEL sel,id data,id type) { assert(self==&receiver && !strcmp(sel,"attach-init") && data==&body && type==&host);init_calls++;return init_result; }
static id native_base_init(id self,SEL sel,id data,id type) { assert(self==&receiver && !strcmp(sel,"base-init") && data==&body && type==&host);base_init_calls++;return init_result; }
static void native_attach_set(id self,SEL sel,id value) { assert(self && !strcmp(sel,"set-image") && value==expected_image);image_set_calls++; }
static void native_paragraph_state(id self,SEL sel,const void *state,const void *old) { assert(self && !strcmp(sel,"state") && state==&body && old==&host);state_calls++; }
static void native_paragraph_layout(id self,SEL sel) { assert(self && !strcmp(sel,"paragraph-layout"));paragraph_layout_calls++; }
static id native_paragraph_text(id self,SEL sel) { assert(self && !strcmp(sel,"attributedText"));paragraph_get_calls++;return paragraph_value; }
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
    /* Full catalog snapshot: no source mutation, no retained keys/IDs. */
    struct Fake k0={"NSString","private-catalog-key",0,0},k1={"NSString","private-alias",0,0},k2={"NSNumber",0,0,0};
    struct Fake v0={"NSString","12345",0,0},v1={"NSString","native-opaque_1",0,0};
    struct Fake catalog={"NSDictionary",0,0,3};catalog_test=&catalog;
    catalog_keys[0]=&k0;catalog_keys[1]=&k1;catalog_keys[2]=&k2;
    catalog_values[0]=&v0;catalog_values[1]=&v0;catalog_values[2]=&v1;
    hooks[EMOTE_MAP].original=(IMP)native_map;emote_map_hook(&receiver,"map",&catalog);
    assert(map_forwarded==1 && !input_consumer_depth && catalog.chars==3);
    assert(catalogs[0].entries==3 && catalogs[0].distinct==2 && catalogs[0].repeated==1);
    assert(catalogs[0].string_keys==2 && catalogs[0].other_keys==1 && catalogs[0].decimal==2 && catalogs[0].opaque==1);
    hooks[MAP_GET].original=(IMP)native_getter;assert(map_get_hook(&receiver,"map-get")==&catalog && getter_forwarded==1);
    for(unsigned i=0;i<10;i++) catalog_snapshot(&receiver,&catalog);
    assert(catalogs[0].snapshots==SNAPSHOT_LIMIT && catalog_budget==4);
    catalog.chars=CATALOG_LIMIT+1;catalog_snapshot(&receiver,&catalog);assert(catalog_oversize==1);catalog.chars=3;
    /* A rejected scope getter does not guess a module or read props. */
    assert(input_scope(&receiver)==0);
    struct Fake theatre_name={"NSString","TwitchRNTheatre",0,0},theatre_surface={"RCTFabricSurface",0,&theatre_name,0};
    struct Fake hosting={"RCTSurfaceHostingView",0,&theatre_surface,0},scoped_input={"UIView",0,&hosting,0};
    assert(input_scope(&scoped_input)==0);encoding="@16@0:8";
    assert(input_scope(&scoped_input)==1);encoding="wrong";
    hooks[INPUT_LAYOUT].original=(IMP)native_layout;input_layout_hook(&receiver,"layout");assert(layout_forwarded==1 && !input_consumer_depth);
    const char *native_template_text="https://static-cdn.jtvnw.net/emoticons/v2/{id}/default/dark/3.0";
    struct Fake tmpl={"NSString",native_template_text,0,0};assert(template_kind(&tmpl)==1);
    tmpl.text="https://static-cdn.jtvnw.net/emoticons/v2/{id}/static/dark/3.0";assert(template_kind(&tmpl)==2);
    tmpl.text="https://unrelated.test/private";assert(template_kind(&tmpl)==0);
    tmpl.chars=1025;assert(template_kind(&tmpl)==0);
    hooks[TEMPLATE].original=(IMP)native_template;template_hook(&receiver,"template",&host);assert(template_forwarded==1 && !input_consumer_depth);
    hooks[TEMPLATE_GET].original=(IMP)native_template_get;assert(template_get_hook(&receiver,"template-get")==&host && template_get_forwarded==1);
    struct Fake image_url={"NSString","https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0",0,0};
    input_consumer_depth=1;observe_url_string(&image_url,NULL,0);input_consumer_depth=0;
    assert(consumer_urls[0]==1 && url_sources[0]==1);
    image_url.text="https://unrelated.test/emoticons/v2/25/default/dark/1.0";observe_url_string(&image_url,NULL,0);assert(consumer_urls[0]==1);
    hooks[URL_INIT].original=(IMP)native_url;assert(url_init_hook(&url,"init-url",&message,&host)==&socket && url_forwarded==1);
    hooks[URL_FACTORY].original=(IMP)native_factory;assert(url_factory_hook(&url,"factory-url",&message)==&socket && factory_forwarded==1);
    /* Four weak slots are bounded; dead identity reuse drops its old stats. */
    struct Fake inputs[4]={{"input",0,0,0},{"input",0,0,0},{"input",0,0,0},{"input",0,0,0}};
    assert(input_slot(&inputs[0],1)==1 && input_slot(&inputs[1],2)==2 && input_slot(&inputs[2],3)==3);
    assert(input_slot(&inputs[3],0)==INPUT_SLOTS && catalog_overflow==1);
    catalogs[1].entries=999;catalogs[1].snapshots=SNAPSHOT_LIMIT;objc_storeWeak(&catalogs[1].input,nil);
    assert(input_slot(&inputs[3],0)==1 && !catalogs[1].entries && !catalogs[1].snapshots && !catalogs[1].scope);
    uint64_t ordered=tag_ranges[0],invalid=tag_ranges[2];
    const char *tags="25:0-4,6-10/native-opaque_1:12-12/reversed:9-1/bad:x-4";
    observe_emote_tag(tags,tags+strlen(tags));assert(tag_ranges[0]==ordered+3 && tag_ranges[1]==1 && tag_ranges[2]==invalid+1);
    uint64_t pos;const char *maximum="18446744073709551615",*overflow="18446744073709551616";
    assert(position_number(maximum,maximum+20,&pos) && pos==UINT64_MAX);
    assert(!position_number(overflow,overflow+20,&pos));
    char large_tag[4097];memset(large_tag,'x',sizeof(large_tag));observe_emote_tag(large_tag,large_tag+sizeof(large_tag));assert(tag_budget==1);
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
    /* Build 54: returned identities/arguments remain unchanged, including an
     * initializer returning a replacement object and unrelated base receivers. */
    diagnostic_abi=true;
    struct Fake native_attachment={ATTACHMENT,0,0,0},other_attachment={"NSTextAttachment",0,0,0};
    struct Fake image={"UIImage",0,0,0},animated_image={"TwitchAnimatedImage",0,0,0};
    hooks[ATTACH_INIT].original=(IMP)native_attach_init;hooks[FOUNDATION_ATTACH_INIT].original=(IMP)native_base_init;
    init_result=&native_attachment;input_consumer_depth=1;
    assert(attachment_init_hook(&receiver,"attach-init",&body,&host)==init_result);
    assert(foundation_attachment_init_hook(&receiver,"base-init",&body,&host)==init_result);
    input_consumer_depth=0;init_result=&other_attachment;
    assert(foundation_attachment_init_hook(&receiver,"base-init",&body,&host)==init_result);
    assert(init_calls==1 && base_init_calls==2 && attachment_inits[0]==1 && attachment_inits[1]==1 && attachment_init_nested[0]==1 && attachment_init_nested[1]==1);
    hooks[ATTACH_IMAGE_SET].original=(IMP)native_attach_set;expected_image=&image;
    attachment_image_set_hook(&native_attachment,"set-image",expected_image);
    attachment_image_set_hook(&other_attachment,"set-image",expected_image);
    expected_image=nil;attachment_image_set_hook(&native_attachment,"set-image",nil);
    assert(image_set_calls==3 && attachment_image_sets==2 && attachment_set_images[0]==1 && attachment_set_images[1]==1);
    native_attachment.inner=&image;attachment_image_at_bounds(&native_attachment);
    native_attachment.inner=&animated_image;attachment_image_at_bounds(&native_attachment);
    native_attachment.inner=nil;attachment_image_at_bounds(&native_attachment);
    assert(attachment_bounds_images[0]==1 && attachment_bounds_images[1]==1 && attachment_bounds_images[2]==1);
    reject_view_abi=true;attachment_image_at_bounds(&native_attachment);assert(attachment_image_getter_refusals==1);reject_view_abi=false;
    /* Parent marker is accepted only together with a chat-region ancestor. */
    struct Fake region={"UIView","chat-message-region",0,0},pressable={"UIView","chat-message-pressable",&region,0};
    struct Fake paragraph={"RCTParagraphComponentView",0,&pressable,0};
    assert(paragraph_chat_scope(&paragraph));pressable.inner=nil;assert(!paragraph_chat_scope(&paragraph));pressable.inner=&region;
    reject_view_abi=true;assert(!paragraph_chat_scope(&paragraph));reject_view_abi=false;
    struct Fake cycle={"UIView",0,0,0};cycle.inner=&cycle;assert(!paragraph_chat_scope(&cycle) && paragraph_hierarchy_refusals==1);
    hooks[PARAGRAPH_STATE].original=(IMP)native_paragraph_state;hooks[PARAGRAPH_LAYOUT].original=(IMP)native_paragraph_layout;hooks[PARAGRAPH_TEXT].original=(IMP)native_paragraph_text;
    struct Fake attributed={"NSAttributedString","private-rendered-text",0,4};paragraph_value=&attributed;attribute_attachment=&other_attachment;
    paragraph_state_hook(&paragraph,"state",&body,&host);
    paragraph_layout_hook(&paragraph,"paragraph-layout");
    assert(paragraph_text_hook(&paragraph,"attributedText")==&attributed);
    assert(state_calls==1 && paragraph_layout_calls==1 && paragraph_get_calls==3 && paragraph_reads==2 && paragraph_snapshots==3 && paragraph_other_attachments==3);
    assert(paragraph_scope_hits[0]==1 && paragraph_scope_hits[1]==1 && paragraph_scope_hits[2]==1 && !paragraph_probe_depth);
    attribute_attachment=&native_attachment;paragraph_snapshot(&attributed);assert(paragraph_native_attachments==1);
    attribute_attachment=&image;paragraph_snapshot(&attributed);assert(paragraph_invalid_attachments==1);
    paragraph_value=nil;assert(!paragraph_text_hook(&paragraph,"attributedText") && paragraph_nil==1);
    paragraph_snapshot(&image);assert(paragraph_other==1);attributed.chars=0;attributed.text=NULL;paragraph_snapshot(&attributed);assert(paragraph_empty==1);attributed.text="private-rendered-text";
    attributed.chars=PARAGRAPH_LENGTH_LIMIT+1;paragraph_snapshot(&attributed);assert(paragraph_length_refusals==1);attributed.chars=4;
    reject_attribute_abi=true;paragraph_snapshot(&attributed);assert(paragraph_attribute_refusals==1);reject_attribute_abi=false;
    invalid_attribute_range=true;paragraph_snapshot(&attributed);assert(paragraph_run_refusals==1);invalid_attribute_range=false;
    tiny_attribute_runs=true;attributed.chars=PARAGRAPH_RUN_LIMIT+1;paragraph_snapshot(&attributed);assert(paragraph_run_refusals==2);tiny_attribute_runs=false;attributed.chars=4;
    on_main=0;unsigned reads_before=paragraph_get_calls;paragraph_layout_hook(&paragraph,"paragraph-layout");
    assert(paragraph_off_main==1 && paragraph_get_calls==reads_before && paragraph_layout_calls==2);on_main=1;
    paragraph.inner=nil;paragraph_read(&paragraph,0);assert(paragraph_unscoped[0]==1);paragraph.inner=&pressable;
    paragraph_snapshots=PARAGRAPH_SNAPSHOT_LIMIT;unsigned attrs_before=attribute_calls;
    paragraph_read(&paragraph,1);paragraph_snapshot(&attributed);
    assert(paragraph_budget==2 && attribute_calls==attrs_before && paragraph_get_calls==reads_before);
    diagnostic_abi=false;
    /* ABI mismatch must leave the native method intact. */
    for(unsigned i=0;i<HOOK_COUNT;i++) hooks[i].original=(IMP)native_connect;
    hooks[CONNECT].original=NULL;tas_rn_probe_retry_hooks();assert(!hooks[CONNECT].original && hooks[CONNECT].rejected && !replaced);
    encoding=hooks[CONNECT].encoding;tas_rn_probe_retry_hooks();assert(hooks[CONNECT].original==(IMP)native_connect && replaced==1);
    tas_rn_probe_retry_hooks();assert(replaced==1);
    char report[32768];tas_rn_probe_status(report,sizeof(report));
    assert(strstr(report,"Build 52 native handoffs") && strstr(report,"Build 53 catalog/metadata consumer") && strstr(report,"Build 54 attachment/paragraph consumers") && strstr(report,"NETWORK") == NULL);
    assert(!strstr(report,"private channel") && !strstr(report,"Kappa") && !strstr(report,"room-id") && !strstr(report,"private body"));
    assert(strstr(report,"No JS parser/token/local-echo callback"));
    assert(!strstr(report,"private-catalog-key") && !strstr(report,"native-opaque_1") && !strstr(report,"12345") && !strstr(report,"{id}"));
    assert(!strstr(report,"private-rendered-text"));
    /* Report tail survives maximum-width first-receiver/caller fields. */
    for(unsigned i=0;i<HOOK_COUNT;i++) {
        memset(hooks[i].receiver,'x',sizeof(hooks[i].receiver)-1);hooks[i].receiver[sizeof(hooks[i].receiver)-1]=0;
        memset(hooks[i].caller,'x',sizeof(hooks[i].caller)-1);hooks[i].caller[sizeof(hooks[i].caller)-1]=0;
        hooks[i].calls=UINT64_MAX;hooks[i].caller_offset=UINTPTR_MAX;
    }
    tas_rn_probe_status(report,sizeof(report));assert(strstr(report,"No JS parser/token/local-echo callback"));
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
