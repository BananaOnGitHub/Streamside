/* Inspected Twitch 31.5/31.6 RN input presentation, composition and cursor admission. UIKit owns
 * marked text; Twitch keeps text storage, selection, tokenization and sending. */
#include "TASRNComposerUI.h"
#include "TASRNComposerModel.h"
#include "TASEmotes.h"
#include "TASEmoteUI.h"
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
typedef struct {double top,left,bottom,right;} Insets;
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
static IMP bounds_original,layout_original,change_original,selection_original,move_original,value_original,map_original,dealloc_original,target_dealloc;
static IMP item_menu_original,interaction_original;
static IMP edit_original,selection_setter;
static IMP image_original;
static BOOL item_menu_installed,interaction_installed;
static Class clock_class;
static ptrdiff_t clock_offset;
static id image_bytes,owners;
static char identity_key,native_image_key,state_key,pending_map_key;
static pthread_mutex_t install_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t bounds_calls,sized,syncs,decoders,advances,ticks,refused,images,provisional;
static uint64_t details_holds;
static uint64_t selection_invalidations;
static uint64_t stale_selections;
static uint64_t native_sized;
static uint64_t native_layouts;
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
        if(digits[0]>='1' && digits[0]<='9') {
            uint64_t candidate=strtoull(digits,&tail,10);
            if(tail!=digits && *tail=='/' && tail-digits<=20) {
                /* Classic Twitch numeric IDs precede Streamside's earliest
                 * synthetic reservation. Never treat an unknown synthetic
                 * provider or transcript-width alias as a native image. */
                if(candidate<9000000000ULL)associate(attachment,&native_image_key,num(candidate));
                if(digits[0]=='9')number=candidate;
            }
        }
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
static double native_image_aspect(id image) {
    if(!kind(image,"UIImage"))return 0;
    Size size=((Size (*)(id,SEL))objc_msgSend)(image,sel_registerName("size"));
    if(!isfinite(size.width) || !isfinite(size.height) || size.width<=0 || size.height<=0)return 0;
    double ratio=size.width/size.height;
    return isfinite(ratio) && ratio>0 && ratio<=20 ? ratio : 0;
}
static void native_geometry_changed(id attachment);
static void attachment_image(id self,SEL command,id image) {
    BOOL native=bounds_original && tas_emotes_enabled_this_launch() && main_thread() && bridge_string && kind(self,ATTACHMENT);
    if(native){attachment_number(self);native=objc_getAssociatedObject(self,&native_image_key)!=nil;}
    double before=native ? native_image_aspect(m0(self,"image")) : 0;
    ((void (*)(id,SEL,id))image_original)(self,command,image);
    /* The donor invalidates display only after a cold download. Changing the
     * aspect also requires new glyph layout, without rebuilding the draft. */
    if(native && before!=native_image_aspect(image))native_geometry_changed(self);
}
static Rect attachment_bounds(id self,SEL command,id container,Rect fragment,Point position,U index) {
    Rect result=((Rect (*)(id,SEL,id,Rect,Point,U))bounds_original)(self,command,container,fragment,position,index);
    INC(bounds_calls);
    uint64_t number=tas_emotes_enabled_this_launch() ? attachment_number(self) : 0;
    double aspect=number ? tas_emotes_aspect(number) : 0;
    if (isfinite(aspect) && aspect>0 && aspect<=20 && isfinite(result.size.height) && result.size.height>0) {
        result.size.width=result.size.height*aspect;INC(sized);
    } else if(!number && tas_emotes_enabled_this_launch() && main_thread() && bridge_string &&
        objc_getAssociatedObject(self,&native_image_key) && isfinite(result.size.height) && result.size.height>0) {
        double ratio=native_image_aspect(m0(self,"image")),width=result.size.height*ratio;
        if(ratio>0 && isfinite(width) && width>0 && width!=result.size.width) {
            result.size.width=width;INC(native_sized);
        }
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
typedef struct {id owner,link,hold,details_attachment;BOOL hold_touch;double timestamp;U count;Frame frames[MAX_FRAMES];} State;
static State *state(id target){State *s=NULL;if(target)memcpy(&s,(char *)target+clock_offset,sizeof(s));return s;}
static void clear_frames(State *s) {
    for(U i=0;i<s->count;i++){objc_release(s->frames[i].attachment);objc_release(s->frames[i].animation);}
    s->count=0;
}
static void stop(State *s){id link=s->link;s->link=nil;s->timestamp=0;m0(link,"invalidate");objc_release(link);}
static void clear_hold(State *s) {
    v1(m0(s->hold,"view"),"removeGestureRecognizer:",s->hold);
    v1(s->hold,"setDelegate:",nil);objc_release(s->hold);s->hold=nil;s->hold_touch=NO;
    objc_release(s->details_attachment);s->details_attachment=nil;
}
static void clock_dealloc(id self,SEL command){State *s=state(self);if(s){stop(s);clear_frames(s);clear_hold(s);objc_destroyWeak(&s->owner);free(s);}((void (*)(id,SEL))target_dealloc)(self,command);}
static BOOL visible(id editor) {
    if (!editor || !m0(editor,"window") || integer(m0((id)objc_getClass("UIApplication"),"sharedApplication"),"applicationState")) return NO;
    id ancestor=editor;
    for(unsigned depth=0;ancestor && depth<64;depth++,ancestor=m0(ancestor,"superview"))
        if(yes(ancestor,"isHidden") || ((double (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("alpha"))<=0)return NO;
    return ancestor==nil;
}
static id attachment_at(id source,U location){return ((id (*)(id,SEL,id,U,Range *))objc_msgSend)(source,sel_registerName("attribute:atIndex:effectiveRange:"),str("NSAttachment"),location,NULL);}
static void native_geometry_changed(id attachment) {
    id list=m0(owners,"allObjects");U count=integer(list,"count");
    for(U n=0;n<count && n<8;n++) {
        id owner=((id (*)(id,SEL,U))objc_msgSend)(list,sel_registerName("objectAtIndex:"),n),editor=editor_for(owner);
        if(!visible(editor))continue;
        id source=m0(editor,"attributedText");U length=integer(source,"length");
        if(length>4096)continue;
        for(U i=0;i<length;i++)if(attachment_at(source,i)==attachment) {
            ((void (*)(id,SEL,Range,Range *))objc_msgSend)(m0(editor,"layoutManager"),sel_registerName("invalidateLayoutForCharacterRange:actualCharacterRange:"),(Range){i,1},NULL);
            INC(native_layouts);
        }
    }
}
/* Read the live attributed text, never a draft string or arbitrary image.
 * Suppress UIKit menus only when our recognizer is attached to this editor. */
static BOOL owned_attachment_at(id owner,id editor,id attachment,Range range) {
    State *s=state(objc_getAssociatedObject(owner,&state_key));
    if(!tas_emotes_enabled_this_launch() || !main_thread() || !s || !s->hold ||
        editor!=editor_for(owner) || m0(s->hold,"view")!=editor || !visible(editor) ||
        m0(editor,"markedTextRange") || !attachment || range.length!=1)return NO;
    id source=m0(editor,"attributedText");U length=integer(source,"length");
    return length<=4096 && range.location<length &&
        ((uint16_t (*)(id,SEL,U))objc_msgSend)(m0(source,"string"),sel_registerName("characterAtIndex:"),range.location)==0xfffc &&
        attachment_at(source,range.location)==attachment && attachment_number(attachment)!=0;
}
static id attachment_at_point(id target,id gesture,id location,Range *range) {
    State *s=state(target);if(!s || gesture!=s->hold)return nil;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner),attachment=nil;
    if(editor && m0(gesture,"view")==editor && visible(editor) && !m0(editor,"markedTextRange") &&
        !tas_emote_ui_modal_visible(owner)) {
        Point point=((Point (*)(id,SEL,id))objc_msgSend)(location,sel_registerName("locationInView:"),editor);
        Insets inset=((Insets (*)(id,SEL))objc_msgSend)(editor,sel_registerName("textContainerInset"));
        point.x-=inset.left;point.y-=inset.top;
        id manager=m0(editor,"layoutManager"),container=m0(editor,"textContainer");
        if(manager && container && isfinite(point.x) && isfinite(point.y)) {
            U glyph=((U (*)(id,SEL,Point,id))objc_msgSend)(manager,sel_registerName("glyphIndexForPoint:inTextContainer:"),point,container);
            if(glyph<integer(manager,"numberOfGlyphs")) {
                U index=((U (*)(id,SEL,U))objc_msgSend)(manager,sel_registerName("characterIndexForGlyphAtIndex:"),glyph);
                Rect bounds=((Rect (*)(id,SEL,Range,id))objc_msgSend)(manager,sel_registerName("boundingRectForGlyphRange:inTextContainer:"),(Range){glyph,1},container);
                id source=m0(editor,"attributedText");
                /* TextKit's nearest glyph can be outside the actual text. */
                if(index<integer(source,"length") && point.x>=bounds.origin.x && point.y>=bounds.origin.y &&
                    point.x<bounds.origin.x+bounds.size.width && point.y<bounds.origin.y+bounds.size.height) {
                    id candidate=attachment_at(source,index);
                    if(owned_attachment_at(owner,editor,candidate,(Range){index,1})) {attachment=candidate;*range=(Range){index,1};}
                }
            }
        }
    }
    objc_release(owner);return attachment;
}
static BOOL hold_receive_touch(id self,SEL command,id gesture,id touch) {
    (void)command;State *s=state(self);Range range={0};
    if(!s || gesture!=s->hold)return YES;
    s->hold_touch=attachment_at_point(self,gesture,touch,&range)!=nil;return s->hold_touch;
}
static BOOL hold_should_begin(id self,SEL command,id gesture) {
    (void)command;State *s=state(self);Range range={0};
    return !s || gesture!=s->hold || attachment_at_point(self,gesture,gesture,&range)!=nil;
}
static BOOL hold_priority(id self,SEL command,id gesture,id other) {
    (void)command;State *s=state(self);
    if(!s || gesture!=s->hold || gesture==other || !s->hold_touch)return NO;
    id editor=m0(gesture,"view"),view=m0(other,"view");
    for(U depth=0;editor && view && depth<12;depth++,view=m0(view,"superview"))if(view==editor)return YES;
    return NO;
}
static void details(id self,SEL command,id object) {
    (void)command;(void)object;State *s=state(self);if(!s)return;
    id attachment=s->details_attachment;s->details_attachment=nil;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    /* Recheck identity after UIKit has finished processing the gesture. A
     * deleted/rebuilt attachment, detached chat or pending modal cannot open. */
    U length=integer(m0(editor,"attributedText"),"length");
    if(attachment && length<=4096 && !tas_emote_ui_modal_visible(owner))for(U i=0;i<length;i++) {
        if(!owned_attachment_at(owner,editor,attachment,(Range){i,1}))continue;
        id metadata=tas_emotes_metadata_copy(attachment_number(attachment));
        if(metadata && tas_emote_ui_present_details(owner,metadata)) {
            INC(details_holds);
            id feedback=((id (*)(id,SEL,long))objc_msgSend)(m0((id)objc_getClass("UIImpactFeedbackGenerator"),"alloc"),sel_registerName("initWithStyle:"),0);
            m0(feedback,"impactOccurred");objc_release(feedback);
        }
        objc_release(metadata);break;
    }
    objc_release(attachment);objc_release(owner);
}
static void hold(id self,SEL command,id gesture) {
    (void)command;if(integer(gesture,"state")!=1)return; /* Began only. */
    Range range={0};id attachment=attachment_at_point(self,gesture,gesture,&range);State *s=state(self);
    if(!attachment || !s || s->details_attachment)return;
    s->details_attachment=objc_retain(attachment);
    ((void (*)(id,SEL,SEL,id,double))objc_msgSend)(self,sel_registerName("performSelector:withObject:afterDelay:"),sel_registerName("ssDetails:"),nil,0.0);
}
static void install_hold(id target,id editor) {
    State *s=state(target);
    if(!s || !interaction_installed || (objc_getClass("UITextItem") && !item_menu_installed))return;
    if(s->hold && m0(s->hold,"view")==editor)return;
    clear_hold(s);
    s->hold=((id (*)(id,SEL,id,SEL))objc_msgSend)(m0((id)objc_getClass("UILongPressGestureRecognizer"),"alloc"),sel_registerName("initWithTarget:action:"),target,sel_registerName("ssHold:"));
    ((void (*)(id,SEL,double))objc_msgSend)(s->hold,sel_registerName("setMinimumPressDuration:"),0.5);
    ((void (*)(id,SEL,BOOL))objc_msgSend)(s->hold,sel_registerName("setCancelsTouchesInView:"),NO);
    v1(s->hold,"setDelegate:",target);v1(editor,"addGestureRecognizer:",s->hold);
}
static id item_menu(id owner,SEL command,id editor,id item,id menu) {
    if(((BOOL (*)(id,SEL,SEL))objc_msgSend)(item,sel_registerName("respondsToSelector:"),sel_registerName("textAttachment")) &&
        ((BOOL (*)(id,SEL,SEL))objc_msgSend)(item,sel_registerName("respondsToSelector:"),sel_registerName("range"))) {
        Range range=((Range (*)(id,SEL))objc_msgSend)(item,sel_registerName("range"));
        if(owned_attachment_at(owner,editor,m0(item,"textAttachment"),range))return nil;
    }
    return item_menu_original ? ((id (*)(id,SEL,id,id,id))item_menu_original)(owner,command,editor,item,menu) :
        m1((id)objc_getClass("UITextItemMenuConfiguration"),"configurationWithMenu:",menu);
}
static BOOL attachment_interaction(id owner,SEL command,id editor,id attachment,Range range,long interaction) {
    if(owned_attachment_at(owner,editor,attachment,range))return NO;
    return interaction_original ? ((BOOL (*)(id,SEL,id,id,Range,long))interaction_original)(owner,command,editor,attachment,range,interaction) : YES;
}
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
static BOOL watch_owner(id owner) {
    if(!owners)owners=objc_retain(m0((id)objc_getClass("NSHashTable"),"weakObjectsHashTable"));
    if(((BOOL (*)(id,SEL,id))objc_msgSend)(owners,sel_registerName("containsObject:"),owner))return YES;
    if(integer(owners,"count")>=8)return NO;
    v1(owners,"addObject:",owner);return YES;
}
static void sync(id owner) {
    if(!tas_emotes_enabled_this_launch() || !main_thread() || !clock_class)return;
    INC(syncs);id editor=editor_for(owner);
    id target=objc_getAssociatedObject(owner,&state_key);State *s=target ? state(target) : NULL;
    if(!visible(editor)){if(s)stop(s);return;}
    if(m0(editor,"markedTextRange"))return;
    id source=m0(editor,"attributedText");U length=integer(source,"length");
    if(length>4096){if(s){stop(s);clear_frames(s);}INC(refused);return;}
    if(!s) {
        target=m0((id)clock_class,"new");s=calloc(1,sizeof(*s));
        if(s && target){objc_initWeak(&s->owner,owner);memcpy((char *)target+clock_offset,&s,sizeof(s));associate(owner,&state_key,target);}
        else {free(s);s=NULL;}
        objc_release(target);
    }
    /* Holds must work for static and cold emotes as well as decoded GIFs. */
    if(s)install_hold(target,editor);
    Frame frames[MAX_FRAMES];U n=0,total_cost=0;id string=m0(source,"string");
    for(U i=0;i<length && n<MAX_FRAMES;i++) {
        if(((uint16_t (*)(id,SEL,U))objc_msgSend)(string,sel_registerName("characterAtIndex:"),i)!=0xfffc)continue;
        id attachment=attachment_at(source,i);uint64_t number=attachment_number(attachment);
        if(!number) {
            /* Native numeric emotes also need a weak owner for cold-image
             * geometry invalidation; no native decoder or clock is added. */
            if(objc_getAssociatedObject(attachment,&native_image_key))watch_owner(owner);
            continue;
        }
        /* Track the visible input before its first image download completes.
         * A decoder-only registry misses cold attachments until another edit. */
        if(!watch_owner(owner)){INC(refused);break;}
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
static BOOL composing(id owner) {
    id editor=editor_for(owner);
    return tas_emotes_enabled_this_launch() && editor && m0(editor,"markedTextRange");
}
static void flush_map(id owner) {
    if(composing(owner) || !map_original)return;
    id pending=objc_retain(objc_getAssociatedObject(owner,&pending_map_key));
    if(!pending)return;
    associate(owner,&pending_map_key,nil);
    ((void (*)(id,SEL,id))map_original)(owner,sel_registerName("setEmoteMap:"),kind(pending,"NSNull") ? nil : pending);
    objc_release(pending);
}
/* The donor's change delegate checks markedTextRange, but its React prop
 * setters rebuild attachments without that check. A provisional full code
 * must never round-trip through JS and those setters while UIKit owns it.
 * Discard provisional values rather than replaying a cancelled prediction.
 * Keep only the latest recognition map; apply it after the native delegate
 * has reconstructed committed text, including when composition is cancelled. */
static void changed(id self,SEL command,id editor){if(composing(self)){INC(provisional);return;}((void (*)(id,SEL,id))change_original)(self,command,editor);flush_map(self);sync(self);}
static void selection(id self,SEL command,id editor){if(composing(self)){INC(provisional);return;}((void (*)(id,SEL,id))selection_original)(self,command,editor);flush_map(self);sync(self);}
static void moved(id self,SEL command){((void (*)(id,SEL))move_original)(self,command);sync(self);}
static void value(id self,SEL command,id text){if(composing(self)){INC(provisional);return;}((void (*)(id,SEL,id))value_original)(self,command,text);flush_map(self);sync(self);}
static void emote_map(id self,SEL command,id map){if(composing(self)){associate(self,&pending_map_key,map ? map : m0((id)objc_getClass("NSNull"),"null"));INC(provisional);return;}associate(self,&pending_map_key,nil);((void (*)(id,SEL,id))map_original)(self,command,map);sync(self);}
static id current_plain_copy(id owner) {
    if(!main_thread() || !kind(owner,INPUT) || !bridge_string)return nil;
    Class cls=object_getClass(owner);
    Ivar field=class_getInstanceVariable(cls,"currentPlainText"),next=class_getInstanceVariable(cls,"imageCache");
    if(!field || !next)return nil;
    ptrdiff_t offset=ivar_getOffset(field),end=ivar_getOffset(next);
    if(offset<0 || end-offset!=16 || (size_t)end>=class_getInstanceSize(cls))return nil;
    uint64_t words[2];memcpy(words,(char *)owner+offset,sizeof(words));
    return words[1] ? bridge_string(words[0],words[1]) : nil;
}
static void selection_prop(id self,SEL command,id request) {
    /* Our suggestion request carries the draft it was created for. Reject
     * late props after newer native text; ordinary Twitch selection props
     * without that context retain their original behavior. */
    if(tas_emotes_enabled_this_launch() && main_thread() && kind(request,"NSDictionary") && editor_for(self)) {
        id expected=m1(request,"objectForKey:",str("text"));
        if(kind(expected,"NSString")) {
            id current=current_plain_copy(self);
            BOOL stale=composing(self) || (kind(current,"NSString") &&
                !((BOOL (*)(id,SEL,id))objc_msgSend)(current,sel_registerName("isEqualToString:"),expected));
            objc_release(current);
            if(stale){request=nil;INC(stale_selections);}
        }
    }
    ((void (*)(id,SEL,id))selection_setter)(self,command,request);
}
static BOOL should_change(id self,SEL command,id editor,Range range,id text) {
    BOOL accepted=((BOOL (*)(id,SEL,id,Range,id))edit_original)(self,command,editor,range,text);
    /* The donor applies selection props asynchronously, checking only its
     * selectionGeneration. An accepted edit supersedes those old offsets.
     * Its nil setter increments that generation without moving the caret.
     * Cancel before UIKit performs the edit; preserve vetoed edits and leave
     * tokenization, UTF-16 mapping and the resulting selection to Twitch. */
    if(accepted && tas_emotes_enabled_this_launch() && main_thread() && selection_setter &&
        editor==editor_for(self) && editor && m0(self,"selection")) {
        ((void (*)(id,SEL,id))selection_setter)(self,sel_registerName("setSelection:"),nil);
        INC(selection_invalidations);
    }
    return accepted;
}
static void owner_dealloc(id self,SEL command){id target=objc_getAssociatedObject(self,&state_key);if(target){State *s=state(target);if(s){stop(s);clear_frames(s);clear_hold(s);}}((void (*)(id,SEL))dealloc_original)(self,command);}
static void install(Class cls,const char *selector,const char *encoding,IMP replacement,IMP *original) {
    if(!cls || *original)return;Method method=class_getInstanceMethod(cls,sel_registerName(selector));
    if(!method || strcmp(method_getTypeEncoding(method),encoding))return;
    *original=method_getImplementation(method);
    if(!class_addMethod(cls,sel_registerName(selector),replacement,encoding))method_setImplementation(method,replacement);
}
static BOOL optional_input_hook(Class cls,const char *selector,const char *encoding,IMP replacement,IMP *original) {
    if(!cls)return NO;
    if(class_getInstanceMethod(cls,sel_registerName(selector))) {
        install(cls,selector,encoding,replacement,original);return *original!=NULL;
    }
    return class_addMethod(cls,sel_registerName(selector),replacement,encoding);
}
void tas_rn_composer_ui_retry_hooks(void) {
    if(!tas_emotes_enabled_this_launch())return;
    pthread_mutex_lock(&install_lock);
    if(!bridge_string)bridge_string=(StringBridge)dlsym(RTLD_DEFAULT,"$sSS10FoundationE19_bridgeToObjectiveCSo8NSStringCyF");
    if(!clock_class && objc_getClass("NSObject")) {
        Class cls=objc_allocateClassPair(objc_getClass("NSObject"),"StreamsideRNPreviewClock",0);
        if(cls && class_addIvar(cls,"_state",sizeof(State *),3,"^v") &&
            class_addMethod(cls,sel_registerName("ssTick:"),(IMP)animate,"v24@0:8@16") &&
            class_addMethod(cls,sel_registerName("ssHold:"),(IMP)hold,"v24@0:8@16") &&
            class_addMethod(cls,sel_registerName("ssDetails:"),(IMP)details,"v24@0:8@16") &&
            class_addMethod(cls,sel_registerName("gestureRecognizerShouldBegin:"),(IMP)hold_should_begin,"B24@0:8@16") &&
            class_addMethod(cls,sel_registerName("gestureRecognizer:shouldReceiveTouch:"),(IMP)hold_receive_touch,"B32@0:8@16@24") &&
            class_addMethod(cls,sel_registerName("gestureRecognizer:shouldBeRequiredToFailByGestureRecognizer:"),(IMP)hold_priority,"B32@0:8@16@24") &&
            class_addMethod(cls,sel_registerName("dealloc"),(IMP)clock_dealloc,"v16@0:8")) {
            target_dealloc=class_getMethodImplementation(objc_getClass("NSObject"),sel_registerName("dealloc"));
            objc_registerClassPair(cls);clock_class=cls;clock_offset=ivar_getOffset(class_getInstanceVariable(cls,"_state"));
        } else if(cls)objc_disposeClassPair(cls);
    }
    Class attachment=objc_getClass(ATTACHMENT),input=objc_getClass(INPUT);
    if(input && !selection_setter) {
        Method getter=class_getInstanceMethod(input,sel_registerName("selection"));
        Method setter=class_getInstanceMethod(input,sel_registerName("setSelection:"));
        if(getter && setter && !strcmp(method_getTypeEncoding(getter),"@16@0:8"))
            install(input,"setSelection:","v24@0:8@16",(IMP)selection_prop,&selection_setter);
    }
    install(attachment,"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:","{CGRect={CGPoint=dd}{CGSize=dd}}80@0:8@16{CGRect={CGPoint=dd}{CGSize=dd}}24{CGPoint=dd}56q72",(IMP)attachment_bounds,&bounds_original);
    install(attachment,"setImage:","v24@0:8@16",(IMP)attachment_image,&image_original);
    install(input,"layoutSubviews","v16@0:8",(IMP)layout,&layout_original);
    install(input,"textViewDidChange:","v24@0:8@16",(IMP)changed,&change_original);
    install(input,"textViewDidChangeSelection:","v24@0:8@16",(IMP)selection,&selection_original);
    install(input,"textView:shouldChangeTextInRange:replacementText:","B48@0:8@16{_NSRange=QQ}24@40",(IMP)should_change,&edit_original);
    install(input,"didMoveToWindow","v16@0:8",(IMP)moved,&move_original);
    install(input,"setValue:","v24@0:8@16",(IMP)value,&value_original);
    install(input,"setEmoteMap:","v24@0:8@16",(IMP)emote_map,&map_original);
    install(input,"dealloc","v16@0:8",(IMP)owner_dealloc,&dealloc_original);
    if(!item_menu_installed && objc_getClass("UITextItem"))item_menu_installed=optional_input_hook(input,"textView:menuConfigurationForTextItem:defaultMenu:","@40@0:8@16@24@32",(IMP)item_menu,&item_menu_original);
    if(!interaction_installed)interaction_installed=optional_input_hook(input,"textView:shouldInteractWithTextAttachment:inRange:interaction:","B56@0:8@16@24{_NSRange=QQ}32q48",(IMP)attachment_interaction,&interaction_original);
    pthread_mutex_unlock(&install_lock);
    /* The existing launch/foreground observer retries these hooks. */
    sync_owners();
}
void tas_rn_composer_ui_status(char *buffer,size_t capacity) {
    if(!buffer || !capacity)return;
    snprintf(buffer,capacity,"\nRN native input previews (this launch)\n"
        "Hooks (bounds/layout/change/selection/window/value/map/dealloc)/String bridge: %s/%s/%s/%s/%s/%s/%s/%s/%s\n"
        "Provisional callbacks/props held: %llu\n"
        "Provider hold hooks (item menu/attachment)/details shown: %s/%s/%llu\n"
        "Cursor edit/selection hooks/props invalidated/stale props refused: %s/%s/%llu/%llu\n"
        "Native numeric-emote image hook/aspect corrections/layout refreshes: %s/%llu/%llu\n"
        "Bounds/sizes/syncs/GIF bodies/decoders/ticks/advances/refused: %llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu\n",
        bounds_original ? "installed":"missing",layout_original ? "installed":"missing",change_original ? "installed":"missing",
        selection_original ? "installed":"missing",move_original ? "installed":"missing",value_original ? "installed":"missing",
        map_original ? "installed":"missing",dealloc_original ? "installed":"missing",bridge_string ? "available":"missing",(unsigned long long)GET(provisional),
        item_menu_installed ? "installed":"missing",interaction_installed ? "installed":"missing",(unsigned long long)GET(details_holds),
        edit_original ? "installed":"missing",selection_setter ? "installed":"missing",(unsigned long long)GET(selection_invalidations),(unsigned long long)GET(stale_selections),
        image_original ? "installed":"missing",(unsigned long long)GET(native_sized),(unsigned long long)GET(native_layouts),
        (unsigned long long)GET(bounds_calls),(unsigned long long)GET(sized),(unsigned long long)GET(syncs),(unsigned long long)GET(images),
        (unsigned long long)GET(decoders),(unsigned long long)GET(ticks),(unsigned long long)GET(advances),(unsigned long long)GET(refused));
}
