#include "TASComposerTrace.h"
#if TAS_RN_COMPOSER_DIAGNOSTIC
#include "TASComposerTraceModel.h"
#include "TASDiagnosticPolicy.h"
#include "TASEmoteUI.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <pthread.h>
#include <time.h>
#include <stdlib.h>
typedef unsigned long U;
typedef struct {double x,y;} Point;
typedef struct {double width,height;} Size;
typedef struct {Point origin;Size size;} Rect;
typedef struct {U location,length;} Range;
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_getAssociatedObject(id,const void *);
extern void objc_setAssociatedObject(id,const void *,id,uintptr_t);
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static TASComposerRing ring;
static id observer,tracked;
static char editor_key,label_key,editor_identity_key;
static unsigned labels,editor_labels,watch_refused;
static Rect keyboard;
static BOOL keyboard_known;
static double active_until;
static unsigned js_pending;
static id m0(id o,const char *s){return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static id m1(id o,const char *s,id a){return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static id string(const char *s){return m1((id)objc_getClass("NSString"),"stringWithUTF8String:",(id)s);}
static BOOL yes(id o,const char *s){return ((BOOL (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static U integer(id o,const char *s){return ((U (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static BOOL kind(id o,const char *s){return o&&((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),objc_getClass(s));}
static BOOL responds(id o,const char *s){return o&&((BOOL (*)(id,SEL,SEL))objc_msgSend)(o,sel_registerName("respondsToSelector:"),sel_registerName(s));}
static BOOL enabled(void){return tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED);}
static uint64_t milliseconds(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static BOOL admit(uint64_t ms){pthread_mutex_lock(&lock);BOOL ok=tas_ct_budget(&ring,ms);pthread_mutex_unlock(&lock);return ok;}
static void store(TASComposerSample *s){pthread_mutex_lock(&lock);tas_ct_store(&ring,s);pthread_mutex_unlock(&lock);}
static void rect_values(int *out,Rect r){out[0]=tas_ct_number(r.origin.x);out[1]=tas_ct_number(r.origin.y);out[2]=tas_ct_number(r.size.width);out[3]=tas_ct_number(r.size.height);}
static Rect window_rect(id view,id window){
    Rect bounds=((Rect (*)(id,SEL))objc_msgSend)(view,sel_registerName("bounds"));
    return ((Rect (*)(id,SEL,Rect,id))objc_msgSend)(view,sel_registerName("convertRect:toView:"),bounds,window);
}
static Rect intersect(Rect a,Rect b){
    double x=fmax(a.origin.x,b.origin.x),y=fmax(a.origin.y,b.origin.y);
    return (Rect){{x,y},{fmax(0,fmin(a.origin.x+a.size.width,b.origin.x+b.size.width)-x),fmax(0,fmin(a.origin.y+a.size.height,b.origin.y+b.size.height)-y)}};
}
static int font_size(id font){return kind(font,"UIFont")?tas_ct_point_size(((double (*)(id,SEL))objc_msgSend)(font,sel_registerName("pointSize"))):-1;}
static uint32_t color_value(id color,id editor){
    if(!kind(color,"UIColor"))return 0;
    if(responds(color,"resolvedColorWithTraitCollection:"))color=m1(color,"resolvedColorWithTraitCollection:",m0(editor,"traitCollection"));
    double r=0,g=0,b=0,a=0;
    if(!((BOOL (*)(id,SEL,double *,double *,double *,double *))objc_msgSend)(color,sel_registerName("getRed:green:blue:alpha:"),&r,&g,&b,&a))return 0;
    if(!isfinite(r)||!isfinite(g)||!isfinite(b)||!isfinite(a))return 0;
    return ((uint32_t)(fmax(0,fmin(1,r))*255)<<24)|((uint32_t)(fmax(0,fmin(1,g))*255)<<16)|((uint32_t)(fmax(0,fmin(1,b))*255)<<8)|(uint32_t)(fmax(0,fmin(1,a))*255);
}
static id field(id owner,const char *name,const char *next,const char *cls,BOOL second){
    Ivar a=class_getInstanceVariable(object_getClass(owner),name),b=class_getInstanceVariable(object_getClass(owner),next);
    if(!a||!b)return nil;ptrdiff_t off=ivar_getOffset(a);
    if(off<0||ivar_getOffset(b)-off!=8||(size_t)off+8>class_getInstanceSize(object_getClass(owner)))return nil;
    if(second)off=ivar_getOffset(b);
    if((size_t)off+8>class_getInstanceSize(object_getClass(owner)))return nil;
    id value=nil;memcpy(&value,(char *)owner+off,8);return kind(value,cls)?value:nil;
}
static void attrs(id attributes,id editor,int *font,uint32_t *color){
    *font=-1;*color=0;if(!kind(attributes,"NSDictionary"))return;
    *font=font_size(m1(attributes,"objectForKey:",string("NSFont")));
    *color=color_value(m1(attributes,"objectForKey:",string("NSColor")),editor);
}
static void run(id text,U index,id editor,int *font,uint32_t *color,unsigned *flags,unsigned bit){
    id attributes=((id (*)(id,SEL,U,Range *))objc_msgSend)(text,sel_registerName("attributesAtIndex:effectiveRange:"),index,NULL);
    attrs(attributes,editor,font,color);
    id attachment=m1(attributes,"objectForKey:",string("NSAttachment"));
    if(attachment)*flags|=bit;
    if(kind(attachment,"_TtC21twitch_rn_emote_input21TwitchEmoteAttachment"))*flags|=bit<<2;
}
static void capture(id owner,id editor,unsigned event){
    TASComposerSample s={0};s.ms=milliseconds();s.event=event;
    if(!admit(s.ms))return;
    s.owner=(unsigned)integer(objc_getAssociatedObject(owner,&label_key),"unsignedIntValue");
    s.editor=(unsigned)integer(objc_getAssociatedObject(editor,&editor_identity_key),"unsignedIntValue");
    id window=m0(editor,"window");
    s.flags=(window?1U:0U)|(yes(editor,"isFirstResponder")?2U:0U)|(m0(editor,"markedTextRange")?4U:0U)|
        (tas_emote_ui_modal_visible(owner)?8U:0U)|(keyboard_known?16U:0U);
    Rect clip=window?((Rect (*)(id,SEL))objc_msgSend)(window,sel_registerName("bounds")):(Rect){0};
    id ancestor=editor;
    for(unsigned i=0;ancestor&&i<32;i++,ancestor=m0(ancestor,"superview")){
        Rect r=window?window_rect(ancestor,window):((Rect (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("bounds"));
        if(yes(ancestor,"isHidden")||((double (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("alpha"))<=0.01){s.flags|=32U;if(!s.hidden_depth)s.hidden_depth=i+1;}
        if(yes(ancestor,"clipsToBounds")){s.flags|=64U;clip=intersect(clip,r);}
        s.depth=i+1;
    }
    rect_values(s.ancestor,clip);
    if(ancestor)s.flags|=128U;
    if(window){Rect r=window_rect(editor,window);rect_values(s.rect,r);Rect bounds=((Rect (*)(id,SEL))objc_msgSend)(window,sel_registerName("bounds"));s.window[0]=tas_ct_number(bounds.size.width);s.window[1]=tas_ct_number(bounds.size.height);
        Rect converted=((Rect (*)(id,SEL,Rect,id))objc_msgSend)(window,sel_registerName("convertRect:fromWindow:"),keyboard,nil);rect_values(s.keyboard,converted);}
    id text=m0(editor,"attributedText");U length=integer(text,"length");s.length=(unsigned)(length>4096?4097:length);
    Range selection=((Range (*)(id,SEL))objc_msgSend)(editor,sel_registerName("selectedRange"));
    s.selection=(unsigned)(selection.location>4096?4097:selection.location);s.selection_length=(unsigned)(selection.length>4096?4097:selection.length);
    attrs(m0(editor,"typingAttributes"),editor,&s.font,&s.color);
    id typing=m0(editor,"typingAttributes");
    if(kind(m1(typing,"objectForKey:",string("NSFont")),"UIFont"))s.flags|=256U;
    if(kind(m1(typing,"objectForKey:",string("NSColor")),"UIColor"))s.flags|=512U;
    s.base_font=font_size(m0(editor,"font"));s.base_color=color_value(m0(editor,"textColor"),editor);
    s.resolved_font=font_size(field(owner,"resolvedFont","resolvedTextColor","UIFont",NO));
    s.resolved_color=color_value(field(owner,"resolvedFont","resolvedTextColor","UIColor",YES),editor);
    s.run_before_font=s.run_after_font=-1;
    if(length<=4096&&selection.location<=length&&!(s.flags&4U)){
        if(selection.location)run(text,selection.location-1,editor,&s.run_before_font,&s.run_before_color,&s.adjacent,1U);
        if(selection.location<length)run(text,selection.location,editor,&s.run_after_font,&s.run_after_color,&s.adjacent,2U);
    }
    store(&s);
}
static void all(unsigned event){
    id list=m0(tracked,"allObjects");U n=integer(list,"count");
    for(U i=0;i<n&&i<8;i++){
        id owner=((id (*)(id,SEL,U))objc_msgSend)(list,sel_registerName("objectAtIndex:"),i);
        id editor=objc_getAssociatedObject(owner,&editor_key);if(editor)capture(owner,editor,event);
    }
}
static void poll(id self,SEL command,id timer){(void)self;(void)command;(void)timer;if(enabled()&&(double)milliseconds()/1000<=active_until)all(TAS_CT_POLL);}
static void keyboard_event(id self,SEL command,id note){
    (void)self;(void)command;if(!enabled())return;
    id info=m0(note,"userInfo"),value=m1(info,"objectForKey:",string("UIKeyboardFrameEndUserInfoKey"));
    if(responds(value,"CGRectValue")){keyboard=((Rect (*)(id,SEL))objc_msgSend)(value,sel_registerName("CGRectValue"));keyboard_known=YES;}
    active_until=(double)milliseconds()/1000+15;all(TAS_CT_KEYBOARD);
}
static void start(void){
    if(observer)return;
    Class cls=objc_allocateClassPair(objc_getClass("NSObject"),"StreamsideComposerTraceObserver",0);
    if(!cls||!class_addMethod(cls,sel_registerName("tick:"),(IMP)poll,"v24@0:8@16")||!class_addMethod(cls,sel_registerName("keyboard:"),(IMP)keyboard_event,"v24@0:8@16"))return;
    objc_registerClassPair(cls);observer=m0((id)cls,"new");
    tracked=objc_retain(m0((id)objc_getClass("NSHashTable"),"weakObjectsHashTable"));
    id center=m0((id)objc_getClass("NSNotificationCenter"),"defaultCenter");
    const char *names[]={"UIKeyboardWillChangeFrameNotification","UIKeyboardDidChangeFrameNotification","UIKeyboardWillHideNotification","UIKeyboardDidHideNotification"};
    for(unsigned i=0;i<4;i++)((void (*)(id,SEL,id,SEL,id,id))objc_msgSend)(center,sel_registerName("addObserver:selector:name:object:"),observer,sel_registerName("keyboard:"),string(names[i]),nil);
    id timer=((id (*)(id,SEL,double,id,SEL,id,BOOL))objc_msgSend)((id)objc_getClass("NSTimer"),sel_registerName("timerWithTimeInterval:target:selector:userInfo:repeats:"),0.25,observer,sel_registerName("tick:"),nil,YES);
    ((void (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSRunLoop"),"mainRunLoop"),sel_registerName("addTimer:forMode:"),timer,string("kCFRunLoopCommonModes"));
}
void tas_composer_trace_native(id owner,id editor,unsigned event){
    if(!enabled()||!yes((id)objc_getClass("NSThread"),"isMainThread")||
       !kind(owner,"_TtC21twitch_rn_emote_input20TwitchEmoteInputView")||!kind(editor,"UITextView"))return;
    start();if(!tracked)return;
    if(!objc_getAssociatedObject(owner,&label_key)){
        if(integer(tracked,"count")>=8){watch_refused++;return;}
        id number=((id (*)(id,SEL,unsigned))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithUnsignedInt:"),++labels);
        objc_setAssociatedObject(owner,&label_key,number,1);
        ((void (*)(id,SEL,id))objc_msgSend)(tracked,sel_registerName("addObject:"),owner);
    }
    objc_setAssociatedObject(owner,&editor_key,editor,1);
    if(!objc_getAssociatedObject(editor,&editor_identity_key)){
        id number=((id (*)(id,SEL,unsigned))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithUnsignedInt:"),++editor_labels);
        objc_setAssociatedObject(editor,&editor_identity_key,number,1);
    }
    if(event!=TAS_CT_LAYOUT)active_until=(double)milliseconds()/1000+15;
    capture(owner,editor,event);
}
void tas_composer_trace_js(unsigned event,unsigned session,double x,double y,double w,double h){
    if(!enabled()||event<20||event>24||!session||session>100000||!isfinite(x)||!isfinite(y)||!isfinite(w)||!isfinite(h))return;
    TASComposerSample s={0};s.ms=milliseconds();if(!admit(s.ms))return;
    s.event=event;s.session=session;rect_values(s.rect,(Rect){{x,y},{w,h}});store(&s);
    if(__atomic_exchange_n(&js_pending,1,__ATOMIC_ACQ_REL))return;
    ((void (*)(id,SEL,id))objc_msgSend)(m0((id)objc_getClass("NSOperationQueue"),"mainQueue"),sel_registerName("addOperationWithBlock:"),(id)^{
        __atomic_store_n(&js_pending,0,__ATOMIC_RELEASE);
        if(enabled()){active_until=(double)milliseconds()/1000+15;all(TAS_CT_POLL);}
    });
}
void tas_composer_trace_report(char *b,size_t cap){
    if(!b||!cap)return;
    if(!enabled()){snprintf(b,cap,"RN composer trace compiled; collection disabled (requires Composer / Picker + Detailed at launch).\n");return;}
    pthread_mutex_lock(&lock);tas_ct_report(&ring,b,cap);pthread_mutex_unlock(&lock);
    size_t used=strlen(b);if(used+100<cap)snprintf(b+used,cap-used,"Trace watch refused=%u; observer=%s. Event/flag legend: RN_COMPOSER_DIAGNOSTICS.md\n",watch_refused,observer?"installed":"not started");
}
void tas_composer_trace_clear(void){pthread_mutex_lock(&lock);memset(&ring,0,sizeof(ring));pthread_mutex_unlock(&lock);}
void tas_composer_trace_sheet_closed(void){
    if(!enabled()||!yes((id)objc_getClass("NSThread"),"isMainThread"))return;
    active_until=(double)milliseconds()/1000+15;all(TAS_CT_SHEET_CLOSED);
}
#endif
