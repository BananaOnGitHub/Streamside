"""Exercise the production definition hook with native identity and scope guards.

A fake ObjC runtime cannot run Twitch's Swift renderer; donor disassembly and
separate production TextKit/layer tests cover those boundaries statically.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_emote_ui import RUNTIME

ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include "TASEmotePresentation.c"
struct Fake {
    const char *cls; char value[128]; uint64_t number;
    id items[128],inner,identifier,code,manager; size_t n;
    uint32_t channel,user; unsigned char absent,next;
    BOOL historical,foreign,regex; I asset;
};
static struct Fake pool[30000],classes[32];static size_t used,nclasses;
static BOOL enabled=YES,bad_encoding,bad_layout,changed_identity,changed_code;
static id native_result,follower_result;static unsigned native_calls,provider_reads;
static id fresh(const char *cls) { assert(used<30000);id o=&pool[used++];o->cls=cls;return o; }
static id text(const char *s) { id o=fresh("NSString");snprintf(o->value,sizeof(o->value),"%s",s);return o; }
static id list(void) { return fresh("NSArray"); }
static void push(id a,id b) { assert(a->n<128);a->items[a->n++]=b; }
Class objc_getClass(const char *s) {
    for(size_t i=0;i<nclasses;i++)if(!strcmp(classes[i].cls,s))return &classes[i];
    assert(nclasses<32);classes[nclasses].cls=s;return &classes[nclasses++];
}
Class object_getClass(id o) { return o ? objc_getClass(o->cls) : nil; }
SEL sel_registerName(const char *s) { return s; }
bool tas_emotes_enabled_this_launch(void) { return enabled; }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_storeWeak(id *slot,id o) { *slot=o;return o; }
id objc_loadWeakRetained(id *slot) { return *slot; }
size_t class_getInstanceSize(Class c) { (void)c;return sizeof(struct Fake); }
Ivar class_getInstanceVariable(Class c,const char *s) {
    static ptrdiff_t offsets[8];
    if(!strcmp(c->cls,DATA_SOURCE)) {
        if(!strcmp(s,"channelID")) { offsets[0]=offsetof(struct Fake,channel)+(bad_layout ? 1 : 0);return &offsets[0]; }
        if(!strcmp(s,"emoteManager")) { offsets[1]=offsetof(struct Fake,channel)+8;return &offsets[1]; }
        if(!strcmp(s,"currentTheme")) { offsets[2]=offsetof(struct Fake,channel)+16;return &offsets[2]; }
    } else if(!strcmp(c->cls,TRANSCRIPT)) {
        if(!strcmp(s,"channelID")) { offsets[0]=offsetof(struct Fake,channel);return &offsets[0]; }
        if(!strcmp(s,"allowOpenURLHandling")) { offsets[1]=offsetof(struct Fake,channel)+5;return &offsets[1]; }
    } else if(!strcmp(c->cls,MANAGER)) {
        if(!strcmp(s,"currentUserID")) { offsets[3]=offsetof(struct Fake,user);return &offsets[3]; }
        if(!strcmp(s,"recommendedEmotes")) { offsets[4]=offsetof(struct Fake,user)+8;return &offsets[4]; }
    }
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return *(ptrdiff_t *)iv; }
static const char *method_name;
Method class_getInstanceMethod(Class c,SEL sel) { if(!c)return NULL;method_name=sel;return (Method)sel; }
const char *method_getTypeEncoding(Method m) {
    (void)m;if(bad_encoding)return "@32@0:8@16q24";
    if(!strcmp(method_name,CONSTRUCTOR))return "@48@0:8@16@24@32q40";
    if(!strcmp(method_name,"assetType"))return "q16@0:8";
    if(!strcmp(method_name,"isRegex"))return "B16@0:8";
    return "@16@0:8";
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list ap;va_start(ap,sel);id r=nil;
    if(!strcmp(sel,"isKindOfClass:")) {
        Class c=va_arg(ap,Class);BOOL same=!strcmp(o->cls,c->cls);
        if(!strcmp(c->cls,"NSArray") && !strcmp(o->cls,"NSMutableArray"))same=YES;
        if(!strcmp(c->cls,TEXT_TOKEN) && strstr(o->cls,"TextToken"))same=YES;
        r=(id)(uintptr_t)same;
    } else if(!strcmp(sel,"respondsToSelector:")) {
        const char *s=va_arg(ap,SEL);BOOL has=NO;
        if(!strcmp(o->cls,PRESENTATION))has=!strcmp(s,"chatMessage");
        else if(!strcmp(o->cls,MESSAGE))has=!strcmp(s,"senderId") || !strcmp(s,"messageTokens") || !strcmp(s,"isHistoricalMessage") || !strcmp(s,"isFromOtherChannelInSharedChat");
        else if(strstr(o->cls,"TextToken"))has=!strcmp(s,"text");
        else if(!strcmp(o->cls,"NativeEmote"))has=!strcmp(s,"emoteText");
        r=(id)(uintptr_t)has;
    } else if(!strcmp(sel,"chatMessage") || !strcmp(sel,"messageTokens") || !strcmp(sel,"text") || !strcmp(sel,"emoteText"))r=o->inner;
    else if(!strcmp(sel,"senderId")) { r=fresh("NSNumber");r->number=o->user; }
    else if(!strcmp(sel,"longLongValue") || !strcmp(sel,"unsignedLongLongValue"))r=(id)(uintptr_t)o->number;
    else if(!strcmp(sel,"isHistoricalMessage"))r=(id)(uintptr_t)o->historical;
    else if(!strcmp(sel,"isFromOtherChannelInSharedChat"))r=(id)(uintptr_t)o->foreign;
    else if(!strcmp(sel,"stringWithUTF8String:"))r=text(va_arg(ap,const char *));
    else if(!strcmp(sel,"isEqual:")) { id b=va_arg(ap,id);r=(id)(uintptr_t)(b && !strcmp(o->value,b->value)); }
    else if(!strcmp(sel,"identifier"))r=o->identifier;
    else if(!strcmp(sel,"code"))r=o->code;
    else if(!strcmp(sel,"isRegex"))r=(id)(uintptr_t)o->regex;
    else if(!strcmp(sel,"assetType"))r=(id)(uintptr_t)o->asset;
    else if(!strcmp(sel,"length"))r=(id)(uintptr_t)strlen(o->value);
    else if(!strcmp(sel,"set") || !strcmp(sel,"array"))r=fresh(!strcmp(sel,"set") ? "NSMutableSet" : "NSArray");
    else if(!strcmp(sel,"alloc"))r=fresh(o->cls);
    else if(!strcmp(sel,CONSTRUCTOR)) {
        o->identifier=va_arg(ap,id);o->code=va_arg(ap,id);(void)va_arg(ap,id);o->asset=va_arg(ap,I);
        if(changed_identity)o->identifier=text("25");if(changed_code)o->code=text("DifferentName");r=o;
    } else if(!strcmp(sel,"count"))r=(id)(uintptr_t)o->n;
    else if(!strcmp(sel,"objectAtIndex:")) { U i=va_arg(ap,U);assert(i<o->n);r=o->items[i]; }
    else if(!strcmp(sel,"addObject:"))push(o,va_arg(ap,id));
    else if(!strcmp(sel,"containsObject:")) { id v=va_arg(ap,id);for(U i=0;i<o->n;i++)if(!strcmp(o->items[i]->value,v->value))r=(id)1; }
    else if(!strcmp(sel,"mutableCopy")) { r=fresh("NSMutableArray");memcpy(r->items,o->items,sizeof(o->items));r->n=o->n; }
    else if(!strcmp(sel,"autorelease"))r=o;
    else if(!strcmp(sel,"componentsSeparatedByString:")) {
        id delimiter=va_arg(ap,id);assert(!strcmp(delimiter->value," "));r=list();
        const char *p=o->value;while(1) { const char *end=strchr(p,' ');size_t n=end ? (size_t)(end-p) : strlen(p);id word=text("");assert(n<sizeof(word->value));memcpy(word->value,p,n);push(r,word);if(!end)break;p=end+1; }
    } else if(!strcmp(sel,"objectForKey:")) { id k=va_arg(ap,id);assert(!strcmp(k->value,"id"));r=o->inner; }
    else if(!strcmp(sel,"description")) { char s[32];snprintf(s,sizeof(s),"%llu",(unsigned long long)o->number);r=text(s); }
    else assert(!"Unexpected selector; originals must remain unmodified");
    va_end(ap);return r;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static const char *names[]={"Square","Wide","Animated","AnimatedWide"};
static const uint64_t ids[]={9000000001ULL,9000000002ULL,9000000003ULL,9000000004ULL};
id tas_emotes_named_copy(id room,id name) {
    assert(!strcmp(room->value,"42"));provider_reads++;
    for(unsigned i=0;i<4;i++)if(!strcmp(name->value,names[i])) {
        id o=fresh("NSDictionary"),v=fresh("NSNumber");v->number=ids[i];o->inner=v;return o;
    }
    return nil;
}
static id native_sub(id self,SEL sel,id p) { (void)self;(void)sel;(void)p;native_calls++;return native_result; }
static id native_follow(id self,SEL sel,id p) { (void)self;(void)sel;(void)p;return follower_result; }
static id token(const char *s) { id t=fresh(TEXT_TOKEN);t->inner=text(s);return t; }
static id native_def(const char *s) { id d=fresh(DEFINITION);d->code=text(s);d->identifier=text("25");return d; }
int main(void) {
    originals[0]=(IMP)native_sub;originals[1]=(IMP)native_sub;followers[0]=(IMP)native_follow;followers[1]=(IMP)native_follow;
    id manager=fresh(MANAGER),source=fresh(DATA_SOURCE),view=fresh(TRANSCRIPT),message=fresh(MESSAGE),p=fresh(PRESENTATION);
    manager->user=7;source->channel=42;view->channel=42;message->user=7;p->inner=message;
    /* The two production fields have independent named storage; write the
     * object pointer into the verified fake emoteManager slot. */
    memcpy((char *)source+offsetof(struct Fake,channel)+8,&manager,sizeof(manager));
    native_result=list();follower_result=list();id native=native_def("Kappa");push(native_result,native);
    id tokens=list();message->inner=tokens;id plain=token("Square Wide Animated AnimatedWide Wide");push(tokens,plain);
    struct Fake saved_message=*message,saved_tokens=*tokens,saved_plain=*plain;
    id output=data_subscriber(source,SUBSCRIBER,p);
    assert(output!=native_result && output->n==5 && output->items[0]==native);
    for(unsigned i=0;i<4;i++) { id d=output->items[i+1];char num[32];snprintf(num,sizeof(num),"%llu",(unsigned long long)ids[i]);assert(!strcmp(d->identifier->value,num) && !strcmp(d->code->value,names[i]) && d->asset==1); }
    assert(!memcmp(message,&saved_message,sizeof(*message)) && !memcmp(tokens,&saved_tokens,sizeof(*tokens)) && !memcmp(plain,&saved_plain,sizeof(*plain)));
    assert(native_result->n==1 && native_result->items[0]==native && native_calls==1);
    /* Rebuilding yields a fresh definition contribution, no duplicates/state. */
    output=data_subscriber(source,SUBSCRIBER,p);assert(output->n==5 && native_result->n==1);
    assert(transcript_subscriber(view,SUBSCRIBER,p)->n==5); /* live observed manager */
    message->user=8;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);message->user=7;
    manager->absent=1;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);manager->absent=0;
    manager->user=8;assert(transcript_subscriber(view,SUBSCRIBER,p)==native_result);manager->user=7;
    view->user=1; /* optional channel nil discriminator at channel+4 */
    assert(transcript_subscriber(view,SUBSCRIBER,p)==native_result);view->user=0;
    bad_layout=YES;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);bad_layout=NO;
    bad_encoding=YES;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);bad_encoding=NO;
    message->historical=YES;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);message->historical=NO;
    message->foreign=YES;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);message->foreign=NO;
    enabled=NO;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);enabled=YES;
    changed_identity=YES;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);changed_identity=NO;
    changed_code=YES;assert(data_subscriber(source,SUBSCRIBER,p)==native_result);changed_code=NO;
    /* Preserve native follower definitions and tokenized-native name conflicts. */
    push(follower_result,native_def("Wide"));id native_token=fresh("NativeEmote");native_token->inner=text("AnimatedWide");push(tokens,native_token);
    output=data_subscriber(source,SUBSCRIBER,p);assert(output->n==3);assert(!strcmp(output->items[1]->code->value,"Square") && !strcmp(output->items[2]->code->value,"Animated"));
    tokens->n=1;follower_result->n=0;
    id unsafe=token("hidden Wide");unsafe->cls="_TtC9TwitchKit25TWMessageAutoModTextToken";push(tokens,unsafe);
    assert(data_subscriber(source,SUBSCRIBER,p)==native_result);
    unsafe->cls="_TtC9TwitchKit26TWMessageCensoredTextToken";assert(data_subscriber(source,SUBSCRIBER,p)==native_result);tokens->n=1;
    plain->inner=text("Wide! Wide\tSquare Wide\nSquare wide Wide");output=data_subscriber(source,SUBSCRIBER,p);assert(output->n==2 && !strcmp(output->items[1]->code->value,"Wide"));
    /* No guessed/stale account binding for transcript-only presentation. */
    weak_manager=nil;assert(transcript_subscriber(view,SUBSCRIBER,p)==native_result);
    observe_manager(manager);id other=fresh(MANAGER);other->user=7;observe_manager(other);assert(transcript_subscriber(view,SUBSCRIBER,p)==native_result);
    assert(definitions>=4 && identity_failures>0 && unsafe_messages>=2 && scope_misses>0 && provider_reads>0);
    return 0;
}
'''

class EmotePresentationTests(unittest.TestCase):
    def test_native_definitions_identity_scope_and_original_message_preservation(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"objc").mkdir()
            (root/"objc/runtime.h").write_text(RUNTIME+"\nsize_t class_getInstanceSize(Class);\n")
            (root/"objc/objc.h").write_text('#include "runtime.h"\n')
            (root/"objc/message.h").write_text('#include "runtime.h"\n')
            harness=root/"presentation.c";binary=root/"presentation";harness.write_text(HARNESS)
            result=subprocess.run([zig,"cc","-std=gnu11","-Wall","-Wextra","-Werror","-Wno-cast-function-type-mismatch",
                "-ffunction-sections","-fdata-sections","-fsanitize=address,undefined","-I",str(root),"-I",str(ROOT/"src"),str(harness),"-Wl,--gc-sections","-lpthread","-o",str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([binary],capture_output=True,text=True,env={**os.environ,"ASAN_OPTIONS":"detect_leaks=0"})
            self.assertEqual(result.returncode,0,result.stderr)
