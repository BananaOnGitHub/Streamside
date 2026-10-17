"""Production RN attachment geometry, holds and preview clock with a small ObjC host."""
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
    id editor,next,identity,target,pending,value,window,parent,marked,image,items[8];
    unsigned char bytes[2048];uint16_t units[8];U length,count,index;
    double seconds,alpha;BOOL hidden,invalidated;int releases;
    id prop_selection,native_identity;uint64_t plain[2];id plain_cache;uint64_t generation,queued_generation;BOOL accept_edit;Size image_size;void *context;Point point;Rect rect;Insets insets;Range range;BOOL first,refuse_resign;
};
static struct Fake classes[64];static unsigned classes_count;
static id pool[512];static unsigned pool_count;
static BOOL enabled=YES,is_main=YES,known=YES,bridge_available=YES,webp_mode=NO;
static double aspect=3;
static unsigned copies,invalidations,assignments,originals,deallocs,bridge_calls,layout_invalidations;
static ptrdiff_t url_gap=16,plain_gap=16;
static struct Fake app={.cls="UIApplication"},mainqueue={.cls="NSOperationQueue"},runloop={.cls="NSRunLoop"},metadata={.cls="NSDictionary"};
static id cache_data,clock_link,queued,shown;
static BOOL modal=NO,present_ok=YES,frame_pending=NO;
static unsigned presentations,haptics,scheduled,added,removed,resignations;
BOOL tas_emote_ui_modal_visible(id view){(void)view;return modal;}
BOOL tas_emote_ui_present_details(id view,id data){assert(data==&metadata && !view->editor->first);presentations++;shown=view;return present_ok;}
static Size __attribute__((unused)) test_size(id o){return o->image_size;}
static Point test_point(id o,id editor){assert(editor);return o->point;}
static Rect test_rect(id o,Range range,id container){assert(range.length==1 && container);return o->rect;}
static Insets test_insets(id o){return o->insets;}
static Range test_range(id o){return o->range;}

