/* Twitch 31.5 RN input presentation only. Never replace text storage, delegate,
 * send callbacks, selection, tokenization, marked text or the native image cache. */
#include "TASRNComposerUI.h"
#include "TASRNComposerModel.h"
#include "TASEmotes.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

typedef unsigned long U;
typedef struct {double x,y;} Point;
typedef struct {double width,height;} Size;
typedef struct {Point origin;Size size;} Rect;
typedef struct {U location,length;} Range;
#define ATTACHMENT "_TtC21twitch_rn_emote_input21TwitchEmoteAttachment"
#define INPUT "_TtC21twitch_rn_emote_input20TwitchEmoteInputView"
#define MAX_FRAMES 128
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_initWeak(id *,id);
extern id objc_loadWeakRetained(id *);
extern void objc_destroyWeak(id *);
extern id objc_getAssociatedObject(id,const void *);
extern void objc_setAssociatedObject(id,const void *,id,uintptr_t);
typedef id (__attribute__((swiftcall)) *StringBridge)(uint64_t,uint64_t);
static StringBridge bridge_string;
static IMP bounds_original,layout_original,change_original,selection_original,move_original,value_original,dealloc_original,target_dealloc;
static Class clock_class;
static ptrdiff_t clock_offset;
static id image_bytes,owners;
static char identity_key,state_key;
static pthread_mutex_t install_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t bounds_calls,sized,syncs,decoders,advances,ticks,refused,images;
#define INC(v) ((void)__atomic_add_fetch(&(v),1,__ATOMIC_RELAXED))
#define GET(v) __atomic_load_n(&(v),__ATOMIC_RELAXED)
static id m0(id o,const char *s){return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static id m1(id o,const char *s,id a){return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static void v1(id o,const char *s,id a){((void (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static U integer(id o,const char *s){return ((U (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static BOOL yes(id o,const char *s){return ((BOOL (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static BOOL main_thread(void){return yes((id)objc_getClass("NSThread"),"isMainThread");}
static BOOL kind(id o,const char *s){Class c=objc_getClass(s);return o && c && ((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),c);}
static id str(const char *s){return m1((id)objc_getClass("NSString"),"stringWithUTF8String:",(id)s);}
static const char *utf8(id s){return ((const char *(*)(id,SEL))objc_msgSend)(s,sel_registerName("UTF8String"));}
static id num(uint64_t n){return ((id (*)(id,SEL,uint64_t))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithUnsignedLongLong:"),n);}
static void associate(id o,const void *key,id value){objc_setAssociatedObject(o,key,value,1);}

/* The exact donor stores url as a 16-byte Swift String, immediately before
 * loaded. Its Foundation bridge is imported and called with x0/x1 at 0x4734.
 * Resolve offsets and bridge at runtime; never reinterpret a Swift String as id. */
static uint64_t attachment_number(id attachment) {
    if (!main_thread() || !kind(attachment,ATTACHMENT) || !bridge_string) return 0;
    id cached=objc_getAssociatedObject(attachment,&identity_key);
    if (cached) return integer(cached,"unsignedLongLongValue");
    Class cls=object_getClass(attachment);
    Ivar url=class_getInstanceVariable(cls,"url"),loaded=class_getInstanceVariable(cls,"loaded");
    if (!url || !loaded) return 0;
    ptrdiff_t offset=ivar_getOffset(url),end=ivar_getOffset(loaded);
    if (offset<0 || end-offset!=16 || (size_t)end>=class_getInstanceSize(cls)) return 0;
    uint64_t words[2];memcpy(words,(char *)attachment+offset,sizeof(words));
    if (!words[1]) return 0;
    id string=bridge_string(words[0],words[1]);
    const char *value=kind(string,"NSString") ? utf8(string) : NULL;
    const char *prefix="https://static-cdn.jtvnw.net/emoticons/v2/";
    uint64_t number=0;
    if (value && !strncmp(value,prefix,strlen(prefix))) {
        const char *digits=value+strlen(prefix);char *tail;
        if (digits[0]=='9') {number=strtoull(digits,&tail,10);if(tail==digits || *tail!='/' || tail-digits>20)number=0;}
    }
    objc_release(string);
    id metadata=number ? tas_emotes_metadata_copy(number) : nil;
    if (!metadata) number=0;
    objc_release(metadata);
    /* Remember native/unknown identities as zero, too; no repeated bridging. */
    associate(attachment,&identity_key,num(number));
    return number;
}
static id editor_for(id owner) {
    if (!kind(owner,INPUT)) return nil;
    Class cls=object_getClass(owner);
    Ivar field=class_getInstanceVariable(cls,"textView"),next=class_getInstanceVariable(cls,"emoteMapDict");
    if (!field || !next || ivar_getOffset(next)-ivar_getOffset(field)!=(ptrdiff_t)sizeof(id)) return nil;
    id editor=nil;memcpy(&editor,(char *)owner+ivar_getOffset(field),sizeof(editor));
    return kind(editor,"TwitchEmoteInputView") && kind(editor,"UITextView") ? editor : nil;
}
static Rect attachment_bounds(id self,SEL command,id container,Rect fragment,Point position,U index) {
    Rect result=((Rect (*)(id,SEL,id,Rect,Point,U))bounds_original)(self,command,container,fragment,position,index);
    INC(bounds_calls);
    uint64_t number=tas_emotes_enabled_this_launch() ? attachment_number(self) : 0;
    double aspect=number ? tas_emotes_aspect(number) : 0;
    if (isfinite(aspect) && aspect>0 && aspect<=20 && isfinite(result.size.height) && result.size.height>0) {
        result.size.width=result.size.height*aspect;INC(sized);
    }
    return result; /* Preserve native baseline, height and paragraph styling. */
}
static void cache_init(void) {
    if (image_bytes) return;
    image_bytes=m0((id)objc_getClass("NSCache"),"new");
    ((void (*)(id,SEL,U))objc_msgSend)(image_bytes,sel_registerName("setCountLimit:"),128);
    ((void (*)(id,SEL,U))objc_msgSend)(image_bytes,sel_registerName("setTotalCostLimit:"),8*1024*1024);
}
static void sync_owners(void);
void tas_rn_composer_ui_image(uint64_t number,id data,id response,id error) {
    if (!tas_emotes_enabled_this_launch() || error || !data || !response) return;
    U status=integer(response,"statusCode"),length=integer(data,"length");
    if (status<200 || status>=300 || !length || length>2*1024*1024) return;
    const unsigned char *bytes=((const unsigned char *(*)(id,SEL))objc_msgSend)(data,sel_registerName("bytes"));
    if (!tas_rn_composer_gif(bytes,length)) return;
    id held=objc_retain(data);
    ((void (*)(id,SEL,id))objc_msgSend)(m0((id)objc_getClass("NSOperationQueue"),"mainQueue"),sel_registerName("addOperationWithBlock:"),(id)^{
        cache_init();
        ((void (*)(id,SEL,id,id,U))objc_msgSend)(image_bytes,sel_registerName("setObject:forKey:cost:"),held,num(number),length);
        INC(images);sync_owners();objc_release(held);
    });
}
typedef struct {id attachment,animation;U location,index,cost;double elapsed;} Frame;
typedef struct {id owner,link;double timestamp;U count;Frame frames[MAX_FRAMES];} State;
static State *state(id target){State *s=NULL;if(target)memcpy(&s,(char *)target+clock_offset,sizeof(s));return s;}
static void clear_frames(State *s) {
    for(U i=0;i<s->count;i++){objc_release(s->frames[i].attachment);objc_release(s->frames[i].animation);}
    s->count=0;
}
static void stop(State *s){id link=s->link;s->link=nil;s->timestamp=0;m0(link,"invalidate");objc_release(link);}
static void clock_dealloc(id self,SEL command){State *s=state(self);if(s){stop(s);clear_frames(s);objc_destroyWeak(&s->owner);free(s);}((void (*)(id,SEL))target_dealloc)(self,command);}
static BOOL visible(id editor) {
    if (!editor || !m0(editor,"window") || integer(m0((id)objc_getClass("UIApplication"),"sharedApplication"),"applicationState")) return NO;
    id ancestor=editor;
    for(unsigned depth=0;ancestor && depth<64;depth++,ancestor=m0(ancestor,"superview"))
        if(yes(ancestor,"isHidden") || ((double (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("alpha"))<=0)return NO;
    return ancestor==nil;
}
static id attachment_at(id source,U location){return ((id (*)(id,SEL,id,U,Range *))objc_msgSend)(source,sel_registerName("attribute:atIndex:effectiveRange:"),str("NSAttachment"),location,NULL);}
static double delay_at(Frame *f) {
    id value=m1(m0(f->animation,"delayTimesForIndexes"),"objectForKey:",num(f->index));
    return tas_rn_composer_delay(((double (*)(id,SEL))objc_msgSend)(value,sel_registerName("doubleValue")));
}
static void animate(id self,SEL command,id link) {
    (void)command;objc_retain(self);State *s=state(self);
    if(!s || link!=s->link){objc_release(self);return;}
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if(!tas_emotes_enabled_this_launch() || !visible(editor)){stop(s);objc_release(owner);objc_release(self);return;}
    INC(ticks);
    double now=((double (*)(id,SEL))objc_msgSend)(link,sel_registerName("timestamp"));
    double delta=tas_rn_composer_delta(now,s->timestamp);s->timestamp=now;
    if(!delta || m0(editor,"markedTextRange")){objc_release(owner);objc_release(self);return;}
    id source=m0(editor,"attributedText"),manager=m0(editor,"layoutManager");U length=integer(source,"length"),live=0;
    for(U i=0;i<s->count;i++) {
        Frame *f=&s->frames[i];
        if(f->location>=length || attachment_at(source,f->location)!=f->attachment)continue;
        live++;f->elapsed+=delta;double delay=delay_at(f);BOOL changed=NO;U count=integer(f->animation,"frameCount");
        if(count<2 || count>300)continue;
        for(unsigned step=0;f->elapsed>=delay && step<16;step++) {
            U next=(f->index+1)%count;
            id image=((id (*)(id,SEL,U))objc_msgSend)(f->animation,sel_registerName("imageLazilyCachedAtIndex:"),next);
            if(!image){f->elapsed=delay;break;}
            f->elapsed-=delay;f->index=next;v1(f->attachment,"setImage:",image);changed=YES;INC(advances);delay=delay_at(f);
        }
        if(changed)((void (*)(id,SEL,Range))objc_msgSend)(manager,sel_registerName("invalidateDisplayForCharacterRange:"),(Range){f->location,1});
    }
    if(!live){stop(s);clear_frames(s);}
    objc_release(owner);objc_release(self);
}
static void sync(id owner) {
    if(!tas_emotes_enabled_this_launch() || !main_thread() || !clock_class)return;
    INC(syncs);id editor=editor_for(owner);
    id target=objc_getAssociatedObject(owner,&state_key);State *s=target ? state(target) : NULL;
    if(!visible(editor)){if(s)stop(s);return;}
    if(m0(editor,"markedTextRange"))return;
    id source=m0(editor,"attributedText");U length=integer(source,"length");
    if(length>4096){if(s){stop(s);clear_frames(s);}INC(refused);return;}
    Frame frames[MAX_FRAMES];U n=0,total_cost=0;id string=m0(source,"string");
    for(U i=0;i<length && n<MAX_FRAMES;i++) {
        if(((uint16_t (*)(id,SEL,U))objc_msgSend)(string,sel_registerName("characterAtIndex:"),i)!=0xfffc)continue;
        id attachment=attachment_at(source,i);uint64_t number=attachment_number(attachment);
        if(!number)continue;
        BOOL duplicate=NO;for(U j=0;j<n;j++)if(frames[j].attachment==attachment)duplicate=YES;
        if(duplicate)continue;
        Frame f={.attachment=attachment,.location=i};
        if(s)for(U j=0;j<s->count;j++)if(s->frames[j].attachment==attachment){f=s->frames[j];f.location=i;break;}
        if(!f.animation) {
            id data=m1(image_bytes,"objectForKey:",num(number));
            if(!data || !objc_getClass("FLAnimatedImage"))continue;
            U bytes=integer(data,"length");
            const unsigned char *p=((const unsigned char *(*)(id,SEL))objc_msgSend)(data,sel_registerName("bytes"));
            if(bytes<10 || !p)continue;
            /* Four lazily cached RGBA frames plus poster and encoded bytes.
             * Repeated attachments have independent decoders, so bound their
             * combined working set rather than just the shared byte cache. */
            U width=p[6]|p[7]<<8,height=p[8]|p[9]<<8;
            f.cost=width*height*4*5+bytes;
            if(f.cost>16*1024*1024-total_cost){INC(refused);continue;}
            f.animation=m1(m0((id)objc_getClass("FLAnimatedImage"),"alloc"),"initWithAnimatedGIFData:",data);
            U count=integer(f.animation,"frameCount");
            if(count<2 || count>300){objc_release(f.animation);INC(refused);continue;}
            ((void (*)(id,SEL,U))objc_msgSend)(f.animation,sel_registerName("setFrameCacheSizeMax:"),4);
            f.index=integer(f.animation,"posterImageFrameIndex");INC(decoders);
        } else {
            if(f.cost>16*1024*1024-total_cost){INC(refused);continue;}
            objc_retain(f.animation);
        }
        total_cost+=f.cost;
        objc_retain(f.attachment);frames[n++]=f;
    }
    if(!s && n) {
        if(!owners)owners=objc_retain(m0((id)objc_getClass("NSHashTable"),"weakObjectsHashTable"));
        if(integer(owners,"count")>=8){for(U i=0;i<n;i++){objc_release(frames[i].attachment);objc_release(frames[i].animation);}INC(refused);return;}
        target=m0((id)clock_class,"new");s=calloc(1,sizeof(*s));
        if(s && target){objc_initWeak(&s->owner,owner);memcpy((char *)target+clock_offset,&s,sizeof(s));associate(owner,&state_key,target);v1(owners,"addObject:",owner);}
        else {free(s);s=NULL;}
        objc_release(target);
    }
    if(!s){for(U i=0;i<n;i++){objc_release(frames[i].attachment);objc_release(frames[i].animation);}return;}
    clear_frames(s);memcpy(s->frames,frames,n*sizeof(*frames));s->count=n;
    if(!n){stop(s);return;}
    if(!s->link) {
        id link=((id (*)(id,SEL,id,SEL))objc_msgSend)((id)objc_getClass("CADisplayLink"),sel_registerName("displayLinkWithTarget:selector:"),target,sel_registerName("ssTick:"));
        s->link=objc_retain(link);s->timestamp=0;
        ((void (*)(id,SEL,U))objc_msgSend)(link,sel_registerName("setPreferredFramesPerSecond:"),30);
        ((void (*)(id,SEL,id,id))objc_msgSend)(link,sel_registerName("addToRunLoop:forMode:"),m0((id)objc_getClass("NSRunLoop"),"mainRunLoop"),str("kCFRunLoopCommonModes"));
    }
}
static void sync_owners(void) {
    if(!main_thread())return;
    id list=m0(owners,"allObjects");U count=integer(list,"count");
    for(U i=0;i<count && i<8;i++) {
        id owner=((id (*)(id,SEL,U))objc_msgSend)(list,sel_registerName("objectAtIndex:"),i);
        State *s=state(objc_getAssociatedObject(owner,&state_key));
        if(s)s->timestamp=0; /* Do not replay hidden/background or download time. */
        sync(owner);
    }
}
static void layout(id self,SEL command){((void (*)(id,SEL))layout_original)(self,command);sync(self);}
static void changed(id self,SEL command,id editor){((void (*)(id,SEL,id))change_original)(self,command,editor);sync(self);}
static void selection(id self,SEL command,id editor){((void (*)(id,SEL,id))selection_original)(self,command,editor);sync(self);}
static void moved(id self,SEL command){((void (*)(id,SEL))move_original)(self,command);sync(self);}
static void value(id self,SEL command,id text){((void (*)(id,SEL,id))value_original)(self,command,text);sync(self);}
static void owner_dealloc(id self,SEL command){id target=objc_getAssociatedObject(self,&state_key);if(target){State *s=state(target);if(s){stop(s);clear_frames(s);}}((void (*)(id,SEL))dealloc_original)(self,command);}
static void install(Class cls,const char *selector,const char *encoding,IMP replacement,IMP *original) {
    if(!cls || *original)return;Method method=class_getInstanceMethod(cls,sel_registerName(selector));
    if(!method || strcmp(method_getTypeEncoding(method),encoding))return;
    *original=method_getImplementation(method);
    if(!class_addMethod(cls,sel_registerName(selector),replacement,encoding))method_setImplementation(method,replacement);
}
void tas_rn_composer_ui_retry_hooks(void) {
    if(!tas_emotes_enabled_this_launch())return;
    pthread_mutex_lock(&install_lock);
    if(!bridge_string)bridge_string=(StringBridge)dlsym(RTLD_DEFAULT,"$sSS10FoundationE19_bridgeToObjectiveCSo8NSStringCyF");
    if(!clock_class && objc_getClass("NSObject")) {
        Class cls=objc_allocateClassPair(objc_getClass("NSObject"),"StreamsideRNPreviewClock",0);
        if(cls && class_addIvar(cls,"_state",sizeof(State *),3,"^v") &&
            class_addMethod(cls,sel_registerName("ssTick:"),(IMP)animate,"v24@0:8@16") &&
            class_addMethod(cls,sel_registerName("dealloc"),(IMP)clock_dealloc,"v16@0:8")) {
            target_dealloc=class_getMethodImplementation(objc_getClass("NSObject"),sel_registerName("dealloc"));
            objc_registerClassPair(cls);clock_class=cls;clock_offset=ivar_getOffset(class_getInstanceVariable(cls,"_state"));
        } else if(cls)objc_disposeClassPair(cls);
    }
    Class attachment=objc_getClass(ATTACHMENT),input=objc_getClass(INPUT);
    install(attachment,"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:","{CGRect={CGPoint=dd}{CGSize=dd}}80@0:8@16{CGRect={CGPoint=dd}{CGSize=dd}}24{CGPoint=dd}56q72",(IMP)attachment_bounds,&bounds_original);
    install(input,"layoutSubviews","v16@0:8",(IMP)layout,&layout_original);
    install(input,"textViewDidChange:","v24@0:8@16",(IMP)changed,&change_original);
    install(input,"textViewDidChangeSelection:","v24@0:8@16",(IMP)selection,&selection_original);
    install(input,"didMoveToWindow","v16@0:8",(IMP)moved,&move_original);
    install(input,"setValue:","v24@0:8@16",(IMP)value,&value_original);
    install(input,"dealloc","v16@0:8",(IMP)owner_dealloc,&dealloc_original);
    pthread_mutex_unlock(&install_lock);
    /* The existing launch/foreground observer retries these hooks. */
    sync_owners();
}
void tas_rn_composer_ui_status(char *buffer,size_t capacity) {
    if(!buffer || !capacity)return;
    snprintf(buffer,capacity,"\nRN native input previews (this launch)\n"
        "Hooks (bounds/layout/change/selection/window/value/dealloc)/String bridge: %s/%s/%s/%s/%s/%s/%s/%s\n"
        "Bounds/sizes/syncs/GIF bodies/decoders/ticks/advances/refused: %llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu\n",
        bounds_original ? "installed":"missing",layout_original ? "installed":"missing",change_original ? "installed":"missing",
        selection_original ? "installed":"missing",move_original ? "installed":"missing",value_original ? "installed":"missing",
        dealloc_original ? "installed":"missing",bridge_string ? "available":"missing",
        (unsigned long long)GET(bounds_calls),(unsigned long long)GET(sized),(unsigned long long)GET(syncs),(unsigned long long)GET(images),
        (unsigned long long)GET(decoders),(unsigned long long)GET(ticks),(unsigned long long)GET(advances),(unsigned long long)GET(refused));
}
