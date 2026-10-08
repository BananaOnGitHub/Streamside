"""Production RN attachment geometry and preview clock with a small ObjC host."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_emote_ui import RUNTIME

ROOT=Path(__file__).resolve().parent.parent
HARNESS=r'''
#include <stdarg.h>
#include <assert.h>
#include <objc/runtime.h>
static double test_double(id,const char *);
#include "composer.c"
void *_NSConcreteStackBlock[32];
struct Fake {
    const char *cls;uint64_t url[2];unsigned char loaded;
    id editor,next,identity,target,value,window,parent,marked,image,items[8];
    unsigned char bytes[2048];uint16_t units[8];U length,count,index;
    double seconds,alpha;BOOL hidden,invalidated;int releases;
    void *context;
};
static struct Fake classes[32];static unsigned classes_count;
static id pool[512];static unsigned pool_count;
static BOOL enabled=YES,is_main=YES,known=YES,bridge_available=YES;
static double aspect=3;
static unsigned copies,invalidations,assignments,originals,deallocs,bridge_calls;
static ptrdiff_t url_gap=16;
static struct Fake app={.cls="UIApplication"},mainqueue={.cls="NSOperationQueue"},runloop={.cls="NSRunLoop"},metadata={.cls="NSDictionary"};
static id cache_data,clock_link;
static id fresh(const char *cls){id o=calloc(1,sizeof(*o));assert(pool_count<512);pool[pool_count++]=o;o->cls=cls;o->alpha=1;return o;}
static id text(const char *s){id o=fresh("NSString");o->value=(id)s;return o;}
Class objc_getClass(const char *s){for(unsigned i=0;i<classes_count;i++)if(!strcmp(classes[i].cls,s))return &classes[i];assert(classes_count<32);classes[classes_count].cls=s;return &classes[classes_count++];}
Class object_getClass(id o){return o;}
SEL sel_registerName(const char *s){return s;}
Ivar class_getInstanceVariable(Class cls,const char *s){(void)cls;if(!strcmp(s,"url"))return (Ivar)(uintptr_t)offsetof(struct Fake,url);if(!strcmp(s,"loaded"))return (Ivar)(uintptr_t)(offsetof(struct Fake,url)+url_gap);if(!strcmp(s,"textView"))return (Ivar)(uintptr_t)offsetof(struct Fake,editor);if(!strcmp(s,"emoteMapDict"))return (Ivar)(uintptr_t)offsetof(struct Fake,next);if(!strcmp(s,"_state"))return (Ivar)(uintptr_t)offsetof(struct Fake,context);return NULL;}
ptrdiff_t ivar_getOffset(Ivar v){return (ptrdiff_t)(uintptr_t)v;}
size_t class_getInstanceSize(Class cls){(void)cls;return sizeof(struct Fake);}
id objc_retain(id o){return o;}
void objc_release(id o){if(o)o->releases++;}
id objc_initWeak(id *p,id o){*p=o;return o;}
id objc_loadWeakRetained(id *p){return *p;}
void objc_destroyWeak(id *p){*p=nil;}
id objc_getAssociatedObject(id o,const void *key){return !o ? nil : key==&identity_key ? o->identity : o->target;}
void objc_setAssociatedObject(id o,const void *key,id value,uintptr_t policy){assert(policy==1);if(key==&identity_key)o->identity=value;else {assert(key==&state_key);o->target=value;}}
bool tas_emotes_enabled_this_launch(void){return enabled;}
id tas_emotes_metadata_copy(uint64_t n){return known && n==900000000000001ULL ? &metadata : nil;}
double tas_emotes_aspect(uint64_t n){return n==900000000000001ULL ? aspect : 0;}
static id __attribute__((swiftcall)) bridge(uint64_t a,uint64_t b){assert(b==1);bridge_calls++;return (id)(uintptr_t)a;}
void *dlsym(void *handle,const char *name){(void)handle;assert(!strcmp(name,"$sSS10FoundationE19_bridgeToObjectiveCSo8NSStringCyF"));return bridge_available ? (void *)bridge : NULL;}
static double test_double(id o,const char *s){return !o ? 0 : !strcmp(s,"alpha") ? o->alpha : o->seconds;}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list ap;va_start(ap,sel);id result=nil;
    if(!strcmp(sel,"new") || !strcmp(sel,"alloc"))result=fresh(o->cls);
    else if(!strcmp(sel,"isMainThread"))result=(id)(uintptr_t)is_main;
    else if(!strcmp(sel,"isKindOfClass:")){Class c=va_arg(ap,Class);result=(id)(uintptr_t)(!strcmp(o->cls,c->cls) || (!strcmp(o->cls,"TwitchEmoteInputView") && !strcmp(c->cls,"UITextView")));}
    else if(!strcmp(sel,"stringWithUTF8String:"))result=text(va_arg(ap,const char *));
    else if(!strcmp(sel,"UTF8String"))result=o->value;
    else if(!strcmp(sel,"numberWithUnsignedLongLong:")){result=fresh("NSNumber");result->index=va_arg(ap,uint64_t);}
    else if(!strcmp(sel,"unsignedLongLongValue") || !strcmp(sel,"posterImageFrameIndex") || !strcmp(sel,"applicationState"))result=(id)(uintptr_t)o->index;
    else if(!strcmp(sel,"length") || !strcmp(sel,"statusCode"))result=(id)(uintptr_t)o->length;
    else if(!strcmp(sel,"frameCount"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"weakObjectsHashTable"))result=fresh("NSHashTable");
    else if(!strcmp(sel,"containsObject:")){id item=va_arg(ap,id);for(U i=0;i<o->count;i++)if(o->items[i]==item)result=(id)(uintptr_t)YES;}
    else if(!strcmp(sel,"addObject:")){assert(o->count<8);o->items[o->count++]=va_arg(ap,id);}
    else if(!strcmp(sel,"allObjects"))result=o;
    else if(!strcmp(sel,"objectAtIndex:"))result=o->items[va_arg(ap,U)];
    else if(!strcmp(sel,"mainQueue"))result=&mainqueue;
    else if(!strcmp(sel,"addOperationWithBlock:")){id block=va_arg(ap,id);((void (^)(void))block)();}
    else if(!strcmp(sel,"setCountLimit:"))assert(va_arg(ap,U)==128);
    else if(!strcmp(sel,"setTotalCostLimit:"))assert(va_arg(ap,U)==8*1024*1024);
    else if(!strcmp(sel,"bytes"))result=(id)o->bytes;
    else if(!strcmp(sel,"setObject:forKey:cost:")){cache_data=va_arg(ap,id);assert(va_arg(ap,id)->index==900000000000001ULL);assert(va_arg(ap,U)==cache_data->length);}
    else if(!strcmp(sel,"objectForKey:")){id key=va_arg(ap,id);result=!strcmp(o->cls,"NSCache") ? cache_data : o->items[key->index];}
    else if(!strcmp(sel,"initWithAnimatedGIFData:")){id data=va_arg(ap,id);assert(data==cache_data);o->value=data->value;o->count=3;copies++;result=o;}
    else if(!strcmp(sel,"setFrameCacheSizeMax:"))assert(va_arg(ap,U)==4);
    else if(!strcmp(sel,"imageLazilyCachedAtIndex:"))result=o->value->items[va_arg(ap,U)];
    else if(!strcmp(sel,"delayTimesForIndexes"))result=o->value->value;
    else if(!strcmp(sel,"displayLinkWithTarget:selector:")){result=fresh("CADisplayLink");result->target=va_arg(ap,id);assert(!strcmp(va_arg(ap,SEL),"ssTick:"));clock_link=result;}
    else if(!strcmp(sel,"setPreferredFramesPerSecond:"))assert(va_arg(ap,U)==30);
    else if(!strcmp(sel,"addToRunLoop:forMode:")){assert(va_arg(ap,id)==&runloop);assert(!strcmp((const char *)va_arg(ap,id)->value,"kCFRunLoopCommonModes"));}
    else if(!strcmp(sel,"mainRunLoop"))result=&runloop;
    else if(!strcmp(sel,"sharedApplication"))result=&app;
    else if(!strcmp(sel,"window"))result=o->window;
    else if(!strcmp(sel,"superview"))result=o->parent;
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"markedTextRange"))result=o->marked;
    else if(!strcmp(sel,"attributedText") || !strcmp(sel,"layoutManager"))result=o->value;
    else if(!strcmp(sel,"string"))result=o;
    else if(!strcmp(sel,"characterAtIndex:"))result=(id)(uintptr_t)o->units[va_arg(ap,U)];
    else if(!strcmp(sel,"attribute:atIndex:effectiveRange:")){assert(!strcmp((const char *)va_arg(ap,id)->value,"NSAttachment"));U i=va_arg(ap,U);assert(!va_arg(ap,Range *));result=o->items[i];}
    else if(!strcmp(sel,"setImage:")){o->image=va_arg(ap,id);assignments++;}
    else if(!strcmp(sel,"invalidateDisplayForCharacterRange:")){Range r=va_arg(ap,Range);assert(r.length==1);invalidations++;}
    else if(!strcmp(sel,"invalidate"))o->invalidated=YES;
    else assert(!"Unexpected RN preview selector");
    va_end(ap);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static Rect original_bounds(id self,SEL command,id container,Rect line,Point p,U index){(void)self;(void)command;(void)container;(void)line;(void)p;(void)index;originals++;return (Rect){{0,-3},{24,24}};}
static void original_view(id self,SEL command){(void)self;(void)command;originals++;}
static void original_change(id self,SEL command,id editor){(void)self;(void)command;(void)editor;originals++;}
static void original_dealloc(id self,SEL command){(void)self;(void)command;deallocs++;}
typedef struct {const char *encoding;IMP original;} TestMethod;
static TestMethod bounds_method={"{CGRect={CGPoint=dd}{CGSize=dd}}80@0:8@16{CGRect={CGPoint=dd}{CGSize=dd}}24{CGPoint=dd}56q72",(IMP)original_bounds};
static TestMethod view_method={"v16@0:8",(IMP)original_view},change_method={"v24@0:8@16",(IMP)original_change},dealloc_method={"v16@0:8",(IMP)original_dealloc};
static unsigned installed;
Method class_getInstanceMethod(Class cls,SEL sel){(void)cls;if(!strcmp(sel,"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:"))return &bounds_method;if(!strcmp(sel,"dealloc"))return &dealloc_method;return strchr(sel,':') ? &change_method : &view_method;}
const char *method_getTypeEncoding(Method m){return ((TestMethod *)m)->encoding;}
IMP method_getImplementation(Method m){return ((TestMethod *)m)->original;}
IMP method_setImplementation(Method m,IMP hook){(void)m;(void)hook;installed++;return NULL;}
BOOL class_addMethod(Class cls,SEL sel,IMP imp,const char *encoding){(void)sel;(void)imp;(void)encoding;return !strcmp(cls->cls,"StreamsideRNPreviewClock");}
BOOL class_addIvar(Class cls,const char *name,size_t size,uint8_t alignment,const char *type){(void)cls;assert(!strcmp(name,"_state") && size==sizeof(State *) && alignment==3 && !strcmp(type,"^v"));return YES;}
Class objc_allocateClassPair(Class base,const char *name,size_t n){(void)base;assert(!n);return objc_getClass(name);}
void objc_registerClassPair(Class cls){(void)cls;}
void objc_disposeClassPair(Class cls){(void)cls;}
IMP class_getMethodImplementation(Class cls,SEL sel){(void)cls;assert(!strcmp(sel,"dealloc"));return (IMP)original_dealloc;}
static id attachment(const char *url){id a=fresh(ATTACHMENT);a->url[0]=(uint64_t)(uintptr_t)text(url);a->url[1]=1;return a;}
static id provider(void){return attachment("https://static-cdn.jtvnw.net/emoticons/v2/900000000000001/static/dark/2.0");}
static void geometry(void) {
    bridge_string=bridge;bounds_original=(IMP)original_bounds;id a=provider();
    Rect r=attachment_bounds(a,"bounds",nil,(Rect){0},(Point){0},0);assert(r.origin.y==-3 && r.size.width==72 && r.size.height==24);
    assert(attachment_number(a)==900000000000001ULL && bridge_calls==1);
    aspect=0.5;r=attachment_bounds(a,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==12 && r.size.height==24);
    aspect=8;r=attachment_bounds(a,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==192 && r.size.height==24);
    aspect=NAN;r=attachment_bounds(a,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);
    const char *urls[]={"https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0","https://example.com/emoticons/v2/900000000000001/static/dark/1.0","https://static-cdn.jtvnw.net/emoticons/v2/900000000000002/static/dark/1.0"};
    aspect=3;for(unsigned i=0;i<3;i++){r=attachment_bounds(attachment(urls[i]),"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);}
    url_gap=8;assert(!attachment_number(provider()));url_gap=16;
    enabled=NO;r=attachment_bounds(a,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);
    enabled=YES;is_main=NO;assert(!attachment_number(a));is_main=YES;bridge_string=NULL;assert(!attachment_number(a));
    assert(originals==8);
}
static U gif_bytes(unsigned char *p,unsigned count) {
    const unsigned char header[]={ 'G','I','F','8','9','a',1,0,1,0,0,0,0};memcpy(p,header,13);U n=13;
    const unsigned char frame[]={0x2c,0,0,0,0,1,0,1,0,0,2,2,0x44,1,0};
    for(unsigned i=0;i<count;i++){memcpy(p+n,frame,sizeof(frame));n+=sizeof(frame);}p[n++]=0x3b;return n;
}
static void gif_gate(void) {
    unsigned char p[8192];U n=gif_bytes(p,3);assert(tas_rn_composer_gif(p,n)==3);
    for(U i=0;i<n;i++)assert(!tas_rn_composer_gif(p,i));
    n=gif_bytes(p,1);assert(!tas_rn_composer_gif(p,n));n=gif_bytes(p,301);assert(!tas_rn_composer_gif(p,n));
    n=gif_bytes(p,3);p[6]=0xff;p[7]=0xf;p[8]=0xff;p[9]=0xf;assert(!tas_rn_composer_gif(p,n));
    n=gif_bytes(p,3);p[13+1]=2;assert(!tas_rn_composer_gif(p,n));
    n=gif_bytes(p,3);p[13+11]=200;assert(!tas_rn_composer_gif(p,n));
    assert(tas_rn_composer_delay(12.5)==12.5 && tas_rn_composer_delay(0.01999999955)==0.01999999955);
    assert(tas_rn_composer_delay(NAN)==0.1 && !tas_rn_composer_delta(1,0) && tas_rn_composer_delta(8,1)==0.25);
    id data=fresh("NSData"),response=fresh("NSHTTPURLResponse");data->length=gif_bytes(data->bytes,3);response->length=200;
    tas_rn_composer_ui_image(900000000000001ULL,data,response,nil);assert(cache_data==data && GET(images)==1);
    response->length=404;tas_rn_composer_ui_image(900000000000001ULL,data,response,nil);assert(GET(images)==1);
    response->length=200;tas_rn_composer_ui_image(900000000000001ULL,data,response,fresh("NSError"));assert(GET(images)==1);
    enabled=NO;tas_rn_composer_ui_image(900000000000001ULL,data,response,nil);assert(GET(images)==1);
}
static void playback(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),source=fresh("NSAttributedString"),window=fresh("UIWindow");
    owner->editor=editor;editor->window=window;editor->parent=window;editor->value=source;
    source->length=3;source->units[0]=source->units[2]=0xfffc;source->units[1]='x';source->items[0]=provider();source->items[2]=provider();
    id template=fresh("Animation"),delays=fresh("NSDictionary");template->value=delays;
    for(unsigned i=0;i<3;i++){template->items[i]=fresh("UIImage");delays->items[i]=fresh("NSNumber");delays->items[i]->seconds=i==2 ? 12.5 : 0.1;}
    cache_data=fresh("NSData");cache_data->value=template;cache_data->length=gif_bytes(cache_data->bytes,3);image_bytes=fresh("NSCache");
    sync(owner);id target=owner->target;State *s=state(target);assert(s && s->count==2 && s->link && copies==2);
    assert(s->frames[0].animation!=s->frames[1].animation);
    id link=s->link;link->seconds=1;animate(target,"ssTick:",link);assert(!assignments);
    link->seconds=1.11;animate(target,"ssTick:",link);assert(assignments==2 && invalidations==2 && s->frames[0].index==1);
    sync(owner);assert(copies==2 && s->frames[0].index==1); /* no rebuild/reset */
    link->seconds=1.22;animate(target,"ssTick:",link);assert(assignments==4 && s->frames[0].index==2);
    link->seconds=1.47;animate(target,"ssTick:",link);assert(assignments==4); /* long final hold */
    editor->marked=fresh("UITextRange");link->seconds=1.72;animate(target,"ssTick:",link);assert(assignments==4);sync(owner);assert(copies==2);editor->marked=nil;
    /* Reordering keeps exact attachment/playhead identity, UTF-16 positions update. */
    id swap=source->items[0];source->items[0]=source->items[2];source->items[2]=swap;sync(owner);assert(copies==2 && s->frames[0].attachment==source->items[0]);
    editor->window=nil;sync(owner);assert(!s->link && link->invalidated);
    editor->window=window;sync(owner);assert(s->link && !s->timestamp && copies==2);
    link=s->link;link->seconds=2;animate(target,"ssTick:",link);assert(s->timestamp==2);
    tas_rn_composer_ui_retry_hooks();assert(!s->timestamp && copies==2);
    source->items[0]=source->items[2]=nil;sync(owner);assert(!s->link && !s->count);
    source->items[0]=provider();sync(owner);assert(s->link && s->count==1);
    owner_dealloc(owner,"dealloc");assert(!s->link && !s->count && deallocs==1);
    clock_dealloc(target,"dealloc");assert(deallocs==2);
    assert(source->units[0]==0xfffc && source->units[1]=='x' && source->length==3);
}
static void installation(void) {
    enabled=NO;tas_rn_composer_ui_retry_hooks();assert(!installed && !bridge_string);
    enabled=YES;bounds_method.encoding="v16@0:8";tas_rn_composer_ui_retry_hooks();assert(!bounds_original && installed==6);
    bounds_method.encoding="{CGRect={CGPoint=dd}{CGSize=dd}}80@0:8@16{CGRect={CGPoint=dd}{CGSize=dd}}24{CGPoint=dd}56q72";
    tas_rn_composer_ui_retry_hooks();assert(bounds_original && installed==7 && clock_class);
    tas_rn_composer_ui_retry_hooks();assert(installed==7);
}
static void cold_start(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),source=fresh("NSAttributedString"),window=fresh("UIWindow");
    owner->editor=editor;editor->window=window;editor->parent=window;editor->value=source;
    source->length=1;source->units[0]=0xfffc;source->items[0]=provider();
    /* Original token already exists while its first network request is pending. */
    sync(owner);assert(!owner->target && !copies);
    assert(owners && owners->count==1 && owners->items[0]==owner);
    sync(owner);assert(owners->count==1); /* pending owners are a weak set */
    id template=fresh("Animation"),delays=fresh("NSDictionary");template->value=delays;
    for(unsigned i=0;i<3;i++){template->items[i]=fresh("UIImage");delays->items[i]=fresh("NSNumber");delays->items[i]->seconds=0.1;}
    id data=fresh("NSData"),response=fresh("NSHTTPURLResponse");
    data->value=template;data->length=gif_bytes(data->bytes,3);response->length=200;
    tas_rn_composer_ui_image(900000000000001ULL,data,response,nil);
    State *s=state(owner->target);assert(s && s->count==1 && s->link && copies==1);
    assert(s->frames[0].attachment==source->items[0]);
    /* Native completion may assign its still image after byte-cache delivery. */
    id still=fresh("UIImage");v1(source->items[0],"setImage:",still);
    s->link->seconds=1;animate(owner->target,"ssTick:",s->link);
    s->link->seconds=1.11;animate(owner->target,"ssTick:",s->link);
    assert(source->items[0]->image==template->items[1] && invalidations==1);
    /* A token deleted before the data arrives must not be rebound. */
    id second=fresh(INPUT),editor2=fresh("TwitchEmoteInputView"),source2=fresh("NSAttributedString");
    second->editor=editor2;editor2->window=window;editor2->parent=window;editor2->value=source2;
    source2->length=1;source2->units[0]=0xfffc;source2->items[0]=provider();cache_data=nil;
    sync(second);assert(!second->target && owners->count==2);
    source2->length=0;source2->items[0]=nil;
    tas_rn_composer_ui_image(900000000000001ULL,data,response,nil);
    assert(!second->target && copies==1 && s->frames[0].index==1);
    assert(source->length==1 && source->units[0]==0xfffc); /* no edit/retype required */
    owner_dealloc(owner,"dealloc");clock_dealloc(owner->target,"dealloc");
}
int main(int argc,char **argv) {
    assert(argc==2);
    if(!strcmp(argv[1],"geometry"))geometry();else if(!strcmp(argv[1],"gif"))gif_gate();else if(!strcmp(argv[1],"playback"))playback();else if(!strcmp(argv[1],"install"))installation();else if(!strcmp(argv[1],"cold"))cold_start();else abort();
    for(unsigned i=0;i<pool_count;i++)free(pool[i]);return 0;
}
'''

class RNComposerUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();p=Path(cls.folder.name);(p/'objc').mkdir()
        runtime=RUNTIME+'\nsize_t class_getInstanceSize(Class);\nBOOL class_addIvar(Class,const char *,size_t,uint8_t,const char *);\n'
        for name in ('runtime.h','objc.h','message.h'):(p/'objc'/name).write_text(runtime)
        source=(ROOT/'src/TASRNComposerUI.c').read_text()
        for obj,sel in [('ancestor','alpha'),('value','doubleValue'),('link','timestamp')]:
            source=source.replace(f'((double (*)(id,SEL))objc_msgSend)({obj},sel_registerName("{sel}"))',f'test_double({obj},"{sel}")')
        (p/'composer.c').write_text(source);(p/'test.c').write_text(HARNESS);cls.binary=p/'test'
        zig=os.environ.get('ZIG') or shutil.which('zig');assert zig
        result=subprocess.run([zig,'cc','-fblocks','-Wall','-Wextra','-Werror','-Wno-cast-function-type-mismatch','-fsanitize=address,undefined','-ffunction-sections','-fdata-sections','-I',str(p),'-I',str(ROOT/'src'),str(p/'test.c'),'-Wl,--gc-sections','-pthread','-o',str(cls.binary)],capture_output=True,text=True)
        if result.returncode:raise AssertionError(result.stderr)
    def run_mode(self,mode):
        r=subprocess.run([self.binary,mode],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
        self.assertEqual(r.returncode,0,r.stderr)
    def test_native_height_baseline_wide_narrow_identity_bridge_and_fallback(self):self.run_mode('geometry')
    def test_gif_preflight_body_budget_complete_blocks_timing_and_transport_gate(self):self.run_mode('gif')
    def test_independent_clocks_reconciliation_ime_deletion_visibility_and_teardown(self):self.run_mode('playback')
    def test_exact_abi_preference_retry_and_idempotent_hooks(self):self.run_mode('install')
    def test_first_download_starts_original_attachment_without_retyping(self):self.run_mode('cold')