static id fresh(const char *cls){id o=calloc(1,sizeof(*o));assert(pool_count<512);pool[pool_count++]=o;o->cls=cls;o->alpha=1;return o;}
static id text(const char *s){id o=fresh("NSString");o->value=(id)s;return o;}
Class objc_getClass(const char *s){for(unsigned i=0;i<classes_count;i++)if(!strcmp(classes[i].cls,s))return &classes[i];assert(classes_count<64);classes[classes_count].cls=s;return &classes[classes_count++];}
Class object_getClass(id o){return o;}
SEL sel_registerName(const char *s){return s;}
Ivar class_getInstanceVariable(Class cls,const char *s){(void)cls;if(!strcmp(s,"url"))return (Ivar)(uintptr_t)offsetof(struct Fake,url);if(!strcmp(s,"loaded"))return (Ivar)(uintptr_t)(offsetof(struct Fake,url)+url_gap);if(!strcmp(s,"textView"))return (Ivar)(uintptr_t)offsetof(struct Fake,editor);if(!strcmp(s,"emoteMapDict"))return (Ivar)(uintptr_t)offsetof(struct Fake,next);if(!strcmp(s,"currentPlainText"))return (Ivar)(uintptr_t)offsetof(struct Fake,plain);if(!strcmp(s,"imageCache"))return (Ivar)(uintptr_t)(offsetof(struct Fake,plain)+plain_gap);if(!strcmp(s,"_state"))return (Ivar)(uintptr_t)offsetof(struct Fake,context);return NULL;}
ptrdiff_t ivar_getOffset(Ivar v){return (ptrdiff_t)(uintptr_t)v;}
size_t class_getInstanceSize(Class cls){(void)cls;return sizeof(struct Fake);}
id objc_retain(id o){return o;}
void objc_release(id o){if(o)o->releases++;}
id objc_initWeak(id *p,id o){*p=o;return o;}
id objc_loadWeakRetained(id *p){return *p;}
void objc_destroyWeak(id *p){*p=nil;}
id objc_getAssociatedObject(id o,const void *key){return !o ? nil : key==&identity_key ? o->identity : key==&native_image_key ? o->native_identity : key==&pending_map_key ? o->pending : o->target;}
void objc_setAssociatedObject(id o,const void *key,id value,uintptr_t policy){assert(policy==1);if(key==&identity_key)o->identity=value;else if(key==&native_image_key)o->native_identity=value;else if(key==&pending_map_key)o->pending=value;else {assert(key==&state_key);o->target=value;}}
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
    else if(!strcmp(sel,"null"))result=fresh("NSNull");
    else if(!strcmp(sel,"isEqualToString:")){id other=va_arg(ap,id);result=(id)(uintptr_t)!strcmp((const char *)o->value,(const char *)other->value);}
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
    else if(!strcmp(sel,"imageLazilyCachedAtIndex:")){U index=va_arg(ap,U);result=frame_pending?nil:o->value->items[index];}
    else if(!strcmp(sel,"delayTimesForIndexes"))result=o->value->value;
    else if(!strcmp(sel,"displayLinkWithTarget:selector:")){result=fresh("CADisplayLink");result->target=va_arg(ap,id);assert(!strcmp(va_arg(ap,SEL),"ssTick:"));clock_link=result;}
    else if(!strcmp(sel,"setPreferredFramesPerSecond:"))assert(va_arg(ap,U)==60);
    else if(!strcmp(sel,"addToRunLoop:forMode:")){assert(va_arg(ap,id)==&runloop);assert(!strcmp((const char *)va_arg(ap,id)->value,"kCFRunLoopCommonModes"));}
    else if(!strcmp(sel,"mainRunLoop"))result=&runloop;
    else if(!strcmp(sel,"sharedApplication"))result=&app;
    else if(!strcmp(sel,"view"))result=o->editor;
    else if(!strcmp(sel,"selection"))result=o->prop_selection;
    else if(!strcmp(sel,"state"))result=(id)(uintptr_t)o->index;
    else if(!strcmp(sel,"initWithTarget:action:")){o->target=va_arg(ap,id);assert(!strcmp(va_arg(ap,SEL),"ssHold:"));result=o;}
    else if(!strcmp(sel,"setMinimumPressDuration:"))assert(va_arg(ap,double)==0.5);
    else if(!strcmp(sel,"setCancelsTouchesInView:"))assert(!va_arg(ap,int));
    else if(!strcmp(sel,"setDelegate:"))o->target=va_arg(ap,id);
    else if(!strcmp(sel,"addGestureRecognizer:")){id g=va_arg(ap,id);g->editor=o;added++;}
    else if(!strcmp(sel,"removeGestureRecognizer:")){id g=va_arg(ap,id);g->editor=nil;removed++;}
    else if(!strcmp(sel,"textContainer"))result=o->value;
    else if(!strcmp(sel,"numberOfGlyphs"))result=(id)(uintptr_t)o->length;
    else if(!strcmp(sel,"glyphIndexForPoint:inTextContainer:")){(void)va_arg(ap,Point);assert(va_arg(ap,id)==o);result=(id)(uintptr_t)o->index;}
    else if(!strcmp(sel,"characterIndexForGlyphAtIndex:"))result=(id)(uintptr_t)va_arg(ap,U);
    else if(!strcmp(sel,"performSelector:withObject:afterDelay:")){assert(!strcmp(va_arg(ap,SEL),"ssDetails:"));assert(!va_arg(ap,id) && va_arg(ap,double)==0);queued=o;scheduled++;}
    else if(!strcmp(sel,"initWithStyle:")){assert(va_arg(ap,long)==0);result=o;}
    else if(!strcmp(sel,"impactOccurred"))haptics++;
    else if(!strcmp(sel,"respondsToSelector:")){SEL probe=va_arg(ap,SEL);result=(id)(uintptr_t)(!strcmp(o->cls,"UITextItem") && (!strcmp(probe,"textAttachment") || !strcmp(probe,"range")));}
    else if(!strcmp(sel,"textAttachment") || !strcmp(sel,"image"))result=o->image;
    else if(!strcmp(sel,"configurationWithMenu:"))result=va_arg(ap,id);
    else if(!strcmp(sel,"window"))result=o->window;
    else if(!strcmp(sel,"superview"))result=o->parent;
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"isFirstResponder"))result=(id)(uintptr_t)o->first;
    else if(!strcmp(sel,"resignFirstResponder")){resignations++;if(!o->refuse_resign){o->first=NO;result=(id)(uintptr_t)YES;}}
    else if(!strcmp(sel,"markedTextRange"))result=o->marked;
    else if(!strcmp(sel,"attributedText") || !strcmp(sel,"layoutManager"))result=o->value;
    else if(!strcmp(sel,"string"))result=o;
    else if(!strcmp(sel,"characterAtIndex:"))result=(id)(uintptr_t)o->units[va_arg(ap,U)];
    else if(!strcmp(sel,"attribute:atIndex:effectiveRange:")){assert(!strcmp((const char *)va_arg(ap,id)->value,"NSAttachment"));U i=va_arg(ap,U);assert(!va_arg(ap,Range *));result=o->items[i];}
    else if(!strcmp(sel,"setImage:")){o->image=va_arg(ap,id);assignments++;}
    else if(!strcmp(sel,"invalidateLayoutForCharacterRange:actualCharacterRange:")){Range r=va_arg(ap,Range);assert(r.length==1 && (r.location==0 || r.location==2) && !va_arg(ap,Range *));layout_invalidations++;}
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
static BOOL original_edit(id self,SEL command,id editor,Range range,id text){(void)command;(void)editor;(void)range;(void)text;originals++;return self->accept_edit;}
static void original_selection_setter(id self,SEL command,id requested){assert(!strcmp(command,"setSelection:"));self->prop_selection=requested;self->generation++;if(requested)self->queued_generation=self->generation;}
static TestMethod edit_method={"B48@0:8@16{_NSRange=QQ}24@40",(IMP)original_edit},setter_method={"v24@0:8@16",(IMP)original_selection_setter},getter_method={"@16@0:8",NULL};
static void original_image(id self,SEL command,id image){(void)command;self->image=image;assignments++;}
static TestMethod image_method={"v24@0:8@16",(IMP)original_image};
static unsigned installed,optional_mode;
static TestMethod item_method={"@40@0:8@16@24@32",(IMP)original_change},interaction_method={"B56@0:8@16@24{_NSRange=QQ}32q48",(IMP)original_change};
Method class_getInstanceMethod(Class cls,SEL sel){(void)cls;if(!strcmp(sel,"setImage:"))return &image_method;if(!strcmp(sel,"textView:shouldChangeTextInRange:replacementText:"))return &edit_method;if(!strcmp(sel,"setSelection:"))return &setter_method;if(!strcmp(sel,"selection"))return &getter_method;if(strstr(sel,"menuConfigurationForTextItem"))return optional_mode ? &item_method : NULL;if(strstr(sel,"shouldInteractWithTextAttachment"))return optional_mode ? &interaction_method : NULL;if(!strcmp(sel,"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:"))return &bounds_method;if(!strcmp(sel,"dealloc"))return &dealloc_method;return strchr(sel,':') ? &change_method : &view_method;}
const char *method_getTypeEncoding(Method m){return ((TestMethod *)m)->encoding;}
IMP method_getImplementation(Method m){return ((TestMethod *)m)->original;}
IMP method_setImplementation(Method m,IMP hook){(void)m;(void)hook;installed++;return NULL;}
BOOL class_addMethod(Class cls,SEL sel,IMP imp,const char *encoding){(void)sel;(void)imp;(void)encoding;return !strcmp(cls->cls,"StreamsideRNPreviewClock") || (!strcmp(cls->cls,INPUT) && (strstr(sel,"menuConfigurationForTextItem") || strstr(sel,"shouldInteractWithTextAttachment")));}
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
id tas_animated_image_create(id data){
    if(!webp_mode)return nil;
    id animation=fresh("StreamsideAnimatedWebP");animation->value=data->value;animation->count=3;copies++;return animation;
}
void tas_animated_image_prepare(id data){(void)data;}
static void playback(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),source=fresh("NSAttributedString"),window=fresh("UIWindow");
    owner->editor=editor;editor->window=window;editor->parent=window;editor->value=source;
    source->length=3;source->units[0]=source->units[2]=0xfffc;source->units[1]='x';source->items[0]=provider();source->items[2]=provider();
    id template=fresh("Animation"),delays=fresh("NSDictionary");template->value=delays;
    for(unsigned i=0;i<3;i++){template->items[i]=fresh("UIImage");delays->items[i]=fresh("NSNumber");delays->items[i]->seconds=i==2 ? 12.5 : 0.1;}
    cache_data=fresh("NSData");cache_data->value=template;cache_data->length=gif_bytes(cache_data->bytes,3);
    if(webp_mode){extern const unsigned char webp_fixture[];extern const unsigned long webp_fixture_size;
        memcpy(cache_data->bytes,webp_fixture,webp_fixture_size);cache_data->length=webp_fixture_size;}
    image_bytes=fresh("NSCache");
    sync(owner);id target=owner->target;State *s=state(target);assert(s && s->count==2 && s->link && copies==2);
    assert(s->frames[0].animation!=s->frames[1].animation);
    id link=s->link;link->seconds=1;animate(target,"ssTick:",link);assert(!assignments);
    if(frame_pending){
        link->seconds=1.250001;animate(target,"ssTick:",link); /* delta caps to .25 */
        assert(s->frames[0].index==2 && !assignments);
        frame_pending=NO;link->seconds=1.251;animate(target,"ssTick:",link);
        assert(assignments==2 && source->items[0]->image==template->items[2]);
        owner_dealloc(owner,"dealloc");clock_dealloc(target,"dealloc");return;
    }
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
    enabled=YES;bounds_method.encoding="v16@0:8";tas_rn_composer_ui_retry_hooks();assert(!bounds_original && installed==10);
    bounds_method.encoding="{CGRect={CGPoint=dd}{CGSize=dd}}80@0:8@16{CGRect={CGPoint=dd}{CGSize=dd}}24{CGPoint=dd}56q72";
    tas_rn_composer_ui_retry_hooks();assert(bounds_original && installed==11 && clock_class);
    tas_rn_composer_ui_retry_hooks();assert(installed==11);
}
static void cold_start(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),source=fresh("NSAttributedString"),window=fresh("UIWindow");
    owner->editor=editor;editor->window=window;editor->parent=window;editor->value=source;
    source->length=1;source->units[0]=0xfffc;source->items[0]=provider();
    /* Original token already exists while its first network request is pending. */
    sync(owner);assert(owner->target && state(owner->target)->hold && !state(owner->target)->link && !copies);
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
    sync(second);assert(second->target && !state(second->target)->link && owners->count==2);
    source2->length=0;source2->items[0]=nil;
    tas_rn_composer_ui_image(900000000000001ULL,data,response,nil);
    assert(!state(second->target)->link && copies==1 && s->frames[0].index==1);
    assert(source->length==1 && source->units[0]==0xfffc); /* no edit/retype required */
    owner_dealloc(owner,"dealloc");clock_dealloc(owner->target,"dealloc");
}

