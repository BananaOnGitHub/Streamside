"""Exercise the production RN delegate and shared IRC rewrite, not a JS mock."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_emote_ui import RUNTIME
from test_provider_presentation_route import HARNESS as ROUTE, ASSOCIATED as ROUTE_ASSOCIATED

ROOT = Path(__file__).resolve().parent.parent
EXTRA = r'''
    else if(!strcmp(sel,"url"))result=o->children[0];
    else if(!strcmp(sel,"scheme")) {
        const char *end=strstr(o->value,"://");assert(end);char scheme[32];
        size_t n=(size_t)(end-o->value);assert(n<sizeof(scheme));memcpy(scheme,o->value,n);scheme[n]=0;result=string(scheme);
    } else if(!strcmp(sel,"lengthOfBytesUsingEncoding:")) {
        assert(va_arg(args,unsigned long)==4);result=(id)(uintptr_t)(o->byte_count ? o->byte_count : strlen(o->payload ? o->payload : o->value));
    } else if(!strcmp(sel,"stringValue")) { char value[64];snprintf(value,sizeof(value),"%llu",(unsigned long long)o->number);result=string(value); }
    else if(!strcmp(sel,"integerValue"))result=(id)(uintptr_t)o->number;
    else if(!strcmp(sel,"array") || !strcmp(sel,"dictionary"))result=fresh(o->cls);
    else if(!strcmp(sel,"alloc"))result=fresh(o->cls);
    else if(!strcmp(sel,"initWithString:")) { id s=va_arg(args,id);o->children[0]=s;result=o; }
    else if(!strcmp(sel,"autorelease"))result=o;
    else if(!strcmp(sel,"string"))result=o->children[0];
    else if(!strcmp(sel,"type"))result=(id)(uintptr_t)o->number;
    else if(!strcmp(sel,"length"))result=(id)(uintptr_t)o->byte_count;
    else if(!strcmp(sel,"standardUserDefaults")) { static id preferences; if(!preferences)preferences=fresh("NSUserDefaults");result=preferences; }
    else if(!strcmp(sel,"arrayForKey:")) {
        id key=va_arg(args,id);for(size_t i=0;i<o->count;i++)if(!strcmp(o->keys[i]->value,key->value))result=o->values[i];
    } else if(!strcmp(sel,"isEqual:")) { id other=va_arg(args,id);result=(id)(uintptr_t)(o->number==other->number); }
    else if(!strcmp(sel,"removeObject:")) {
        id value=va_arg(args,id);for(size_t i=0;i<o->count;) {
            if(!strcmp(o->children[i]->value,value->value)) { memmove(o->children+i,o->children+i+1,(o->count-i-1)*sizeof(id));o->count--; } else i++;
        }
    } else if(!strcmp(sel,"insertObject:atIndex:")) {
        id value=va_arg(args,id);size_t index=va_arg(args,size_t);assert(index<=o->count && o->count<64);
        memmove(o->children+index+1,o->children+index,(o->count-index)*sizeof(id));o->children[index]=value;o->count++;
    }
'''
MAIN = r'''
static int picker_mode;
int ss_composer_suggestion_mode(void) { return picker_mode; }
void *_NSConcreteStackBlock[32];
/* Minimal Blocks ABI lifetime fixture. Foundation copies escaping completions;
 * exercise compiler-generated copy/dispose helpers, including nested blocks. */
typedef struct TestBlock {
    void *isa;int flags,reserved;void (*invoke)(void);
    struct TestBlockDescriptor { unsigned long reserved,size;
        void (*copy)(void *,const void *);void (*dispose)(const void *); } *descriptor;
} TestBlock;
static unsigned nested_block_copies;
static void *copy_block(const void *value) {
    TestBlock *b=(TestBlock *)value;
    if(!b || (b->flags&(1<<28)))return b;
    if(b->flags&(1<<24)){b->flags++;return b;}
    TestBlock *out=malloc(b->descriptor->size);assert(out);
    memcpy(out,b,b->descriptor->size);out->flags|=(1<<24)|1;
    if(b->flags&(1<<25))b->descriptor->copy(out,b);
    return out;
}
static void release_block(const void *value) {
    TestBlock *b=(TestBlock *)value;
    if(!b || !(b->flags&(1<<24)))return;
    if((b->flags&65535)>1){b->flags--;return;}
    if(b->flags&(1<<25))b->descriptor->dispose(b);
    free(b);
}
void _Block_object_assign(void *destination,const void *value,int flags) {
    assert(flags==7);nested_block_copies++;*(void **)destination=copy_block(value);
}
void _Block_object_dispose(const void *value,int flags) { assert(flags==7);release_block(value); }
void tas_diag_log(const char *event,const char *detail) { (void)event;(void)detail; }
static unsigned preview_image_calls;
void tas_rn_composer_ui_image(uint64_t number,id data,id response,id error) {
    assert(number);(void)data;(void)response;(void)error;preview_image_calls++;
}
void tas_rn_composer_ui_retry_hooks(void) {}
static unsigned deliveries;
static id delivered,expected_self,expected_socket;
static void original(id self,SEL command,id socket,id message) {
    assert(self==expected_self && socket==expected_socket);
    assert(!strcmp(command,"webSocket:didReceiveMessage:"));deliveries++;delivered=message;
}
static void receive(id socket,id message) {
    expected_socket=socket;unsigned before=deliveries;
    rn_receive(expected_self,"webSocket:didReceiveMessage:",socket,message);
    assert(deliveries==before+1);
}
static Room *ready(const char *number) {
    Room *r=room_locked(number,time(NULL));snprintf(r->login,sizeof(r->login),"fixture");
    for(unsigned i=0;i<3;i++)r->loaded[i]=true;return r;
}
static void check_body(id input,id output) {
    const char *a=strstr(input->value," PRIVMSG #"),*b=strstr(output->value," PRIVMSG #");
    assert(a && b && !strcmp(a,b)); /* command, channel and body byte-identical */
}
static void flow(void) {
    g_enabled=true;for(unsigned i=0;i<3;i++)g_global.loaded[i]=true;
    Room *r=ready("42");ready("43");
    add_emote_locked(r,MAX_ROOM,"Square","https://cdn.7tv.app/emote/square/2x.webp",0,false,NULL,1);
    add_emote_locked(r,MAX_ROOM,"Kappa","https://cdn.7tv.app/emote/collision/2x.webp",0,false,NULL,1);
    add_emote_locked(&g_global,MAX_GLOBAL,"Global","https://cdn.betterttv.net/emote/global/2x",1,true,NULL,1);
    uint64_t number=find_word(r,"Square")->fake_id;
    expected_self=fresh("RCTWebSocketModule");g_rn_receive=(IMP)original;
    id socket=fresh("SRWebSocket"),url=fresh("NSURL");socket->children[0]=url;
    snprintf(url->value,sizeof(url->value),"wss://irc-ws.chat.twitch.tv:443");
    id input=string("@room-id=42;emotes=25:0-4 :u!u@h PRIVMSG #fixture :Kappa Square");
    receive(socket,input);assert(delivered!=input);check_body(input,delivered);
    char expected[256];snprintf(expected,sizeof(expected),"@room-id=42;emotes=25:0-4/%llu:6-11 :u!u@h PRIVMSG #fixture :Kappa Square",(unsigned long long)number);
    assert(!strcmp(delivered->value,expected));
    /* Existing redirect resolves the same ID without modifying the request. */
    id request=fresh("NSMutableURLRequest"),cdn=fresh("NSURL");request->children[0]=cdn;
    snprintf(cdn->value,sizeof(cdn->value),"https://static-cdn.jtvnw.net/emoticons/v2/%llu/default/dark/1.0",(unsigned long long)number);
    id redirected=tas_emotes_rewrite_request_copy(request);
    assert(redirected && !strcmp(redirected->children[0]->value,"https://cdn.7tv.app/emote/square/2x.webp"));
    assert(tas_emotes_is_redirected_image_url(redirected->children[0]));
    assert(!tas_emotes_is_redirected_image_url(request->children[0]));
    assert(strstr(cdn->value,"static-cdn.jtvnw.net"));
    /* Unicode code points (not UTF-16 or bytes), punctuation, repeated matches. */
    input=string("@room-id=42;emotes= :u!u@h PRIVMSG #fixture :😀 é Square (Square)");
    receive(socket,input);snprintf(expected,sizeof(expected),"emotes=%llu:4-9/%llu:12-17",(unsigned long long)number,(unsigned long long)number);
    assert(strstr(delivered->value,expected));check_body(input,delivered);
    /* A control line at the start must not hide subsequent tagged IRC lines. */
    input=string("PING :tmi.twitch.tv\r\n@room-id=42 :u!u@h PRIVMSG #fixture :Square\r\n");
    receive(socket,input);assert(delivered!=input && !strncmp(delivered->value,"PING :tmi.twitch.tv\r\n",20));
    assert(strstr(delivered->value,";emotes=") && strstr(delivered->value," :Square\r\n"));
    /* Re-delivery is idempotent and retains the rewritten object's identity. */
    input=delivered;receive(socket,input);assert(delivered==input);
    /* Similar tag names cannot hide real native ranges or create duplicates. */
    input=string("@room-id=42;notemotes=x;emotes=25:0-5 :u!u@h PRIVMSG #fixture :Square");
    receive(socket,input);assert(delivered==input);
    input=string("@room-id=42;notemotes=x;emotes= :u!u@h PRIVMSG #fixture :Square");
    receive(socket,input);assert(delivered!=input && strstr(delivered->value,";notemotes=x;emotes=9"));
    const char *unchanged[]={
        "@room-id=42;emotes=25:0-5 :u!u@h PRIVMSG #fixture :Square",
        "@room-id=42;emotes=25:2-8 :u!u@h PRIVMSG #fixture :Square", /* partial overlap */
        "@room-id=42;emotes=;emotes= :u!u@h PRIVMSG #fixture :Square",
        "@room-id=43 :u!u@h PRIVMSG #fixture :Square", /* no other-room fallback */
        "@room-id=42;source-room-id=43 :u!u@h PRIVMSG #fixture :Square",
        "@room-id=42;source-room-id=bad :u!u@h PRIVMSG #fixture :Square",
        "@room-id=bad :u!u@h PRIVMSG #fixture :Square",
        "@emotes= :u!u@h PRIVMSG #fixture :Square",
        "@room-id=42 :s NOTICE #fixture :fake PRIVMSG #fixture :Square",
        "@room-id=42 :s CLEARMSG #fixture :Square",
        "@room-id=42 :s ROOMSTATE #fixture",
        "@room-id=42 :u!u@h PRIVMSG #fixture :square unknown",
        "PING :tmi.twitch.tv",
        ""
    };
    for(unsigned i=0;i<sizeof(unchanged)/sizeof(unchanged[0]);i++) { input=string(unchanged[i]);receive(socket,input);assert(delivered==input); }
    input=string("@room-id=43 :u!u@h PRIVMSG #fixture :Global");receive(socket,input);assert(delivered!=input);
    /* Non-chat sockets, binary frames, disabled preference: original objects. */
    input=string("@room-id=42 :u!u@h PRIVMSG #fixture :Square");
    const char *hosts[]={"wss://example.com/","wss://irc-ws.chat.twitch.tv.evil/","https://irc-ws.chat.twitch.tv/"};
    for(unsigned i=0;i<3;i++) { snprintf(url->value,sizeof(url->value),"%s",hosts[i]);receive(socket,input);assert(delivered==input); }
    snprintf(url->value,sizeof(url->value),"wss://irc-ws.chat.twitch.tv/");
    receive(fresh("NSObject"),input);assert(delivered==input);
    id binary=fresh("NSData");receive(socket,binary);assert(delivered==binary);
    receive(socket,nil);assert(!delivered);
    g_enabled=false;receive(socket,input);assert(delivered==input);g_enabled=true;
    /* Embedded NUL and oversized input must not truncate or partially rewrite. */
    input=string("@room-id=42 :u!u@h PRIVMSG #fixture :Square");input->byte_count=strlen(input->value)+2;
    receive(socket,input);assert(delivered==input);
    char *large=malloc(MAX_FRAME+2);assert(large);memset(large,'a',MAX_FRAME+1);large[MAX_FRAME+1]=0;
    input=fresh("NSString");input->payload=large;receive(socket,input);assert(delivered==input);free(large);
    /* Oversized authentic metadata passes through instead of hiding overlaps. */
    large=malloc(4500);assert(large);size_t used=(size_t)sprintf(large,"@room-id=42;emotes=");
    memset(large+used,'1',4096);used+=4096;strcpy(large+used," :u!u@h PRIVMSG #fixture :Square");
    input=fresh("NSString");input->payload=large;receive(socket,input);assert(delivered==input);free(large);
    /* Refuse the entire frame when accumulated expansions exceed its budget. */
    add_emote_locked(r,MAX_ROOM,"S","https://cdn.7tv.app/emote/s/2x.webp",0,false,NULL,1);
    large=calloc(1,6000);assert(large);used=0;
    for(unsigned row=0;row<10;row++) {
        used+=(size_t)sprintf(large+used,"@room-id=42 :u!u@h PRIVMSG #fixture :");
        for(unsigned word=0;word<200;word++) { large[used++]='S';large[used++]=' '; }
        large[used++]='\r';large[used++]='\n';
    }
    large[used]=0;input=fresh("NSString");input->payload=large;
    uint64_t rewrites=PROBE_GET(g_rn_rewritten);receive(socket,input);
    assert(delivered==input && PROBE_GET(g_rn_rewritten)==rewrites);free(large);
    /* Shared refactor preserves the old NSURLSession message wrapper contract. */
    input=string("@room-id=42 :u!u@h PRIVMSG #fixture :Square");
    id wrapped=fresh("NSURLSessionWebSocketMessage");wrapped->number=1;wrapped->children[0]=input;
    id rewritten=rewrite_message(wrapped);assert(rewritten && rewritten!=wrapped && rewritten->children[0]!=input);
    wrapped->number=0;assert(!rewrite_message(wrapped));
    assert(PROBE_GET(g_rn_rewritten)>0 && PROBE_GET(g_frame_refused)==3);
    assert(r->size==3 && !strcmp(find_word(r,"Square")->name,"Square"));
}
static void widths(void) {
    flow();
    Room *r=ready("42");
    add_emote_locked(r,MAX_ROOM,"Wide","https://cdn.7tv.app/emote/wide/2x.webp",0,false,NULL,3.2);
    Emote *e=find_word(r,"Wide");assert(e && !e->width_id);
    id input=string("@room-id=42;emotes=25:0-4 :u!u@h PRIVMSG #fixture :Kappa Wide");
    __atomic_store_n(&g_rn_width_ready,true,__ATOMIC_RELEASE);
    receive(expected_socket,input);check_body(input,delivered);
    uint64_t alias=tas_rn_width_id(e->fake_id,3.2);
    char expected[256];snprintf(expected,sizeof(expected),"@room-id=42;emotes=25:0-4/%llu:6-9 :u!u@h PRIVMSG #fixture :Kappa Wide",(unsigned long long)alias);
    assert(!strcmp(delivered->value,expected) && e->width_id==alias && alias!=e->fake_id);
    assert(alias%10000==3200 && tas_emotes_aspect(alias)==3.2);
    id request=fresh("NSMutableURLRequest"),url=fresh("NSURL");request->children[0]=url;
    snprintf(url->value,sizeof(url->value),"https://static-cdn.jtvnw.net/emoticons/v2/%llu/default/dark/2.0",(unsigned long long)alias);
    id redirect=tas_emotes_rewrite_request_copy(request);
    assert(redirect && !strcmp(redirect->children[0]->value,e->url));
    /* Dimensions freeze per alias; a cached URL never changes bitmap identity. */
    e->aspect=2;receive(expected_socket,input);assert(e->width_id==alias);
    /* Legacy and failed-admission RN retain build-55 IDs. */
    id legacy=rewrite_text(input);assert(legacy && strstr(legacy->value,"Wide"));
    snprintf(expected,sizeof(expected),"/%llu:",(unsigned long long)e->fake_id);assert(strstr(legacy->value,expected));
    __atomic_store_n(&g_rn_width_ready,false,__ATOMIC_RELEASE);
    receive(expected_socket,input);assert(strstr(delivered->value,expected));
    /* Collision fails closed without dropping the incoming emote. */
    add_emote_locked(r,MAX_ROOM,"Clash","https://cdn.7tv.app/emote/clash/2x.webp",0,false,NULL,1);
    e=find_word(r,"Wide"); /* Sorted insertion may move registry entries. */
    Emote *clash=find_word(r,"Clash");clash->width_id=tas_rn_width_id(e->fake_id,e->aspect);e->width_id=0;
    __atomic_store_n(&g_rn_width_ready,true,__ATOMIC_RELEASE);
    receive(expected_socket,input);assert(!e->width_id && strstr(delivered->value,expected));
    assert(PROBE_GET(g_rn_width_collisions)==1);
    /* Eviction/history maps both aliases until the existing grace expires. */
    e->width_id=alias;retire_emote_locked(e,time(NULL));
    assert(emote_for_id_locked(alias));
    char *mapped=url_for_id_locked(alias,time(NULL));assert(mapped && !strcmp(mapped,"https://cdn.7tv.app/emote/wide/2x.webp"));free(mapped);
}
struct FakeMethod { SEL name;const char *encoding;IMP imp; };
static id expected_url_session,url_original_task,url_original_url,url_original_completion;
static id url_original_data,url_original_response,url_original_error;
static unsigned url_original_calls,url_callback_calls;
static bool url_deliver;
static void *url_deferred_completion;
static id original_url_completion(id self,SEL sel,id url,id completion) {
    assert(self==expected_url_session && !strcmp(sel,"dataTaskWithURL:completionHandler:"));
    url_original_calls++;url_original_url=url;url_original_completion=completion;
    if (url_deliver && completion) ((void (^)(id,id,id))completion)(url_original_data,url_original_response,url_original_error);
    if (!url_deliver && completion) {
        release_block(url_deferred_completion);url_deferred_completion=copy_block(completion);
    }
    return url_original_task;
}
static struct FakeMethod public_url_method={"dataTaskWithURL:completionHandler:","@32@0:8@16@?24",(IMP)original_url_completion};
static struct FakeMethod private_url_method={"dataTaskWithURL:completionHandler:","@32@0:8@16@24",(IMP)original_url_completion};
static bool public_url_owned=true,private_url_owned=true;
static struct FakeMethod receive_method={"webSocket:didReceiveMessage:","v32@0:8@16@24",(IMP)original};
static struct FakeMethod url_method={"url","@16@0:8",(IMP)original};
static unsigned source_calls;
static id source_original(id self,SEL sel) { assert(!strcmp(sel,"data"));source_calls++;return self->children[0]; }
static struct FakeMethod source_method={"data","@16@0:8",(IMP)source_original};
static bool has_class=true,own_method=true;
static unsigned replacements;
Method *class_copyMethodList(Class cls,unsigned *n) {
    *n=own_method ? 1 : 0;Method *out=malloc(sizeof(Method));
    if(!strcmp(cls->cls,"NSURLSession")) {*n=public_url_owned ? 1 : 0;out[0]=&public_url_method;return out;}
    if(!strcmp(cls->cls,"__NSURLSessionLocal")) {*n=private_url_owned ? 1 : 0;out[0]=&private_url_method;return out;}
    out[0]=!strcmp(cls->cls,"RCTSource") ? &source_method : &receive_method;return out;
}
Method class_getInstanceMethod(Class cls,SEL sel) { (void)cls;return !strcmp(sel,"url") && has_class ? &url_method : NULL; }
SEL method_getName(Method m) { return sel_registerName(((struct FakeMethod *)m)->name); }
const char *method_getTypeEncoding(Method m) { return ((struct FakeMethod *)m)->encoding; }
IMP method_getImplementation(Method m) { return ((struct FakeMethod *)m)->imp; }
IMP method_setImplementation(Method m,IMP replacement) { struct FakeMethod *f=m;IMP old=f->imp;f->imp=replacement;replacements++;return old; }
id objc_getAssociatedObject(id obj,const void *key) {
    for(size_t i=0;i<obj->count;i++)if(obj->keys[i]==(id)key)return obj->values[i];return nil;
}
void objc_setAssociatedObject(id obj,const void *key,id value,uintptr_t policy) {
    assert(policy==1);
    for(size_t i=0;i<obj->count;i++)if(obj->keys[i]==(id)key){obj->values[i]=value;return;}
    assert(obj->count<8);obj->keys[obj->count]=(id)key;obj->values[obj->count++]=value;
}
static void installation(void) {
    g_rn_receive=NULL;has_class=false;install_rn_receive();assert(!g_rn_receive);
    has_class=true;own_method=false;install_rn_receive();assert(!g_rn_receive);
    own_method=true;receive_method.encoding="@32@0:8@16@24";install_rn_receive();assert(!g_rn_receive);
    receive_method.encoding="v32@0:8@16@24";url_method.encoding="q16@0:8";install_rn_receive();assert(!g_rn_receive);
    url_method.encoding="@16@0:8";install_rn_receive();assert(g_rn_receive==(IMP)original && replacements==1);
    install_rn_receive();assert(replacements==1); /* no self-hook recursion */
}
static void source_hook(void) {
    own_method=false;install_rn_width();assert(!g_rn_source_data);
    own_method=true;source_method.encoding="q16@0:8";install_rn_width();assert(!g_rn_source_data);
    source_method.encoding="@16@0:8";install_rn_width();assert(g_rn_source_data==(IMP)source_original && replacements==1);
    install_rn_width();assert(replacements==1);
    id source=fresh("RCTSource"),data=fresh("NSData");source->children[0]=data;data->byte_count=12;
    g_enabled=false;assert(rn_source_data(source,"data")==data && source_calls==1 && !source->count);
    g_enabled=true;assert(rn_source_data(source,"data")==data && source_calls==2 && !g_rn_width_ready);
    assert(PROBE_GET(g_rn_width_refused)==1);
    assert(rn_source_data(source,"data")==data && source_calls==3 && PROBE_GET(g_rn_width_refused)==1);
    id cached=fresh("NSData");objc_setAssociatedObject(source,&g_rn_width_data_key,cached,1);
    assert(rn_source_data(source,"data")==cached && source_calls==4);
}
static void local_echo(void) {
    g_enabled=true;g_rn_local_ready=true;g_rn_width_ready=true;
    for(unsigned i=0;i<3;i++)g_global.loaded[i]=true;
    Room *r=ready("42"),*other=ready("43");snprintf(other->login,sizeof(other->login),"other");
    snprintf(g_last_room,sizeof(g_last_room),"43");
    add_emote_locked(r,MAX_ROOM,"Wide","https://cdn.7tv.app/emote/wide/2x.gif",0,false,NULL,2.5);
    add_emote_locked(r,MAX_ROOM,"Kappa","https://cdn.7tv.app/emote/collision/2x.webp",0,false,NULL,1);
    add_emote_locked(other,MAX_ROOM,"Other","https://cdn.7tv.app/emote/other/2x.webp",0,false,NULL,1);
    add_emote_locked(&g_global,MAX_GLOBAL,"Global","https://cdn.betterttv.net/emote/global/2x",1,true,NULL,1);
    id input=string("@display-name=Me;id=local-echo-1;client-nonce=abc;emotes=25:0-4;reply-parent-msg-id=parent :me!me@me.tmi.twitch.tv PRIVMSG #fixture :Kappa 😀 Wide (Wide) Global Other");
    id output=rn_local_echo(nil,NULL,input);assert(output!=input);check_body(input,output);
    uint64_t wide=find_word(r,"Wide")->width_id,global=find_word(&g_global,"Global")->width_id;
    assert(wide%10000==2500 && global%10000==1000);
    char ranges[256];snprintf(ranges,sizeof(ranges),"emotes=25:0-4/%llu:8-11/%llu:14-17/%llu:20-25",(unsigned long long)wide,(unsigned long long)wide,(unsigned long long)global);
    assert(strstr(output->value,ranges) && strstr(output->value,";client-nonce=abc;") && strstr(output->value,";reply-parent-msg-id=parent"));
    assert(!strstr(output->value,"room-id=") && !strcmp(g_last_room,"43"));
    assert(PROBE_GET(g_rn_local_calls)==1 && PROBE_GET(g_rn_local_changed)==1);
    assert(!PROBE_GET(g_rn_rewritten) && !PROBE_GET(g_rewritten_frames) && !PROBE_GET(g_room_frames));
    assert(rn_local_echo(nil,NULL,output)==output); /* native ranges own every existing match */
    id request=fresh("NSMutableURLRequest"),cdn=fresh("NSURL");request->children[0]=cdn;
    snprintf(cdn->value,sizeof(cdn->value),"https://static-cdn.jtvnw.net/emoticons/v2/%llu/default/dark/1.0",(unsigned long long)wide);
    id redirected=tas_emotes_rewrite_request_copy(request);assert(redirected && strstr(redirected->children[0]->value,"wide/2x.gif"));
    const char *same[]={
        "@id=local-echo-2 :me!me@h PRIVMSG #other :Wide", /* explicit other room */
        "@id=local-echo-2 :me!me@h PRIVMSG #unknown :Global", /* no last-room/global-only guess */
        "@id=local-echo-2;emotes=25:1-3 :me!me@h PRIVMSG #fixture :Wide",
        "@id=local-echo-2;emotes=;emotes= :me!me@h PRIVMSG #fixture :Wide",
        "@id=server-1 :me!me@h PRIVMSG #fixture :Wide",
        "@id=local-echo- :me!me@h PRIVMSG #fixture :Wide",
        "@id=local-echo-x :me!me@h PRIVMSG #fixture :Wide",
        "@id=local-echo-2;room-id=42 :me!me@h PRIVMSG #fixture :Wide",
        "@id=local-echo-2;source-room-id=42 :me!me@h PRIVMSG #fixture :Wide",
        "@id=local-echo-2 :me!me@h NOTICE #fixture :Wide",
        "@id=local-echo-2 :me!me@h PRIVMSG #fixture :\1ACTION Wide\1",
        "@id=local-echo-2 :me!me@h PRIVMSG #fixture :Wide\r\nPING :x",
        "@id=local-echo-2 :me!me@h PRIVMSG #fixture :unknown wide",
        ""
    };
    for(unsigned i=0;i<sizeof(same)/sizeof(same[0]);i++) { input=string(same[i]);assert(rn_local_echo(nil,NULL,input)==input); }
    input=string("@id=local-echo-2 :me!me@h PRIVMSG #fixture :Wide");
    g_enabled=false;assert(rn_local_echo(nil,NULL,input)==input);g_enabled=true;
    g_rn_local_ready=false;assert(rn_local_echo(nil,NULL,input)==input);g_rn_local_ready=true;
    snprintf(other->login,sizeof(other->login),"fixture");assert(rn_local_echo(nil,NULL,input)==input); /* ambiguous mapping */
    assert(rn_local_echo(nil,NULL,fresh("NSData")));
    input->byte_count=MAX_FRAME+1;assert(rn_local_echo(nil,NULL,input)==input);
    input->byte_count=strlen(input->value)+1;assert(rn_local_echo(nil,NULL,input)==input); /* embedded NUL refused */
    uint64_t discoveries=PROBE_GET(g_rn_local_exports);
    const TASRNMethodInfo *info=rn_local_export(nil,NULL);
    assert(PROBE_GET(g_rn_local_exports)==discoveries+1);
    assert(!strcmp(info->js_name,"buildLocalEcho") && !strcmp(info->objc_name,"renderLocalBody:(NSString *)body channel:(NSString *)channel nativeRanges:(NSArray *)native") && info->synchronous);
    assert(!rn_local_main_queue(nil,NULL));
    assert(!strcmp(text(rn_local_module_name(nil,NULL)),"buildLocalEcho"));
    /* A quiet room is associated by ROOMSTATE, before any incoming PRIVMSG. */
    Room *quiet=ready("44");quiet->login[0]=0;
    add_emote_locked(quiet,MAX_ROOM,"Quiet","https://cdn.7tv.app/emote/quiet/2x.webp",0,false,NULL,1);
    const char *state="@room-id=44 :server ROOMSTATE #quiet";
    assert(!rewrite_line_impl(state,strlen(state),true) && !strcmp(quiet->login,"quiet"));
    input=string("@id=local-echo-3 :me!me@h PRIVMSG #quiet :Quiet");
    output=rn_local_echo(nil,NULL,input);assert(output!=input);check_body(input,output);
}
static id range_fixture(uint64_t first,uint64_t last) {
    id range=fresh("NSDictionary");range->count=3;
    range->keys[0]=string("id");range->values[0]=string("25");
    range->keys[1]=string("start");range->values[1]=fresh("NSNumber");range->values[1]->number=first;
    range->keys[2]=string("end");range->values[2]=fresh("NSNumber");range->values[2]->number=last;
    return range;
}
static void local_array(void) {
    g_enabled=true;g_rn_local_ready=true;g_rn_width_ready=true;
    for(unsigned i=0;i<3;i++)g_global.loaded[i]=true;
    Room *r=ready("42"),*other=ready("43");snprintf(other->login,sizeof(other->login),"other");
    snprintf(g_last_room,sizeof(g_last_room),"43");
    add_emote_locked(r,MAX_ROOM,"Square","https://cdn.7tv.app/emote/square/2x.webp",0,false,NULL,1);
    add_emote_locked(r,MAX_ROOM,"Wide","https://cdn.7tv.app/emote/wide/2x.gif",0,false,NULL,2.5);
    add_emote_locked(r,MAX_ROOM,"Kappa","https://cdn.7tv.app/emote/collision/2x.webp",0,false,NULL,1);
    id native=fresh("NSArray"),body=string("Square"),channel=string("fixture");
    id result=rn_local_ranges(nil,NULL,body,channel,native);
    char square[64];snprintf(square,sizeof(square),"%llu",(unsigned long long)find_word(r,"Square")->width_id);
    assert(count(result)==1 && !strcmp(text(dict(at(result,0),"id")),square));
    assert(!dict(at(result,0),"start")->number && dict(at(result,0),"end")->number==5);
    assert(!strcmp(text(body),"Square") && !count(native));
    id original=range_fixture(0,4);native->children[native->count++]=original;
    body=string("Kappa 😀 Wide (Wide)");result=rn_local_ranges(nil,NULL,body,string("#fixture"),native);
    assert(count(result)==2 && at(native,0)==original && count(native)==1);
    assert(dict(at(result,0),"start")->number==8 && dict(at(result,0),"end")->number==11);
    assert(dict(at(result,1),"start")->number==14 && dict(at(result,1),"end")->number==17);
    char alias[64];snprintf(alias,sizeof(alias),"%llu",(unsigned long long)find_word(r,"Wide")->width_id);
    assert(!strcmp(text(dict(at(result,0),"id")),alias) && !strcmp(g_last_room,"43"));
    assert(!PROBE_GET(g_rn_rewritten) && !PROBE_GET(g_rewritten_frames) && !PROBE_GET(g_room_frames));
    body=string("Square");native->children[0]=range_fixture(1,3);
    assert(!rn_local_ranges(nil,NULL,body,channel,native)); /* partial native ownership */
    native->count=0;
    assert(!rn_local_ranges(nil,NULL,body,string("other"),native));
    assert(!rn_local_ranges(nil,NULL,body,string("unknown"),native));
    assert(!rn_local_ranges(nil,NULL,body,string("fixture :Other"),native));
    assert(!rn_local_ranges(nil,NULL,string("Square\r\nPING :x"),channel,native));
    assert(!rn_local_ranges(nil,NULL,string("unknown"),channel,native));
    assert(!rn_local_ranges(nil,NULL,body,channel,fresh("NSDictionary")));
    native->count=1;native->children[0]=range_fixture(0,99);
    assert(!rn_local_ranges(nil,NULL,body,channel,native));
    native->children[0]->values[1]=string("0");assert(!rn_local_ranges(nil,NULL,body,channel,native));
    native->count=129;assert(!rn_local_ranges(nil,NULL,body,channel,native));native->count=0;
    body->byte_count=MAX_FRAME;assert(!rn_local_ranges(nil,NULL,body,channel,native));body->byte_count=0;
    g_enabled=false;assert(!rn_local_ranges(nil,NULL,body,channel,native));g_enabled=true;
    g_rn_local_ready=false;assert(!rn_local_ranges(nil,NULL,body,channel,native));g_rn_local_ready=true;
    snprintf(other->login,sizeof(other->login),"fixture");assert(!rn_local_ranges(nil,NULL,body,channel,native));
}
static bool local_registration_available,local_protocol_available;
static void composer_map(void) {
    g_enabled=true;g_rn_composer_ready=true;
    Room *r=ready("42"),*other=ready("43");snprintf(other->login,sizeof(other->login),"other");
    snprintf(g_last_room,sizeof(g_last_room),"43");
    add_emote_locked(r,MAX_ROOM,"Square","https://cdn.7tv.app/emote/square/2x.webp",0,false,NULL,1);
    add_emote_locked(r,MAX_ROOM,"Wide","https://cdn.frankerfacez.com/emote/wide/2",2,false,NULL,3);
    add_emote_locked(r,MAX_ROOM,"Kappa","https://cdn.7tv.app/emote/collision/2x.webp",0,false,NULL,1);
    add_emote_locked(&g_global,MAX_GLOBAL,"Global","https://cdn.betterttv.net/emote/global/2x",1,true,NULL,1);
    add_emote_locked(&g_global,MAX_GLOBAL,"Square","https://cdn.betterttv.net/emote/loser/2x",1,true,NULL,1);
    add_emote_locked(other,MAX_ROOM,"Foreign","https://cdn.7tv.app/emote/foreign/2x.webp",0,false,NULL,1);
    id native=fresh("NSDictionary"),kappa=string("25");native->count=1;
    native->keys[0]=string("Kappa");native->values[0]=kappa;
    id draft=string("😀 Kappa Square Square Wide Global Foreign"),channel=string("42");
    id result=rn_composer_map(nil,NULL,draft,channel,native);
    assert(result && result!=native && count(result)==4 && count(native)==1 && dict(result,"Kappa")==kappa);
    assert(!dict(result,"Foreign") && !dict(native,"Square"));
    char number[64];snprintf(number,sizeof(number),"%llu",(unsigned long long)find_word(r,"Square")->fake_id);
    assert(!strcmp(text(dict(result,"Square")),number));
    id request=fresh("NSMutableURLRequest"),url=fresh("NSURL");request->children[0]=url;
    snprintf(url->value,sizeof(url->value),"https://static-cdn.jtvnw.net/emoticons/v2/%s/static/dark/1.0",number);
    id redirected=tas_emotes_rewrite_request_copy(request);
    assert(redirected && !strcmp(redirected->children[0]->value,"https://cdn.7tv.app/emote/square/2x.webp"));
    assert(!strcmp(text(draft),"😀 Kappa Square Square Wide Global Foreign") && !strcmp(text(channel),"42"));
    assert(PROBE_GET(g_rn_composer_maps)==1 && PROBE_GET(g_rn_composer_entries)==3);
    assert(!rn_composer_map(nil,NULL,string("Kappa square PreSquare SquarePost"),channel,native));
    assert(rn_composer_map(nil,NULL,string("Square"),channel,nil));
    assert(!rn_composer_map(nil,NULL,string(""),channel,native));
    assert(!rn_composer_map(nil,NULL,draft,string("unknown"),native));
    assert(!rn_composer_map(nil,NULL,string("Wide"),string("43"),native));
    assert(!rn_composer_map(nil,NULL,draft,channel,fresh("NSArray")));
    draft->byte_count=8193;assert(!rn_composer_map(nil,NULL,draft,channel,native));draft->byte_count=0;
    draft->byte_count=strlen(text(draft))+1;assert(!rn_composer_map(nil,NULL,draft,channel,native));draft->byte_count=0;
    native->count=20001;assert(!rn_composer_map(nil,NULL,draft,channel,native));native->count=1;
    g_enabled=false;assert(!rn_composer_map(nil,NULL,draft,channel,native));g_enabled=true;
    g_rn_composer_ready=false;assert(!rn_composer_map(nil,NULL,draft,channel,native));g_rn_composer_ready=true;
    snprintf(other->login,sizeof(other->login),"42");assert(!rn_composer_map(nil,NULL,draft,channel,native));
    const TASRNMethodInfo *info=rn_composer_export(nil,NULL);
    assert(!strcmp(info->js_name,"emoteMap") && info->synchronous);
}
static void image_url_flow(void) {
    g_enabled=true;
    Room *r=ready("42");
    add_emote_locked(r,MAX_ROOM,"Square","https://cdn.7tv.app/emote/square/2x.webp",0,false,NULL,1);
    Emote *e=find_word(r,"Square");e->width_id=tas_rn_width_id(e->fake_id,1);
    expected_url_session=fresh("__NSURLSessionLocal");url_original_task=fresh("NSURLSessionDataTask");
    url_original_data=fresh("NSData");url_original_data->byte_count=16;
    url_original_response=fresh("NSURLResponse");url_original_error=nil;
    id callback_session=expected_url_session;
    id callback=(id)^(id data,id response,id error) {
        assert(expected_url_session==callback_session);
        assert(data==url_original_data && response==url_original_response && error==url_original_error);
        url_callback_calls++;
    };
    const char *sel="dataTaskWithURL:completionHandler:";
    id url=fresh("NSURL");
    snprintf(url->value,sizeof(url->value),"https://static-cdn.jtvnw.net/emoticons/v2/%llu/static/dark/3.0",(unsigned long long)e->fake_id);
    char original_text[256];snprintf(original_text,sizeof(original_text),"%s",url->value);
    url_deliver=true;
    g_public_url_completion=(IMP)original_url_completion;g_private_url_completion=(IMP)original_url_completion;
    assert(public_url_task_completion(expected_url_session,sel,url,callback)==url_original_task);
    assert(url_original_calls==1 && url_callback_calls==1 && url_original_url!=url && url_original_completion!=callback);
    assert(!strcmp(text(url),original_text) && !strcmp(text(url_original_url),e->url));
    assert(tas_emotes_is_redirected_image_url(url_original_url));
    assert(!tas_emotes_is_redirected_image_url(url));
    assert(PROBE_GET(g_url_completion_mapped)==1 && PROBE_GET(g_url_completion_results)==1);
    assert(!PROBE_GET(g_url_completion_errors) && !PROBE_GET(g_url_completion_empty));
    /* Invoke only after the hook returns, just as a network completion does. */
    url_deliver=false;
    assert(public_url_task_completion(expected_url_session,sel,url,callback)==url_original_task);
    assert(nested_block_copies==1 && url_callback_calls==1);
    ((void (^)(id,id,id))url_deferred_completion)(url_original_data,url_original_response,url_original_error);
    release_block(url_deferred_completion);url_deferred_completion=NULL;
    assert(url_callback_calls==2 && PROBE_GET(g_url_completion_results)==2);
    assert(preview_image_calls==2);
    url_deliver=true;
    /* A width alias resolves through the same registry; preserve error payload. */
    snprintf(url->value,sizeof(url->value),"https://static-cdn.jtvnw.net/emoticons/v2/%llu/default/dark/2.0",(unsigned long long)e->width_id);
    url_original_data=nil;url_original_error=fresh("NSError");
    assert(private_url_task_completion(expected_url_session,sel,url,callback)==url_original_task);
    assert(url_original_calls==3 && url_callback_calls==3 && !strcmp(text(url_original_url),e->url));
    assert(PROBE_GET(g_url_completion_errors)==1 && PROBE_GET(g_url_completion_empty)==1);
    /* Null completion remains null; do not synthesize/resume a task. */
    assert(public_url_task_completion(expected_url_session,sel,url,nil)==url_original_task);
    assert(!url_original_completion && url_original_calls==4 && url_callback_calls==3);
    const char *native[]={"https://static-cdn.jtvnw.net/emoticons/v2/25/static/dark/2.0",
        "https://static-cdn.jtvnw.net/emoticons/v2/900000000009999/static/dark/2.0",
        "https://example.com/emoticons/v2/900000000000001/static/dark/2.0",
        "https://cdn.7tv.app/emote/square/2x.webp",
        "https://usher.ttvnw.net/api/channel/hls/fixture.m3u8"};
    uint64_t mapped=PROBE_GET(g_url_completion_mapped);
    url_deliver=false;
    for(unsigned i=0;i<sizeof(native)/sizeof(native[0]);i++) {
        snprintf(url->value,sizeof(url->value),"%s",native[i]);
        assert(public_url_task_completion(expected_url_session,sel,url,callback)==url_original_task);
        assert(url_original_url==url && url_original_completion==callback);
    }
    snprintf(url->value,sizeof(url->value),"%s",original_text);g_enabled=false;
    assert(public_url_task_completion(expected_url_session,sel,url,callback)==url_original_task);
    assert(url_original_url==url && url_original_completion==callback && PROBE_GET(g_url_completion_mapped)==mapped);
    release_block(url_deferred_completion);url_deferred_completion=NULL;
}
static void image_url_installation(void) {
    g_enabled=false;install_image_url();assert(!g_public_url_completion && !g_private_url_completion && !replacements);
    g_enabled=true;public_url_owned=private_url_owned=false;install_image_url();assert(!replacements);
    public_url_owned=private_url_owned=true;public_url_method.encoding="v32@0:8@16@24";
    private_url_method.encoding="@24@0:8@16";install_image_url();assert(!replacements);
    public_url_method.encoding="@32@0:8@16@?24";install_image_url();assert(replacements==1 && g_public_url_completion==(IMP)original_url_completion && !g_private_url_completion);
    private_url_method.encoding="@32@0:8@16@24";install_image_url();assert(replacements==2 && g_private_url_completion==(IMP)original_url_completion);
    assert(public_url_method.imp==(IMP)public_url_task_completion && private_url_method.imp==(IMP)private_url_task_completion);
    install_image_url();assert(replacements==2);
}
static unsigned local_allocations,local_disposals,local_registrations,local_exports;
static Class local_allocated_class,local_meta;
static void register_local_fixture(Class cls) { assert(cls==local_registered_class);local_exports++; }
void *dlsym(void *handle,const char *name) {
    (void)handle;
    if(!strcmp(name,"RCTRegisterModule") && local_registration_available)return (void *)register_local_fixture;
    return NULL;
}
void *objc_getProtocol(const char *name) { assert(!strcmp(name,"RCTBridgeModule"));return local_protocol_available ? (void *)1 : NULL; }
BOOL class_addProtocol(Class cls,void *protocol) { assert(cls==local_allocated_class && protocol==(void *)1);return YES; }
Class objc_allocateClassPair(Class parent,const char *name,size_t size) {
    assert(parent==objc_getClass("NSObject") && !strcmp(name,"TASRNLocalEchoModule") && !size);
    local_allocations++;local_allocated_class=fresh(name);local_meta=fresh("metaclass");return local_allocated_class;
}
void objc_disposeClassPair(Class cls) { assert(cls==local_allocated_class);local_disposals++; }
Class object_getClass(id object) { assert(object==local_allocated_class);return local_meta; }
BOOL class_addMethod(Class cls,SEL selector,IMP imp,const char *encoding) {
    if(!strcmp(selector,"renderLocalBody:channel:nativeRanges:"))assert(cls==local_allocated_class && imp==(IMP)rn_local_ranges && !strcmp(encoding,"@40@0:8@16@24@32"));
    else if(!strcmp(selector,"previewMap:channel:nativeMap:"))assert(cls==local_allocated_class && imp==(IMP)rn_composer_map && !strcmp(encoding,"@40@0:8@16@24@32"));
    else if(!strcmp(selector,"providerMetadata:"))assert(cls==local_allocated_class && imp==(IMP)rn_popup_metadata && !strcmp(encoding,"@24@0:8@16"));
    else if(!strcmp(selector,"providerAction:action:"))assert(cls==local_allocated_class && imp==(IMP)rn_popup_action && !strcmp(encoding,"v32@0:8@16@24"));
    else if(!strcmp(selector,"pickerState"))assert(cls==local_allocated_class && imp==(IMP)rn_strip_state && !strcmp(encoding,"@16@0:8"));
    else if(!strcmp(selector,"pickerSearch:query:"))assert(cls==local_allocated_class && imp==(IMP)rn_strip_search && !strcmp(encoding,"@32@0:8@16@24"));
    else if(!strcmp(selector,"librarySnapshot:"))assert(cls==local_allocated_class && imp==(IMP)rn_library_snapshot && !strcmp(encoding,"@24@0:8@16"));
    else if(!strcmp(selector,"libraryLookup:name:"))assert(cls==local_allocated_class && imp==(IMP)rn_library_lookup && !strcmp(encoding,"@32@0:8@16@24"));
    else if(!strcmp(selector,"libraryRemember:name:identifier:"))assert(cls==local_allocated_class && imp==(IMP)rn_library_remember && !strcmp(encoding,"@40@0:8@16@24@32"));
    else {
        assert(cls==local_meta);
        if(!strcmp(selector,"moduleName"))assert(imp==(IMP)rn_local_module_name && !strcmp(encoding,"@16@0:8"));
        else if(!strcmp(selector,"requiresMainQueueSetup"))assert(imp==(IMP)rn_local_main_queue && !strcmp(encoding,"B16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsideComposer"))assert(imp==(IMP)rn_composer_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsideInfo"))assert(imp==(IMP)rn_popup_metadata_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsideInfoAction"))assert(imp==(IMP)rn_popup_action_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsidePickerState"))assert(imp==(IMP)rn_strip_state_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsidePickerSearch"))assert(imp==(IMP)rn_strip_search_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsideLibrarySnapshot"))assert(imp==(IMP)rn_library_snapshot_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsideLibraryLookup"))assert(imp==(IMP)rn_library_lookup_export && !strcmp(encoding,"^v16@0:8"));
        else if(!strcmp(selector,"__rct_export__streamsideLibraryRemember"))assert(imp==(IMP)rn_library_remember_export && !strcmp(encoding,"^v16@0:8"));
        else assert(!strcmp(selector,"__rct_export__streamsideLocalEcho") && imp==(IMP)rn_local_export && !strcmp(encoding,"^v16@0:8"));
    }
    return YES;
}
void objc_registerClassPair(Class cls) { assert(cls==local_allocated_class);local_registered_class=cls;local_registrations++; }
static void local_registration(void) {
    g_enabled=true;install_rn_local();assert(!local_allocations && !g_rn_local_registered);
    local_registration_available=true;install_rn_local();assert(!local_allocations && !g_rn_local_registered);
    local_protocol_available=true;g_enabled=false;install_rn_local();assert(!local_allocations);
    g_enabled=true;install_rn_local();assert(g_rn_local_registered && local_allocations==1 && local_registrations==1 && local_exports==1 && !local_disposals);
    install_rn_local();assert(local_allocations==1 && local_exports==1);
    const TASRNMethodInfo *info=rn_popup_metadata_export(nil,NULL);
    assert(info->synchronous && !strcmp(info->js_name,"getMetadata") && !strcmp(info->objc_name,"providerMetadata:(id)identifier"));
    info=rn_popup_action_export(nil,NULL);
    assert(!info->synchronous && !strcmp(info->js_name,"sendAction") && !strcmp(info->objc_name,"providerAction:(id)identifier action:(NSNumber *)action"));
    info=rn_strip_state_export(nil,NULL);assert(info->synchronous && !strcmp(info->js_name,"getState") && !strcmp(info->objc_name,"pickerState"));
    info=rn_strip_search_export(nil,NULL);assert(info->synchronous && !strcmp(info->js_name,"search") && !strcmp(info->objc_name,"pickerSearch:(NSString *)channel query:(NSString *)query"));
    info=rn_library_snapshot_export(nil,NULL);assert(info->synchronous && !strcmp(info->js_name,"getSnapshot") && !strcmp(info->objc_name,"librarySnapshot:(NSString *)channel"));
    info=rn_library_remember_export(nil,NULL);assert(info->synchronous && !strcmp(info->js_name,"remember"));
    info=rn_library_lookup_export(nil,NULL);assert(info->synchronous && !strcmp(info->js_name,"lookup") && !strcmp(info->objc_name,"libraryLookup:(NSString *)channel name:(NSString *)name"));
}
static void popup_metadata(void) {
    g_enabled=true;Room *room=ready("42");
    add_emote_locked(room,MAX_ROOM,"Wide","https://cdn.7tv.app/emote/wide/2x.gif",0,false,"creator",3);
    Emote *e=find_word(room,"Wide");e->width_id=860000000000123ULL;
    char number[32];snprintf(number,sizeof(number),"%llu",(unsigned long long)e->fake_id);
    assert(!rn_popup_metadata(nil,NULL,string(number))); /* admitted source required */
    g_rn_popup_ready=true;id value=rn_popup_metadata(nil,NULL,string(number));
    assert(value && !strcmp(text(dict(value,"name")),"Wide"));
    assert(!strcmp(text(dict(value,"subtitle")),"7TV channel emote\nby creator"));
    assert(!strcmp(text(dict(value,"title")),"Copy name") && !strcmp(text(dict(value,"openURL")),"Open in browser"));
    assert(dict(value,"id")->number==e->fake_id);
    id alias=rn_popup_metadata(nil,NULL,string("860000000000123"));assert(alias && dict(alias,"id")->number==e->fake_id);
    assert(rn_popup_metadata(nil,NULL,dict(value,"id")));
    const char *bad[]={"25","opaque-native","-900000000000123","+900000000000123","900000000000123x","99999999999999999"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++)assert(!rn_popup_metadata(nil,NULL,string(bad[i])));
    assert(!rn_popup_metadata(nil,NULL,fresh("NSArray")));
    /* Action capability refusal must be harmless, with no UI side effect. */
    rn_popup_action(nil,NULL,dict(value,"id"),dict(value,"provider"));assert(PROBE_GET(g_rn_popup_refused)==1);
    reset_room_locked(room,true,time(NULL));
    assert(rn_popup_metadata(nil,NULL,string(number))); /* retired visible message */
    assert(!strcmp(text(dict(value,"name")),"Wide")); /* owned snapshot */
    g_enabled=false;assert(!rn_popup_metadata(nil,NULL,string(number)));
}
static void strip_search(void) {
    g_enabled=true;Room *room=ready("42");
    add_emote_locked(room,MAX_ROOM,"Wide","https://cdn.7tv.app/emote/wide/2x.gif",0,false,NULL,3);
    add_emote_locked(&g_global,MAX_GLOBAL,"Global","https://cdn.betterttv.net/emote/global/2x",1,true,NULL,1);
    assert(!dict(rn_strip_state(nil,NULL),"enabled")->number);
    assert(!rn_strip_search(nil,NULL,string("42"),string("Wi")));
    g_rn_strip_ready=true;
    for(int mode=0;mode<3;mode++) {
        picker_mode=mode;id config=rn_strip_state(nil,NULL);
        assert(count(config)==3 && dict(config,"enabled")->number==1 && dict(config,"mode")->number==(uint64_t)mode);
        assert(dict(config,"revision")->number==tas_emotes_catalog_revision());
        id items=rn_strip_search(nil,NULL,string("42"),string("Wi"));
        if(mode==2)assert(!items);else assert(items && count(items)==1 && !strcmp(text(dict(at(items,0),"name")),"Wide"));
    }
    picker_mode=0;id items=rn_strip_search(nil,NULL,string("42"),string(""));assert(count(items)==2);
    assert(!rn_strip_search(nil,NULL,string("other"),string(""))); /* no last-room/global-only fallback */
    assert(!rn_strip_search(nil,NULL,fresh("NSNumber"),string("Wi")));
    assert(!rn_strip_search(nil,NULL,string("42"),fresh("NSArray")));
    char large[98];memset(large,'x',97);large[97]=0;assert(!rn_strip_search(nil,NULL,string("42"),string(large)));
    id embedded=string("Wi");embedded->byte_count=3;assert(!rn_strip_search(nil,NULL,string("42"),embedded));
    assert(PROBE_GET(g_rn_strip_refused)==5);
    g_enabled=false;assert(!dict(rn_strip_state(nil,NULL),"enabled")->number);
    assert(!rn_strip_search(nil,NULL,string("42"),string("Wi")));
}
static void library_flow(void) {
    g_enabled=true;Room *room=ready("42");id channel=string("42");
    add_emote_locked(room,MAX_ROOM,"Wide","https://cdn.7tv.app/emote/wide/2x.gif",0,false,NULL,3);
    add_emote_locked(&g_global,MAX_GLOBAL,"Global","https://cdn.betterttv.net/emote/global/2x",1,true,NULL,1);
    assert(!rn_library_snapshot(nil,NULL,channel));assert(!rn_library_lookup(nil,NULL,channel,string("Wide")));g_rn_strip_ready=true;
    for(int mode=0;mode<3;mode++) {
        picker_mode=mode;id value=rn_library_snapshot(nil,NULL,channel);
        assert(count(dict(value,"sections"))==2 && count(at(dict(value,"sections"),0))==1 && count(at(dict(value,"sections"),1))==1);
        assert(count(dict(value,"recents"))==0 && count(dict(value,"labels"))==6);
        assert(rn_library_lookup(nil,NULL,channel,string("Wide")));
        assert(rn_library_lookup(nil,NULL,channel,string("Global")));
        assert(!rn_library_lookup(nil,NULL,channel,string("wide")));
        assert(!rn_library_lookup(nil,NULL,channel,string("Wide extra")));
    }
    id wide=tas_emotes_named_copy(channel,string("Wide")),global=tas_emotes_named_copy(channel,string("Global"));
    assert(!rn_library_remember(nil,NULL,channel,string("Wide"),dict(global,"id")));
    assert(rn_library_remember(nil,NULL,channel,string("Wide"),dict(wide,"id")));
    id before=rn_library_snapshot(nil,NULL,channel);
    assert(count(dict(before,"recents"))==1);
    assert(rn_library_remember(nil,NULL,channel,string("Global"),dict(global,"id")));
    id after=rn_library_snapshot(nil,NULL,channel);assert(count(dict(after,"recents"))==2);
    assert(!strcmp(text(dict(at(dict(after,"recents"),0),"name")),"Global"));
    assert(count(dict(before,"recents"))==1); /* snapshot graph remains owned */
    assert(rn_library_remember(nil,NULL,channel,string("Wide"),dict(wide,"id")));
    after=rn_library_snapshot(nil,NULL,channel);assert(count(dict(after,"recents"))==2);
    assert(!strcmp(text(dict(at(dict(after,"recents"),0),"name")),"Wide"));
    assert(!rn_library_snapshot(nil,NULL,string("other")));
    assert(!rn_library_lookup(nil,NULL,string("other"),string("Global")));
    assert(!rn_library_remember(nil,NULL,string("other"),string("Global"),dict(global,"id")));
    assert(!rn_library_remember(nil,NULL,channel,string("unknown"),dict(wide,"id")));
    /* Manually typed provider codes use the completed own-message display path. */
    g_rn_local_ready=true;id native=call0((id)objc_getClass("NSMutableArray"),"new");
    assert(rn_local_ranges(nil,NULL,string("Global"),string("fixture"),native));
    after=rn_library_snapshot(nil,NULL,channel);
    assert(!strcmp(text(dict(at(dict(after,"recents"),0),"name")),"Global"));
    Room *other=ready("43");assert(!rn_library_snapshot(nil,NULL,string("fixture"))); /* ambiguous login */
    assert(!rn_library_lookup(nil,NULL,string("fixture"),string("Global")));
    reset_room_locked(other,true,time(NULL));reset_room_locked(room,true,time(NULL));
    assert(!rn_library_remember(nil,NULL,channel,string("Wide"),dict(wide,"id"))); /* retired identity */
    g_enabled=false;assert(!rn_library_snapshot(nil,NULL,channel));
    assert(!rn_library_lookup(nil,NULL,channel,string("Global")));
    assert(!rn_library_remember(nil,NULL,channel,string("Global"),dict(global,"id")));
}
int main(int argc,char **argv) {
    assert(argc==2);if(!strcmp(argv[1],"flow"))flow();else if(!strcmp(argv[1],"widths"))widths();
    else if(!strcmp(argv[1],"source"))source_hook();else if(!strcmp(argv[1],"local"))local_echo();
    else if(!strcmp(argv[1],"array"))local_array();else if(!strcmp(argv[1],"composer"))composer_map();
    else if(!strcmp(argv[1],"url"))image_url_flow();else if(!strcmp(argv[1],"url-install"))image_url_installation();
    else if(!strcmp(argv[1],"registration"))local_registration();else if(!strcmp(argv[1],"popup"))popup_metadata();
    else if(!strcmp(argv[1],"strip"))strip_search();else if(!strcmp(argv[1],"library"))library_flow();else installation();return 0;
}
'''
HARNESS = ROUTE[:ROUTE.index('int main(void)')].replace(ROUTE_ASSOCIATED, '')
HARNESS = HARNESS.replace('uint64_t number;', 'uint64_t number;size_t byte_count;const char *payload;')
HARNESS = HARNESS.replace('snprintf(o->value,sizeof(o->value),"%s",value);return o;',
    'if(strlen(value)>=sizeof(o->value))o->payload=strdup(value);else snprintf(o->value,sizeof(o->value),"%s",value);return o;')
HARNESS = HARNESS.replace('(!strcmp(c->cls,"NSDictionary") && !strcmp(o->cls,"NSMutableDictionary"))', '( (!strcmp(c->cls,"NSDictionary") && !strcmp(o->cls,"NSMutableDictionary")) || (!strcmp(c->cls,"NSArray") && !strcmp(o->cls,"NSMutableArray")) )')
HARNESS = HARNESS.replace('classes[8]', 'classes[32]').replace('class_count<8', 'class_count<32')
HARNESS = HARNESS.replace('keys[8],values[8]', 'keys[16],values[16]').replace('o->count<8','o->count<16')
HARNESS = HARNESS.replace('children[32]', 'children[64]').replace('o->count<32','o->count<64')
HARNESS = HARNESS.replace('Class objc_getClass(const char *name) {',
    'static Class local_registered_class;\nClass objc_getClass(const char *name) {\nif(!strcmp(name,"TASRNLocalEchoModule"))return local_registered_class;')
HARNESS = HARNESS.replace('SEL sel_registerName(const char *name) { return name; }', r'''
SEL sel_registerName(const char *name) {
    static char names[128][96];static unsigned n;
    for(unsigned i=0;i<n;i++)if(!strcmp(names[i],name))return names[i];
    assert(n<128);snprintf(names[n],96,"%s",name);return names[n++];
}''')
HARNESS = HARNESS.replace('result=(id)o->value;', 'result=(id)(o->payload ? o->payload : o->value);')
HARNESS = HARNESS.replace("const char *end=strchr(p,'/');assert(end);", "const char *end=strpbrk(p,\":/\");if(!end)end=p+strlen(p);")
HARNESS = HARNESS.replace('else assert(!"unexpected provider route selector");', EXTRA+'else assert(!"unexpected RN selector");') + MAIN


class RNIncomingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        root = Path(cls.folder.name)
        (root / "objc").mkdir()
        declarations = RUNTIME + '\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n'
        for name in ("runtime.h", "objc.h", "message.h"):
            (root / "objc" / name).write_text(declarations)
        source = root / "incoming.c"
        source.write_text(HARNESS)
        cls.binary = root / "incoming"
        zig = os.environ.get("ZIG") or shutil.which("zig")
        if not zig:
            raise AssertionError("Zig required for production RN receive harness")
        built = subprocess.run([zig, "cc", "-fblocks", "-Wall", "-Wextra", "-Werror",
            "-Wno-cast-function-type-mismatch", "-ffunction-sections", "-fdata-sections",
            "-fsanitize=address,undefined", "-I", str(root), "-I", str(ROOT / "src"),
            str(source), "-Wl,--gc-sections", "-pthread", "-o", str(cls.binary)], capture_output=True, text=True)
        if built.returncode:
            raise AssertionError(built.stderr)

    def test_local_display_array_static_unicode_native_overlap_and_scope(self):
        result=subprocess.run([self.binary,'array'],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
        self.assertEqual(result.returncode,0,result.stderr)

    def test_composer_preview_map_draft_native_identity_provider_precedence_scope_and_bounds(self):
        self.run_harness("composer")

    def test_library_snapshots_recents_identity_room_admission_and_inline_off(self):
        self.run_harness("library")

    def test_native_composer_url_transport_mapping_callbacks_errors_and_fallback(self):
        self.run_harness("url")

    def test_url_transport_owned_methods_exact_abi_disabled_and_retry(self):
        self.run_harness("url-install")

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def run_harness(self, mode):
        result = subprocess.run([self.binary, mode], capture_output=True, text=True,
            env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_incoming_identity_metadata_unicode_room_scope_and_redirect(self):
        self.run_harness("flow")

    def test_hook_abi_ownership_and_retry_idempotence(self):
        self.run_harness("install")

    def test_width_aliases_redirect_freeze_fallback_collisions_and_history(self):
        self.run_harness("widths")

    def test_source_hook_abi_disabled_refusal_identity_and_source_owned_cache(self):
        self.run_harness("source")

    def test_local_preview_room_native_ranges_unicode_metadata_redirect_and_refusals(self):
        self.run_harness("local")

    def test_local_module_registration_availability_exports_disabled_and_idempotence(self):
        self.run_harness("registration")

    def test_provider_info_admission_exact_identity_alias_history_and_snapshot(self):
        self.run_harness("popup")

    def test_horizontal_picker_bridge_modes_scope_bounds_and_metadata(self):
        self.run_harness("strip")