static id map_applied,value_applied;
static void original_map(id self,SEL command,id map){(void)self;assert(!strcmp(command,"setEmoteMap:"));originals++;map_applied=map;}
static void original_value(id self,SEL command,id text){(void)self;(void)command;originals++;value_applied=text;}
static void composition(void) {
    tas_rn_composer_ui_retry_hooks();map_original=(IMP)original_map;value_original=(IMP)original_value;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),source=fresh("NSAttributedString");owner->editor=editor;editor->value=source;
    source->length=4;source->units[0]='W';source->units[1]='i';source->units[2]='d';source->units[3]='e';
    id prediction=text("Wide"),first=fresh("NSDictionary"),latest=fresh("NSDictionary");
    editor->marked=fresh("UITextRange");
    changed(owner,"textViewDidChange:",editor);selection(owner,"textViewDidChangeSelection:",editor);
    value(owner,"setValue:",prediction);emote_map(owner,"setEmoteMap:",first);emote_map(owner,"setEmoteMap:",latest);
    assert(!originals && !map_applied && !value_applied && owner->pending==latest && GET(provisional)==5);
    assert(source->length==4 && source->units[3]=='e'); /* UIKit's provisional text untouched */
    editor->marked=nil;changed(owner,"textViewDidChange:",editor);
    assert(originals==2 && map_applied==latest && !owner->pending && !value_applied);
    /* Cancelling a prediction never replays its discarded full value. */
    editor->marked=fresh("UITextRange");value(owner,"setValue:",prediction);emote_map(owner,"setEmoteMap:",first);
    source->length=2;editor->marked=nil;selection(owner,"textViewDidChangeSelection:",editor);
    assert(originals==4 && source->length==2 && !value_applied && !owner->pending && map_applied==first);
    value(owner,"setValue:",text("Wide"));assert(originals==5 && value_applied);
    editor->marked=fresh("UITextRange");emote_map(owner,"setEmoteMap:",nil);editor->marked=nil;changed(owner,"textViewDidChange:",editor);
    assert(originals==7 && !map_applied && !owner->pending);
    /* Missing donor editor and disabled emotes retain original behavior. */
    owner->editor=nil;value(owner,"setValue:",prediction);assert(originals==8);
    owner->editor=editor;editor->marked=fresh("UITextRange");enabled=NO;changed(owner,"textViewDidChange:",editor);assert(originals==9);
}

static id detail_owner,detail_editor,detail_source,detail_target,detail_gesture;
static void setup_details(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    detail_owner=fresh(INPUT);detail_editor=fresh("TwitchEmoteInputView");detail_source=fresh("NSAttributedString");
    detail_owner->editor=detail_editor;detail_editor->window=fresh("UIWindow");detail_editor->value=detail_source;
    detail_editor->insets=(Insets){.top=8,.left=4};
    detail_source->length=3;detail_source->units[0]=detail_source->units[2]=0xfffc;detail_source->units[1]='x';
    detail_source->items[0]=provider();detail_source->items[2]=attachment("https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0");
    detail_source->rect=(Rect){{0,0},{24,24}};
    sync(detail_owner);detail_target=detail_owner->target;detail_gesture=state(detail_target)->hold;
    if(!optional_mode)assert(detail_gesture && added==1 && !state(detail_target)->link);
    if(detail_gesture){detail_gesture->point=(Point){12,16};detail_gesture->index=1;}
}
static void detail_hits(void) {
    setup_details();Range r={0};id touch=fresh("UITouch");touch->point=detail_gesture->point;
    assert(attachment_at_point(detail_target,detail_gesture,touch,&r)==detail_source->items[0] && r.location==0 && r.length==1);
    assert(hold_receive_touch(detail_target,"touch",detail_gesture,touch));
    assert(hold_should_begin(detail_target,"begin",detail_gesture));
    id native=fresh("Gesture"),child=fresh("UIView");native->editor=child;child->parent=detail_editor;
    assert(hold_priority(detail_target,"priority",detail_gesture,native));
    native->editor=fresh("UIView");assert(!hold_priority(detail_target,"priority",detail_gesture,native));
    assert(!hold_priority(detail_target,"priority",detail_gesture,detail_gesture));
    touch->point=(Point){100,16};assert(!hold_receive_touch(detail_target,"touch",detail_gesture,touch));
    native->editor=detail_editor;assert(!hold_priority(detail_target,"priority",detail_gesture,native));
    detail_source->index=1;assert(!attachment_at_point(detail_target,detail_gesture,detail_gesture,&r)); /* text */
    detail_source->index=2;assert(!attachment_at_point(detail_target,detail_gesture,detail_gesture,&r)); /* native */
    detail_source->index=3;assert(!attachment_at_point(detail_target,detail_gesture,detail_gesture,&r)); /* outside glyphs */
    detail_source->index=0;detail_editor->marked=fresh("UITextRange");assert(!hold_should_begin(detail_target,"begin",detail_gesture));detail_editor->marked=nil;
    modal=YES;assert(!hold_should_begin(detail_target,"begin",detail_gesture));modal=NO;
    enabled=NO;assert(!hold_should_begin(detail_target,"begin",detail_gesture));enabled=YES;
    detail_editor->window=nil;assert(!hold_should_begin(detail_target,"begin",detail_gesture));
    detail_editor->window=fresh("UIWindow");detail_gesture->point.x=NAN;assert(!hold_should_begin(detail_target,"begin",detail_gesture));
    sync(detail_owner);assert(added==1); /* no duplicate recognizers */
}
static void detail_safety(void) {
    setup_details();
    detail_editor->first=YES;
    detail_gesture->index=2;hold(detail_target,"hold",detail_gesture);assert(!scheduled);
    detail_gesture->index=1;hold(detail_target,"hold",detail_gesture);hold(detail_target,"hold",detail_gesture);
    assert(scheduled==1 && queued==detail_target && !presentations);
    details(queued,"details",nil);assert(presentations==1 && shown==detail_owner && haptics==1 && GET(details_holds)==1 && !state(queued)->details_attachment);
    assert(resignations==1 && GET(details_blurs)==1 && !detail_editor->first);
    details(queued,"details",nil);assert(presentations==1 && haptics==1);
    hold(detail_target,"hold",detail_gesture);id original=detail_source->items[0];detail_source->items[0]=provider();
    details(queued,"details",nil);assert(presentations==1); /* same ID, replaced native attachment */
    detail_source->items[0]=original;hold(detail_target,"hold",detail_gesture);detail_editor->marked=fresh("UITextRange");
    details(queued,"details",nil);assert(presentations==1);detail_editor->marked=nil;
    hold(detail_target,"hold",detail_gesture);modal=YES;details(queued,"details",nil);assert(presentations==1);modal=NO;
    hold(detail_target,"hold",detail_gesture);known=NO;details(queued,"details",nil);assert(presentations==1);known=YES; /* metadata refreshed */
    hold(detail_target,"hold",detail_gesture);present_ok=NO;details(queued,"details",nil);assert(presentations==2 && haptics==1);
    hold(detail_target,"hold",detail_gesture);state(detail_target)->owner=nil;details(queued,"details",nil);assert(presentations==2);state(detail_target)->owner=detail_owner;
    hold(detail_target,"hold",detail_gesture);owner_dealloc(detail_owner,"dealloc");
    assert(!state(detail_target)->hold && !state(detail_target)->details_attachment && removed==1 && !detail_gesture->target);
    details(queued,"details",nil);assert(presentations==2);clock_dealloc(detail_target,"dealloc");
    assert(detail_source->length==3 && detail_source->units[1]=='x');
}
static void detail_keyboard(void) {
    setup_details();id text=detail_editor->value;id attachment=detail_source->items[0];
    detail_editor->first=YES;detail_editor->refuse_resign=YES;
    hold(detail_target,"hold",detail_gesture);details(queued,"details",nil);
    assert(resignations==1 && GET(details_blur_refused)==1 && !presentations && !haptics && detail_editor->first);
    assert(detail_editor->value==text && detail_source->items[0]==attachment && !state(detail_target)->details_attachment);
    detail_editor->refuse_resign=NO;
    hold(detail_target,"hold",detail_gesture);details(queued,"details",nil);
    assert(resignations==2 && presentations==1 && haptics==1 && !detail_editor->first);
    assert(detail_editor->value==text && detail_source->items[0]==attachment);
    /* A closed/hardware-keyboard-free editor opens details without a redundant
     * resignation. Invalid metadata/competing sheets never blur the input. */
    hold(detail_target,"hold",detail_gesture);details(queued,"details",nil);assert(resignations==2 && presentations==2);
    detail_editor->first=YES;known=NO;
    hold(detail_target,"hold",detail_gesture);details(queued,"details",nil);assert(resignations==2 && detail_editor->first);
    known=YES;hold(detail_target,"hold",detail_gesture);modal=YES;details(queued,"details",nil);assert(resignations==2 && detail_editor->first);
}
static id original_menu(id owner,SEL command,id editor,id item,id menu){(void)owner;(void)command;(void)editor;(void)item;originals++;return menu;}
static BOOL original_interaction(id owner,SEL command,id editor,id attachment,Range range,long interaction){(void)owner;(void)command;(void)editor;(void)attachment;assert(range.length==1 && interaction==2);originals++;return NO;}
static void detail_menus(void) {
    setup_details();id item=fresh("UITextItem"),menu=fresh("UIMenu");item->range=(Range){0,1};item->image=detail_source->items[0];
    item_menu_original=(IMP)original_menu;interaction_original=(IMP)original_interaction;
    assert(!item_menu(detail_owner,"menu",detail_editor,item,menu));
    assert(!attachment_interaction(detail_owner,"interact",detail_editor,item->image,item->range,2) && !originals);
    item->range=(Range){2,1};item->image=detail_source->items[2];
    assert(item_menu(detail_owner,"menu",detail_editor,item,menu)==menu);
    assert(!attachment_interaction(detail_owner,"interact",detail_editor,item->image,item->range,2) && originals==2);
    item_menu_original=NULL;interaction_original=NULL;
    assert(item_menu(detail_owner,"menu",detail_editor,item,menu)==menu);
    assert(attachment_interaction(detail_owner,"interact",detail_editor,item->image,item->range,2));
    item->range=(Range){0,2};item->image=detail_source->items[0];assert(item_menu(detail_owner,"menu",detail_editor,item,menu)==menu);
    item->range=(Range){~0UL,1};assert(item_menu(detail_owner,"menu",detail_editor,item,menu)==menu);
    item->range=(Range){0,1};clear_hold(state(detail_target));assert(item_menu(detail_owner,"menu",detail_editor,item,menu)==menu);
    assert(attachment_interaction(detail_owner,"interact",detail_editor,item->image,item->range,2));
}
static void detail_abi(void) {
    optional_mode=1;item_method.encoding="v16@0:8";interaction_method.encoding="v16@0:8";
    setup_details();assert(!item_menu_installed && !interaction_installed && !state(detail_target)->hold && !added);
    item_method.encoding="@40@0:8@16@24@32";interaction_method.encoding="B56@0:8@16@24{_NSRange=QQ}32q48";
    tas_rn_composer_ui_retry_hooks();sync(detail_owner);
    assert(item_menu_installed && interaction_installed && item_menu_original && interaction_original && state(detail_target)->hold && added==1);
    unsigned count=installed;tas_rn_composer_ui_retry_hooks();sync(detail_owner);assert(installed==count && added==1);
}
/* Controlled donor queue: the inspected closure compares only its captured
 * selectionGeneration, then applies its old plain offsets to the current text. */
static void apply_queued_selection(id owner,id editor,id request) {
    if(owner->queued_generation==owner->generation)editor->range=request->range;
}
static void cursor_race(void) {
    tas_rn_composer_ui_retry_hooks();selection_setter=(IMP)original_selection_setter;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),request=fresh("NSDictionary");owner->editor=editor;owner->accept_edit=YES;
    request->range=(Range){5,0};original_selection_setter(owner,"setSelection:",request);
    /* A completed emote occupies one displayed character. Additional typing
     * expands that token back into an editable word before the queue drains. */
    assert(should_change(owner,"edit",editor,(Range){1,0},text("tail")));
    editor->range=(Range){9,0};apply_queued_selection(owner,editor,request);
    assert(editor->range.location==9 && !owner->prop_selection && owner->generation==2);
    assert(originals==1 && GET(selection_invalidations)==1);
    /* A vetoed edit must keep the requested selection valid. */
    original_selection_setter(owner,"setSelection:",request);owner->accept_edit=NO;
    assert(!should_change(owner,"edit",editor,(Range){1,0},text("x")));
    apply_queued_selection(owner,editor,request);assert(editor->range.location==5 && owner->prop_selection==request && owner->generation==3);
    /* Missing editor / disabled emotes / missing ABI preserve native behavior. */
    owner->accept_edit=YES;owner->editor=nil;assert(should_change(owner,"edit",editor,(Range){1,0},text("x")) && owner->generation==3);owner->editor=editor;
    enabled=NO;assert(should_change(owner,"edit",editor,(Range){1,0},text("x")) && owner->generation==3);enabled=YES;
    selection_setter=NULL;assert(should_change(owner,"edit",editor,(Range){1,0},text("x")) && owner->generation==3);
    selection_setter=(IMP)original_selection_setter;is_main=NO;assert(should_change(owner,"edit",editor,(Range){1,0},text("x")) && owner->generation==3);is_main=YES;
    owner->prop_selection=nil;assert(should_change(owner,"edit",editor,(Range){1,0},text("x")) && owner->generation==3);
}
static void cursor_abi(void) {
    setter_method.encoding="v16@0:8";tas_rn_composer_ui_retry_hooks();assert(edit_original && !selection_setter);
    setter_method.encoding="v24@0:8@16";getter_method.encoding="v16@0:8";
    tas_rn_composer_ui_retry_hooks();assert(!selection_setter);
    getter_method.encoding="@16@0:8";tas_rn_composer_ui_retry_hooks();assert(selection_setter==(IMP)original_selection_setter);
    unsigned before=installed;tas_rn_composer_ui_retry_hooks();assert(installed==before);
}
static void late_cursor_prop(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),request=fresh("NSDictionary");owner->editor=editor;
    owner->plain[0]=(uint64_t)(uintptr_t)text("Wide tail");owner->plain[1]=1;
    request->items[0]=text("Wide ");request->range=(Range){5,0};editor->range=(Range){9,0};
    selection_prop(owner,"setSelection:",request);apply_queued_selection(owner,editor,request);
    assert(!owner->prop_selection && editor->range.location==9 && GET(stale_selections)==1);
    request->items[0]=text("Wide tail");selection_prop(owner,"setSelection:",request);
    assert(owner->prop_selection==request);apply_queued_selection(owner,editor,request);assert(editor->range.location==5);
    editor->marked=fresh("UITextRange");selection_prop(owner,"setSelection:",request);assert(!owner->prop_selection && GET(stale_selections)==2);editor->marked=nil;
    /* Native props without a draft, and unknown field/bridge layouts, pass through. */
    request->items[0]=nil;selection_prop(owner,"setSelection:",request);assert(owner->prop_selection==request);
    request->items[0]=text("stale");plain_gap=8;selection_prop(owner,"setSelection:",request);assert(owner->prop_selection==request);plain_gap=16;bridge_string=NULL;selection_prop(owner,"setSelection:",request);assert(owner->prop_selection==request);
    enabled=NO;bridge_string=bridge;selection_prop(owner,"setSelection:",request);assert(owner->prop_selection==request);
    selection_prop(owner,"setSelection:",nil);assert(!owner->prop_selection);
}
static void late_native_cursor(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),request=fresh("NSDictionary");owner->editor=editor;owner->accept_edit=YES;
    owner->plain[0]=(uint64_t)(uintptr_t)text("Wide ");owner->plain[1]=1;
    /* No selection has arrived yet, so the edit guard has nothing to cancel. */
    assert(should_change(owner,"edit",editor,(Range){2,0},text("tail")));
    assert(!owner->prop_selection && GET(selection_invalidations)==0);
    owner->plain[0]=(uint64_t)(uintptr_t)text("Wide tail");editor->range=(Range){9,0};request->range=(Range){5,0};
    /* Bare native offsets reproduce the uncovered late-arrival path. */
    selection_prop(owner,"setSelection:",request);apply_queued_selection(owner,editor,request);
    assert(editor->range.location==5);
    /* The scoped adapter now preserves the original request draft. */
    editor->range=(Range){9,0};request->items[0]=text("Wide ");
    selection_prop(owner,"setSelection:",request);apply_queued_selection(owner,editor,request);
    assert(editor->range.location==9 && !owner->prop_selection && GET(stale_selections)==1);
    /* A current request can deliberately select the middle; never force end. */
    request->items[0]=text("Wide tail");request->range=(Range){2,3};
    selection_prop(owner,"setSelection:",request);apply_queued_selection(owner,editor,request);
    assert(editor->range.location==2 && editor->range.length==3);
}
static void native_geometry(void) {
    bridge_string=bridge;bounds_original=(IMP)original_bounds;
    id smile=attachment("https://static-cdn.jtvnw.net/emoticons/v2/1/static/dark/3.0"),image=fresh("UIImage");
    image->image_size=(Size){72,54};smile->image=image;
    Rect r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);
    assert(r.size.width==32 && r.size.height==24 && r.origin.y==-3);
    image->image_size=(Size){24,18};r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==32);
    id frown=attachment("https://static-cdn.jtvnw.net/emoticons/v2/2/static/dark/3.0");frown->image=image;
    r=attachment_bounds(frown,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==32);
    image->image_size=(Size){24,24};r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);
    smile->image=nil;r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);
    smile->image=image;image->image_size=(Size){72,54};r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==32); /* arrival on same attachment */
    const Size invalid[]={{0,54},{72,0},{NAN,54},{72,INFINITY},{-1,54},{1000,1}};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++){image->image_size=invalid[i];r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);}
    image->image_size=(Size){72,54};image->cls="OtherImage";r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);image->cls="UIImage";
    const char *urls[]={"https://example.com/emoticons/v2/1/static/dark/3.0","https://static-cdn.jtvnw.net/emoticons/v2/1junk/static/dark/3.0","https://static-cdn.jtvnw.net/emoticons/v2/0/static/dark/3.0","https://static-cdn.jtvnw.net/emoticons/v2/900000000000002/static/dark/3.0","https://static-cdn.jtvnw.net/emoticons/v2/860000000000125/static/dark/3.0","https://static-cdn.jtvnw.net/emoticons/v2/9000000001/static/dark/3.0"};
    for(unsigned i=0;i<sizeof(urls)/sizeof(*urls);i++){id foreign=attachment(urls[i]);foreign->image=image;r=attachment_bounds(foreign,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);}
    id other=fresh("NSTextAttachment");other->image=image;r=attachment_bounds(other,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);
    enabled=NO;r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);enabled=YES;
    is_main=NO;r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);is_main=YES;
    bridge_string=NULL;r=attachment_bounds(smile,"bounds",nil,(Rect){0},(Point){0},0);assert(r.size.width==24);
}
static void native_arrival(void) {
    tas_rn_composer_ui_retry_hooks();bridge_string=bridge;
    id owner=fresh(INPUT),editor=fresh("TwitchEmoteInputView"),source=fresh("NSAttributedString");owner->editor=editor;editor->value=source;editor->window=fresh("UIWindow");
    id a=attachment("https://static-cdn.jtvnw.net/emoticons/v2/9/static/dark/3.0"),image=fresh("UIImage");image->image_size=(Size){72,54};
    source->length=3;source->units[0]=source->units[2]=0xfffc;source->units[1]='x';source->items[0]=source->items[2]=a;
    sync(owner);assert(owners->count==1 && owners->items[0]==owner && !state(owner->target)->link && !copies);
    attachment_image(a,"setImage:",image);assert(a->image==image && assignments==1 && layout_invalidations==2 && GET(native_layouts)==2);
    id same=fresh("UIImage");same->image_size=(Size){24,18};attachment_image(a,"setImage:",same);assert(assignments==2 && layout_invalidations==2);
    id square=fresh("UIImage");square->image_size=(Size){24,24};attachment_image(a,"setImage:",square);assert(layout_invalidations==4);
    editor->window=nil;attachment_image(a,"setImage:",image);assert(layout_invalidations==4);
    editor->window=fresh("UIWindow");source->length=0;attachment_image(a,"setImage:",square);assert(layout_invalidations==4); /* removed */
    source->length=3;source->items[0]=source->items[2]=provider();attachment_image(a,"setImage:",image);assert(layout_invalidations==4); /* rebuilt */
    attachment_image(source->items[0],"setImage:",image);assert(layout_invalidations==4 && source->items[0]->image==image); /* providers untouched */
    enabled=NO;source->items[0]=source->items[2]=a;attachment_image(a,"setImage:",square);assert(layout_invalidations==4);enabled=YES;
    is_main=NO;attachment_image(a,"setImage:",image);assert(layout_invalidations==4);is_main=YES;
    source->length=4097;attachment_image(a,"setImage:",square);assert(layout_invalidations==4);
    source->length=3;assert(source->units[1]=='x' && !copies);owner_dealloc(owner,"dealloc");clock_dealloc(owner->target,"dealloc");
}
static void native_image_abi(void) {
    image_method.encoding="v16@0:8";tas_rn_composer_ui_retry_hooks();assert(bounds_original && !image_original);
    unsigned count=installed;image_method.encoding="v24@0:8@16";tas_rn_composer_ui_retry_hooks();assert(image_original==(IMP)original_image && installed==count+1);
    tas_rn_composer_ui_retry_hooks();assert(installed==count+1);
}
int main(int argc,char **argv) {
    if(argc==2 && !strcmp(argv[1],"detailkeyboard")){detail_keyboard();return 0;}
    assert(argc==2);
    if(!strcmp(argv[1],"webpmiss")){
        webp_mode=YES;frame_pending=YES;playback();
        for(unsigned i=0;i<pool_count;i++)free(pool[i]);return 0;
    }
    if(!strcmp(argv[1],"geometry"))geometry();else if(!strcmp(argv[1],"gif"))gif_gate();else if(!strcmp(argv[1],"playback"))playback();else if(!strcmp(argv[1],"webp")){webp_mode=YES;playback();}else if(!strcmp(argv[1],"install"))installation();else if(!strcmp(argv[1],"cold"))cold_start();else if(!strcmp(argv[1],"composition"))composition();else if(!strcmp(argv[1],"hits"))detail_hits();else if(!strcmp(argv[1],"safety"))detail_safety();else if(!strcmp(argv[1],"menus"))detail_menus();else if(!strcmp(argv[1],"abi"))detail_abi();else if(!strcmp(argv[1],"cursor"))cursor_race();else if(!strcmp(argv[1],"cursorabi"))cursor_abi();else if(!strcmp(argv[1],"latecursor"))late_cursor_prop();else if(!strcmp(argv[1],"latenative"))late_native_cursor();else if(!strcmp(argv[1],"nativegeometry"))native_geometry();else if(!strcmp(argv[1],"nativearrival"))native_arrival();else if(!strcmp(argv[1],"nativeimageabi"))native_image_abi();else abort();
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
        source=source.replace('#define ATTACHMENT', 'static Size test_size(id);\nstatic Point test_point(id,id);\nstatic Rect test_rect(id,Range,id);\nstatic Insets test_insets(id);\nstatic Range test_range(id);\n#define ATTACHMENT')
        source=source.replace('((Point (*)(id,SEL,id))objc_msgSend)(location,sel_registerName("locationInView:"),editor)', 'test_point(location,editor)')
        source=source.replace('((Insets (*)(id,SEL))objc_msgSend)(editor,sel_registerName("textContainerInset"))', 'test_insets(editor)')
        source=source.replace('((Rect (*)(id,SEL,Range,id))objc_msgSend)(manager,sel_registerName("boundingRectForGlyphRange:inTextContainer:"),(Range){glyph,1},container)', 'test_rect(manager,(Range){glyph,1},container)')
        source=source.replace('((Size (*)(id,SEL))objc_msgSend)(image,sel_registerName("size"))', 'test_size(image)')
        source=source.replace('((Range (*)(id,SEL))objc_msgSend)(item,sel_registerName("range"))', 'test_range(item)')
        from test_webp_animation import animation
        body=animation([100,100,12500])
        fixture='const unsigned char webp_fixture[]={'+','.join(str(b) for b in body)+'};const unsigned long webp_fixture_size=sizeof(webp_fixture);\n'
        (p/'composer.c').write_text(source);(p/'test.c').write_text(fixture+HARNESS);cls.binary=p/'test'
        zig=os.environ.get('ZIG') or shutil.which('zig');assert zig
        result=subprocess.run([zig,'cc','-fblocks','-Wall','-Wextra','-Werror','-Wno-cast-function-type-mismatch','-fsanitize=address,undefined','-ffunction-sections','-fdata-sections','-I',str(p),'-I',str(ROOT/'src'),str(p/'test.c'),'-Wl,--gc-sections','-pthread','-o',str(cls.binary)],capture_output=True,text=True)
        if result.returncode:raise AssertionError(result.stderr)
    def run_mode(self,mode):
        r=subprocess.run([self.binary,mode],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
        self.assertEqual(r.returncode,0,r.stderr)
    def test_native_height_baseline_wide_narrow_identity_bridge_and_fallback(self):self.run_mode('geometry')
    def test_gif_preflight_body_budget_complete_blocks_timing_and_transport_gate(self):self.run_mode('gif')
    def test_independent_clocks_reconciliation_ime_deletion_visibility_and_teardown(self):self.run_mode('playback')
    def test_webp_independent_clocks_long_hold_visibility_and_teardown(self):self.run_mode('webp')
    def test_webp_decode_miss_keeps_clock_and_retries_current_frame(self):self.run_mode('webpmiss')
    def test_exact_abi_preference_retry_and_idempotent_hooks(self):self.run_mode('install')
    def test_first_download_starts_original_attachment_without_retyping(self):self.run_mode('cold')
    def test_unconfirmed_prediction_and_ime_never_rebuild_or_replay_draft(self):self.run_mode('composition')

    def test_hold_admission_hit_bounds_native_text_ime_modal_and_priority(self):self.run_mode('hits')
    def test_info_sheet_ends_editing_before_presentation_and_preserves_vetoed_or_stale_inputs(self):self.run_mode('detailkeyboard')
    def test_deferred_details_live_identity_metadata_teardown_and_one_haptic(self):self.run_mode('safety')
    def test_provider_menu_suppression_and_original_native_fallback(self):self.run_mode('menus')

    def test_optional_menu_hooks_refuse_unknown_abi_and_retry_existing_methods(self):self.run_mode('abi')

    def test_accepted_edit_invalidates_queued_cursor_but_veto_and_fallback_do_not(self):self.run_mode('cursor')

    def test_cursor_guard_requires_both_selection_abis_and_retries(self):self.run_mode('cursorabi')

    def test_late_suggestion_cursor_prop_checks_live_draft_and_preserves_native_props(self):self.run_mode('latecursor')

    def test_late_native_selection_after_recognition_requires_its_original_draft(self):self.run_mode('latenative')

    def test_native_emoticon_image_aspect_arrival_scale_and_guarded_fallback(self):self.run_mode('nativegeometry')

    def test_native_cold_image_layout_only_for_live_identity_and_changed_aspect(self):self.run_mode('nativearrival')
    def test_native_image_setter_requires_exact_abi_and_installs_once(self):self.run_mode('nativeimageabi')
