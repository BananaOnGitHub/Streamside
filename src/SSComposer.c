/* Streamside's UIKit composer integration. Never construct Swift emote values,
 * or mutate native emote history/models. All editor offsets are UTF-16. */
#include "SSComposer.h"
#include "SSComposerModel.h"
#include "TASEmotes.h"
#include "TASEmoteGeometry.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

typedef unsigned long U;
typedef long I;
typedef struct { double x,y; } Point;
typedef struct { double width,height; } Size;
typedef struct { Point origin; Size size; } Rect;
typedef struct { U location,length; } Range;
typedef struct { double top,left,bottom,right; } Insets;
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_getAssociatedObject(id,const void *);
extern void objc_setAssociatedObject(id,const void *,id,uintptr_t);
extern id objc_initWeak(id *,id);
extern id objc_loadWeakRetained(id *);
extern void objc_destroyWeak(id *);
#define INPUT "_TtC6Twitch13ChatInputView"
#define FOOTER "_TtC6Twitch34EmoticonPaletteContainerFooterView"
#define CONTAINER "_TtC6Twitch28EmoticonPaletteContainerView"
#define ENTRY "_TtC6TwitchP33_C04E56FD3AAC83881997DAF21B26CBB613TextEntryView"
#define MODE_KEY "StreamsideEmoteSuggestions"
#define RECENTS_KEY "StreamsideRecentEmotes"
#define ATTACHMENT_KEY "StreamsideEmoteCode"
#define MAX_TOKENS 512
#define IMAGE_NOTICE "StreamsideEmoteImagesChanged"
static char state_key,footer_key,button_key,cell_key,undo_key,attachment_metadata_key;
static Class delegate_class,attachment_class;
static IMP original_dealloc,original_change,original_selection,original_should_change;
static IMP original_begin,original_end,original_send,original_apply,original_move,original_layout,original_emoticon;
static IMP original_footer_apply,original_footer_move,original_container_layout;
static IMP original_footer_actions[5],original_copy,original_cut,original_paste,original_undo,original_redo;
static id images,pending,failed,image_session;
static uint64_t edited,previewed,insertions,palette_opens,identity_misses,image_failures;
static uint64_t grid_taps,strip_taps,selection_missing,lookup_misses,validation_vetoes,range_misses,unchanged_edits;
#define INC(v) ((void)__atomic_add_fetch(&(v),1,__ATOMIC_RELAXED))
#define GET(v) __atomic_load_n(&(v),__ATOMIC_RELAXED)

static id m0(id o,const char *s) { return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static id m1(id o,const char *s,id a) { return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a); }
static void v1(id o,const char *s,id a) { ((void (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a); }
static void vi(id o,const char *s,I a) { ((void (*)(id,SEL,I))objc_msgSend)(o,sel_registerName(s),a); }
static void vb(id o,const char *s,BOOL a) { ((void (*)(id,SEL,BOOL))objc_msgSend)(o,sel_registerName(s),a); }
static U number(id o,const char *s) { return ((U (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static BOOL yes(id o,const char *s) { return ((BOOL (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static id str(const char *s) { return m1((id)objc_getClass("NSString"),"stringWithUTF8String:",(id)s); }
static BOOL responds(id o,const char *s) { return o && ((BOOL (*)(id,SEL,SEL))objc_msgSend)(o,sel_registerName("respondsToSelector:"),sel_registerName(s)); }
static BOOL kind(id o,const char *s) { Class c=objc_getClass(s); return o && c && ((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),c); }
static BOOL equal(id a,id b) { return a == b || (a && b && ((BOOL (*)(id,SEL,id))objc_msgSend)(a,sel_registerName("isEqual:"),b)); }
static id key(id o,const char *k) { return m1(o,"objectForKey:",str(k)); }
static id at(id a,U i) { return ((id (*)(id,SEL,U))objc_msgSend)(a,sel_registerName("objectAtIndex:"),i); }
static id sub(id s,Range r) { return ((id (*)(id,SEL,Range))objc_msgSend)(s,sel_registerName("substringWithRange:"),r); }
static Rect rect(id o,const char *s) { return ((Rect (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static void frame(id o,Rect r) { ((void (*)(id,SEL,Rect))objc_msgSend)(o,sel_registerName("setFrame:"),r); }
static id view(const char *c,Rect r) { return ((id (*)(id,SEL,Rect))objc_msgSend)(m0((id)objc_getClass(c),"alloc"),sel_registerName("initWithFrame:"),r); }
static id color(const char *s) { return m0((id)objc_getClass("UIColor"),s); }
static id defaults(void) { return m0((id)objc_getClass("NSUserDefaults"),"standardUserDefaults"); }
static void associate(id o,const void *k,id a) { objc_setAssociatedObject(o,k,a,1); }
static Range selection(id editor) { return ((Range (*)(id,SEL))objc_msgSend)(editor,sel_registerName("selectedRange")); }
static void select_range(id editor,Range r) { ((void (*)(id,SEL,Range))objc_msgSend)(editor,sel_registerName("setSelectedRange:"),r); }
/* Only inspected strong object ivars are read here, and their expected UIKit
 * class is checked. Resolve offset and pointer span; Swift structs stay opaque. */
static id object_field(id o,const char *name,const char *expected) {
    if (!o) return nil;
    Class c=object_getClass(o); Ivar iv=class_getInstanceVariable(c,name);
    if (!iv) return nil;
    ptrdiff_t offset=ivar_getOffset(iv); size_t size=class_getInstanceSize(c);
    if (offset < 0 || (size_t)offset > size || size-(size_t)offset < sizeof(id)) return nil;
    id result=nil; memcpy(&result,(char *)o+offset,sizeof(result));
    return kind(result,expected) ? result : nil;
}
static id editor_for(id owner) { return object_field(owner,"textEntryView","UITextView"); }
/* Twitch 30.4.2 stores Identity? in a 56-byte span. Its native palette
 * selection checks the word at +16 for nil, then reads UInt32 at +0. Read
 * those primitive words only; never dereference its Swift strings.
 * Unknown layouts fail to globals instead of borrowing a background room. */
static id room_for(id owner) {
    Class c=object_getClass(owner);
    Ivar a=class_getInstanceVariable(c,"channelIdentity"),b=class_getInstanceVariable(c,"shouldOmitSettingsUI");
    if (!a || !b || ivar_getOffset(b)-ivar_getOffset(a)!=56) { INC(identity_misses); return nil; }
    ptrdiff_t off=ivar_getOffset(a);
    if (off < 0 || (size_t)off+56 > class_getInstanceSize(c)) return nil;
    uint32_t room=ss_identity_room((char *)owner+off,56);
    if (!room) return nil;
    char text[16]; snprintf(text,sizeof(text),"%u",room); return str(text);
}

typedef struct {
    id owner; /* objc weak storage */
    id room,strip,suggestions,panel,grid,provider,scope,entries,empty,recent_strip;
    id footer; /* objc weak storage: the emote keyboard may be recreated */
    id native_content; /* retained only while an overlay uses it */
    Insets native_inset;
    Range completion;
    int library,library_scope,tab;
    BOOL busy,scheduled,native_was_hidden;
} State;
static State *state(id delegate) {
    State *s=NULL; Ivar iv=class_getInstanceVariable(delegate_class,"_state");
    if (delegate && iv) memcpy(&s,(char *)delegate+ivar_getOffset(iv),sizeof(s));
    return s;
}
static id delegate_for(id owner);
static void refresh(id delegate);
static void render(id delegate);
static void expand(id delegate);
static void layout(id delegate);
static void restore_native(State *s);

int ss_composer_suggestion_mode(void) {
    I mode=((I (*)(id,SEL,id))objc_msgSend)(defaults(),sel_registerName("integerForKey:"),str(MODE_KEY));
    return mode>=0 && mode<=2 ? (int)mode : 0;
}
void ss_composer_set_suggestion_mode(int mode) {
    if (mode<0 || mode>2) return;
    ((void (*)(id,SEL,I,id))objc_msgSend)(defaults(),sel_registerName("setInteger:forKey:"),(I)mode,str(MODE_KEY));
    ((void (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSNotificationCenter"),"defaultCenter"),sel_registerName("postNotificationName:object:"),str(IMAGE_NOTICE),nil);
}

static id cached_image(id metadata) { id url=key(metadata,"url"); return url ? m1(images,"objectForKey:",url) : nil; }
static void image_request(id metadata) {
    id url=key(metadata,"url"); const char *utf8=((const char *(*)(id,SEL))objc_msgSend)(url,sel_registerName("UTF8String"));
    if (!utf8 || !tas_emotes_is_provider_image_url(utf8) || cached_image(metadata) || key(pending,utf8) || number(pending,"count")>=8) return;
    id failure=m1(failed,"objectForKey:",url);
    if (failure && time(NULL)-(time_t)number(failure,"longLongValue")<60) return;
    id held=objc_retain(url);
    id task=((id (*)(id,SEL,id,id))objc_msgSend)(image_session,sel_registerName("dataTaskWithURL:completionHandler:"),m1((id)objc_getClass("NSURL"),"URLWithString:",url),(id)^(id data,id response,id error) {
        I status=((I (*)(id,SEL))objc_msgSend)(response,sel_registerName("statusCode"));
        U bytes=number(data,"length");
        id held_data=!error && status>=200 && status<300 && bytes && bytes<=2*1024*1024 ? objc_retain(data) : nil;
        ((void (*)(id,SEL,id))objc_msgSend)(m0((id)objc_getClass("NSOperationQueue"),"mainQueue"),sel_registerName("addOperationWithBlock:"),(id)^{
            v1(pending,"removeObjectForKey:",held);
            id image=nil,animation=nil;
            if (held_data) {
                const unsigned char *p=((const unsigned char *(*)(id,SEL))objc_msgSend)(held_data,sel_registerName("bytes"));
                double aspect=tas_emote_image_aspect(p,bytes);
                /* Provider thumbnails, not arbitrary full resolution images. */
                if (aspect>0) image=m1((id)objc_getClass("UIImage"),"imageWithData:",held_data);
                Size dimensions=((Size (*)(id,SEL))objc_msgSend)(image,sel_registerName("size"));
                if (dimensions.width>1024 || dimensions.height>1024 || dimensions.width*dimensions.height>524288) image=nil;
                if (image && bytes>=6 && !memcmp(p,"GIF8",4) && objc_getClass("FLAnimatedImage")) {
                    animation=m1(m0((id)objc_getClass("FLAnimatedImage"),"alloc"),"initWithAnimatedGIFData:",held_data);
                    if (responds(animation,"setFrameCacheSizeMax:")) vi(animation,"setFrameCacheSizeMax:",4);
                }
                if (image) {
                    id record=m0((id)objc_getClass("NSMutableDictionary"),"new");
                    ((void (*)(id,SEL,id,id))objc_msgSend)(record,sel_registerName("setObject:forKey:"),image,str("image"));
                    if (animation) ((void (*)(id,SEL,id,id))objc_msgSend)(record,sel_registerName("setObject:forKey:"),animation,str("animation"));
                    U cost=(U)(dimensions.width*dimensions.height*4)*(animation ? 5 : 1)+bytes;
                    ((void (*)(id,SEL,id,id,U))objc_msgSend)(images,sel_registerName("setObject:forKey:cost:"),record,held,cost);
                    objc_release(record);
                }
                if (animation) objc_release(animation);
                objc_release(held_data);
            }
            if (!image) {
                INC(image_failures);
                if (number(failed,"count")>=128) m0(failed,"removeAllObjects");
                id now=((id (*)(id,SEL,int64_t))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithLongLong:"),(int64_t)time(NULL));
                ((void (*)(id,SEL,id,id))objc_msgSend)(failed,sel_registerName("setObject:forKey:"),now,held);
            }
            objc_release(held);
            ((void (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSNotificationCenter"),"defaultCenter"),sel_registerName("postNotificationName:object:"),str(IMAGE_NOTICE),nil);
        });
    });
    if (!task) { objc_release(held); return; }
    ((void (*)(id,SEL,id,id))objc_msgSend)(pending,sel_registerName("setObject:forKey:"),task,url);
    m0(task,"resume");
}
static void set_thumbnail(id image_view,id metadata) {
    id cached=cached_image(metadata);
    v1(image_view,"setImage:",key(cached,"image"));
    if (responds(image_view,"setAnimatedImage:")) v1(image_view,"setAnimatedImage:",key(cached,"animation"));
    image_request(metadata);
}

/* Expand only our attribute. Twitch's native attachments and other attributes
 * survive byte-for-byte. Visual substitutions never enter undo history. */
static id expanded_copy(id editor,Range *selected,SSSpan *spans,size_t *n) {
    id source=m0(editor,"attributedText"),copy=m0(source,"mutableCopy");
    if (!copy) copy=m1(m0((id)objc_getClass("NSMutableAttributedString"),"alloc"),"initWithString:",str(""));
    U length=number(source,"length"),extra=0; *n=0;
    for (U i=0;i<length;i++) {
        id code=((id (*)(id,SEL,id,U,Range *))objc_msgSend)(source,sel_registerName("attribute:atIndex:effectiveRange:"),str(ATTACHMENT_KEY),i,NULL);
        if (!kind(code,"NSString") || !number(code,"length") || *n>=MAX_TOKENS) continue;
        U size=number(code,"length"); spans[(*n)++]=(SSSpan){i+extra,size}; extra+=size-1;
    }
    if (selected) {
        U end=ss_plain_position(selected->location+selected->length,spans,*n);
        selected->location=ss_plain_position(selected->location,spans,*n); selected->length=end-selected->location;
    }
    for (size_t i=*n;i>0;i--) {
        size_t j=i-1; U shown=ss_display_position(spans[j].start,spans,j);
        id code=((id (*)(id,SEL,id,U,Range *))objc_msgSend)(source,sel_registerName("attribute:atIndex:effectiveRange:"),str(ATTACHMENT_KEY),shown,NULL);
        ((void (*)(id,SEL,Range,id))objc_msgSend)(copy,sel_registerName("replaceCharactersInRange:withString:"),(Range){shown,1},code);
        ((void (*)(id,SEL,id,Range))objc_msgSend)(copy,sel_registerName("removeAttribute:range:"),str("NSAttachment"),(Range){shown,number(code,"length")});
        ((void (*)(id,SEL,id,Range))objc_msgSend)(copy,sel_registerName("removeAttribute:range:"),str(ATTACHMENT_KEY),(Range){shown,number(code,"length")});
    }
    return copy;
}
static void visual_text(id editor,id text,Range selected) {
    /* This is a direct text-storage presentation update, not a user edit.
     * Querying or toggling UITextView's undo manager here can throw while an
     * asynchronous image notification is being delivered (iOS 18.2). */
    id storage=m0(editor,"textStorage"); m0(storage,"beginEditing");
    ((void (*)(id,SEL,Range,id))objc_msgSend)(storage,sel_registerName("replaceCharactersInRange:withAttributedString:"),(Range){0,number(storage,"length")},text);
    m0(storage,"endEditing");
    U len=number(text,"length"); if (selected.location>len) selected.location=len;
    if (selected.length>len-selected.location) selected.length=len-selected.location;
    select_range(editor,selected);
}
static void expand(id delegate) {
    State *s=state(delegate); if (!s || s->busy) return;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!editor || m0(editor,"markedTextRange")) { objc_release(owner); return; }
    SSSpan spans[MAX_TOKENS]; size_t n; Range r=selection(editor);
    id plain=expanded_copy(editor,&r,spans,&n);
    if (n) { s->busy=YES; visual_text(editor,plain,r); s->busy=NO; }
    objc_release(plain); objc_release(owner);
}
static void render(id delegate) {
    State *s=state(delegate); if (!s || s->busy) return;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!editor || m0(editor,"markedTextRange")) { objc_release(owner); return; }
    Range r=selection(editor); SSSpan old[MAX_TOKENS],spans[MAX_TOKENS]; size_t old_n,n=0;
    id plain=expanded_copy(editor,&r,old,&old_n),text=m0(plain,"string"); U length=number(text,"length");
    if (length>4096) { objc_release(plain); objc_release(owner); return; }
    uint16_t units[4096]; ((void (*)(id,SEL,uint16_t *,Range))objc_msgSend)(text,sel_registerName("getCharacters:range:"),units,(Range){0,length});
    id output=m0(plain,"mutableCopy"),source=m0(editor,"attributedText");
    for (U start=0;start<length && n<MAX_TOKENS;) {
        if (ss_space(units[start]) || units[start]==0xfffc) { start++; continue; }
        U end=start; while (end<length && !ss_space(units[end]) && units[end]!=0xfffc) end++;
        id metadata=tas_emotes_named_copy(s->room,sub(text,(Range){start,end-start}));
        id cached=metadata ? cached_image(metadata) : nil,attachment=nil;
        /* Reuse our existing decoded preview after cache eviction; do not keep
         * downloading it on every edit or replace identical attachments. */
        U original_position=ss_display_position(start,old,old_n);
        if (metadata && original_position<number(source,"length")) {
            id previous=((id (*)(id,SEL,id,U,Range *))objc_msgSend)(source,sel_registerName("attribute:atIndex:effectiveRange:"),str("NSAttachment"),original_position,NULL);
            id previous_metadata=objc_getAssociatedObject(previous,&attachment_metadata_key);
            if (previous_metadata && equal(key(previous_metadata,"id"),key(metadata,"id"))) attachment=objc_retain(previous);
        }
        if (metadata && !attachment) image_request(metadata);
        if (cached || attachment) {
            if (!attachment) { attachment=m0((id)attachment_class,"new"); v1(attachment,"setImage:",key(cached,"image")); associate(attachment,&attachment_metadata_key,metadata); }
            double height=22, width=22,aspect=((double (*)(id,SEL))objc_msgSend)(key(metadata,"aspect"),sel_registerName("doubleValue"));
            if (aspect<=0) { Size z=((Size (*)(id,SEL))objc_msgSend)(m0(attachment,"image"),sel_registerName("size")); if (z.height>0) aspect=z.width/z.height; }
            tas_emote_proportions(&width,&height,aspect);
            ((void (*)(id,SEL,Rect))objc_msgSend)(attachment,sel_registerName("setBounds:"),(Rect){{0,-4},{width,height}});
            id item=m1((id)objc_getClass("NSAttributedString"),"attributedStringWithAttachment:",attachment);
            id replacement=m0(item,"mutableCopy");
            ((void (*)(id,SEL,id,id,Range))objc_msgSend)(replacement,sel_registerName("addAttribute:value:range:"),str(ATTACHMENT_KEY),key(metadata,"name"),(Range){0,1});
            U shown=ss_display_position(start,spans,n);
            ((void (*)(id,SEL,Range,id))objc_msgSend)(output,sel_registerName("replaceCharactersInRange:withAttributedString:"),(Range){shown,end-start},replacement);
            spans[n++]=(SSSpan){start,end-start}; objc_release(replacement); objc_release(attachment);
        }
        if (metadata) objc_release(metadata); start=end;
    }
    if ((n || old_n) && !((BOOL (*)(id,SEL,id))objc_msgSend)(output,sel_registerName("isEqualToAttributedString:"),source)) {
        U end=ss_display_position(r.location+r.length,spans,n);
        r.location=ss_display_position(r.location,spans,n); r.length=end-r.location;
        s->busy=YES; visual_text(editor,output,r); s->busy=NO;
        __atomic_add_fetch(&previewed,n,__ATOMIC_RELAXED);
        /* Attachment attributes must not leak into subsequent ordinary typing. */
        id attributes=m0(m0(editor,"typingAttributes"),"mutableCopy");
        v1(attributes,"removeObjectForKey:",str(ATTACHMENT_KEY)); v1(attributes,"removeObjectForKey:",str("NSAttachment"));
        v1(editor,"setTypingAttributes:",attributes); objc_release(attributes);
    }
    objc_release(output); objc_release(plain); objc_release(owner);
}

static id recents(State *s) {
    id saved=m1(defaults(),"arrayForKey:",str(RECENTS_KEY)),result=m0((id)objc_getClass("NSMutableArray"),"new");
    if (kind(saved,"NSArray")) for (U i=0;i<number(saved,"count") && i<40;i++) {
        id name=at(saved,i),metadata=tas_emotes_named_copy(s->room,name);
        if (metadata) { v1(result,"addObject:",metadata); objc_release(metadata); }
    }
    return result;
}
static void remember(id name) {
    id saved=m1(defaults(),"arrayForKey:",str(RECENTS_KEY));
    id list=kind(saved,"NSArray") ? m0(saved,"mutableCopy") : m0((id)objc_getClass("NSMutableArray"),"new");
    v1(list,"removeObject:",name);
    ((void (*)(id,SEL,id,U))objc_msgSend)(list,sel_registerName("insertObject:atIndex:"),name,(U)0);
    while (number(list,"count")>40) m0(list,"removeLastObject");
    ((void (*)(id,SEL,id,id))objc_msgSend)(defaults(),sel_registerName("setObject:forKey:"),list,str(RECENTS_KEY)); objc_release(list);
}
static void remember_typed(id delegate) {
    State *s=state(delegate); id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    id text=m0(editor,"text"); U length=number(text,"length");
    if (length<=4096) {
        uint16_t units[4096]; ((void (*)(id,SEL,uint16_t *,Range))objc_msgSend)(text,sel_registerName("getCharacters:range:"),units,(Range){0,length});
        for (U start=0;start<length;) {
            if (ss_space(units[start]) || units[start]==0xfffc) { start++; continue; }
            U end=start; while (end<length && !ss_space(units[end]) && units[end]!=0xfffc) end++;
            id metadata=tas_emotes_named_copy(s->room,sub(text,(Range){start,end-start}));
            if (metadata) { remember(key(metadata,"name")); objc_release(metadata); } start=end;
        }
    }
    objc_release(owner);
}
/* All insertions pass Twitch's native permission/length/command checks. UIKit
 * performs the plain-text edit, so undo and send models see emote codes. */
static BOOL replace_plain(id delegate,Range range,id replacement) {
    State *s=state(delegate); if (!s || s->busy) { INC(selection_missing); return NO; }
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!editor || m0(editor,"markedTextRange")) { INC(selection_missing); objc_release(owner); return NO; }
    expand(delegate); U length=number(m0(editor,"text"),"length");
    if (range.location>length || range.length>length-range.location) { INC(range_misses); objc_release(owner); return NO; }
    BOOL allowed=((BOOL (*)(id,SEL,id,Range,id))original_should_change)(owner,sel_registerName("textView:shouldChangeTextInRange:replacementText:"),editor,range,replacement);
    if (allowed) {
        id beginning=m0(editor,"beginningOfDocument");
        id start=((id (*)(id,SEL,id,I))objc_msgSend)(editor,sel_registerName("positionFromPosition:offset:"),beginning,(I)range.location);
        id end=((id (*)(id,SEL,id,I))objc_msgSend)(editor,sel_registerName("positionFromPosition:offset:"),start,(I)range.length);
        id text_range=((id (*)(id,SEL,id,id))objc_msgSend)(editor,sel_registerName("textRangeFromPosition:toPosition:"),start,end);
        if (text_range) {
            id before=m0(m0(editor,"text"),"copy");
            s->busy=YES;
            ((void (*)(id,SEL,id,id))objc_msgSend)(editor,sel_registerName("replaceRange:withText:"),text_range,replacement);
            BOOL changed=!equal(before,m0(editor,"text")); objc_release(before);
            if (changed) select_range(editor,(Range){range.location+number(replacement,"length"),0});
            s->busy=NO;
            if (changed) { ((void (*)(id,SEL,id))original_change)(owner,sel_registerName("textViewDidChange:"),editor); INC(edited); }
            else { INC(unchanged_edits); allowed=NO; }
        } else { INC(range_misses); allowed=NO; }
    } else INC(validation_vetoes);
    render(delegate); refresh(delegate); objc_release(owner); return allowed;
}
static void choose(id delegate,id metadata,BOOL suggestion) {
    State *s=state(delegate); id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!editor || !metadata) { INC(selection_missing); objc_release(owner); return; }
    id current=tas_emotes_named_copy(room_for(owner),key(metadata,"name"));
    if (!current) { INC(lookup_misses); refresh(delegate); objc_release(owner); return; }
    metadata=current;
    refresh(delegate);
    /* The native palette can leave the editor unfocused. Make it the active
     * text input before asking Twitch to validate and apply the edit. */
    m0(editor,"becomeFirstResponder");
    Range r=selection(editor); SSSpan spans[MAX_TOKENS]; size_t n;
    id plain=expanded_copy(editor,&r,spans,&n); objc_release(plain);
    if (suggestion) r=s->completion;
    id code=m1(key(metadata,"name"),"stringByAppendingString:",str(" "));
    if (replace_plain(delegate,r,code)) { remember(key(metadata,"name")); INC(insertions); }
    objc_release(current); objc_release(owner);
}

static void target(id control,id delegate,const char *action,U events) {
    ((void (*)(id,SEL,id,SEL,U))objc_msgSend)(control,sel_registerName("addTarget:action:forControlEvents:"),delegate,sel_registerName(action),events);
}
static id thumbnail_button(id delegate,id metadata,Rect r) {
    id button=view("UIButton",r); associate(button,&button_key,metadata);
    id image=view(objc_getClass("FLAnimatedImageView") ? "FLAnimatedImageView" : "UIImageView",(Rect){{6,3},{r.size.width-12,30}});
    vi(image,"setContentMode:",1); vb(image,"setUserInteractionEnabled:",NO); set_thumbnail(image,metadata);
    v1(button,"addSubview:",image); objc_release(image);
    id label=view("UILabel",(Rect){{2,33},{r.size.width-4,13}});
    v1(label,"setText:",key(metadata,"name")); vi(label,"setTextAlignment:",1);
    v1(label,"setFont:",((id (*)(id,SEL,double))objc_msgSend)((id)objc_getClass("UIFont"),sel_registerName("systemFontOfSize:"),10.0));
    v1(label,"setTextColor:",color("secondaryLabelColor")); v1(button,"addSubview:",label); objc_release(label);
    v1(button,"setAccessibilityLabel:",key(metadata,"name")); target(button,delegate,"ssPick:",1UL<<6); return button;
}
static void fill_strip(id scroll,id delegate,id items) {
    id children=m0(m0(scroll,"subviews"),"copy");
    for (U i=0;i<number(children,"count");i++) if (objc_getAssociatedObject(at(children,i),&button_key)) m0(at(children,i),"removeFromSuperview"); objc_release(children);
    for (U i=0;i<number(items,"count");i++) {
        id button=thumbnail_button(delegate,at(items,i),(Rect){{(double)i*64,0},{64,48}});
        v1(scroll,"addSubview:",button); objc_release(button);
    }
    ((void (*)(id,SEL,Size))objc_msgSend)(scroll,sel_registerName("setContentSize:"),(Size){(double)number(items,"count")*64,48});
}
static void refresh_strip_images(id scroll) {
    id children=m0(scroll,"subviews");
    for (U i=0;i<number(children,"count");i++) {
        id button=at(children,i),metadata=objc_getAssociatedObject(button,&button_key);
        if (!metadata) continue;
        id image=at(m0(button,"subviews"),0); set_thumbnail(image,metadata);
    }
}
static void picker_button(id self,SEL sel,id sender) { (void)sel; INC(strip_taps); choose(self,objc_getAssociatedObject(sender,&button_key),YES); }
static void recent_button(id self,SEL sel,id sender) { (void)sel; INC(strip_taps); choose(self,objc_getAssociatedObject(sender,&button_key),NO); }
static I item_count(id self,SEL sel,id collection,I section) { (void)sel;(void)collection;(void)section; return (I)number(state(self)->entries,"count"); }
static id cell(id self,SEL sel,id collection,id path) {
    (void)sel; State *s=state(self); U index=number(path,"item");
    id c=((id (*)(id,SEL,id,id))objc_msgSend)(collection,sel_registerName("dequeueReusableCellWithReuseIdentifier:forIndexPath:"),str("SSEmoteCell"),path);
    id content=m0(c,"contentView"),image=objc_getAssociatedObject(c,&cell_key);
    if (!image) {
        image=view(objc_getClass("FLAnimatedImageView") ? "FLAnimatedImageView" : "UIImageView",(Rect){{6,5},{44,34}});
        vi(image,"setContentMode:",1); v1(content,"addSubview:",image); associate(c,&cell_key,image); objc_release(image);
        id label=view("UILabel",(Rect){{1,40},{54,14}}); vi(label,"setTag:",301); vi(label,"setTextAlignment:",1);
        v1(label,"setFont:",((id (*)(id,SEL,double))objc_msgSend)((id)objc_getClass("UIFont"),sel_registerName("systemFontOfSize:"),9.0));
        v1(label,"setTextColor:",color("secondaryLabelColor")); v1(content,"addSubview:",label); objc_release(label);
    }
    id metadata=index<number(s->entries,"count") ? at(s->entries,index) : nil;
    set_thumbnail(image,metadata);
    id label=((id (*)(id,SEL,I))objc_msgSend)(content,sel_registerName("viewWithTag:"),(I)301);
    v1(label,"setText:",key(metadata,"name")); v1(c,"setAccessibilityLabel:",key(metadata,"name"));
    return c;
}
static void selected_cell(id self,SEL sel,id collection,id path) {
    (void)sel; (void)collection; INC(grid_taps); State *s=state(self); U i=number(path,"item");
    if (i<number(s->entries,"count")) choose(self,at(s->entries,i),NO);
    else INC(selection_missing);
}
static id segmented(id delegate,const char **labels,size_t n,const char *action) {
    id items=m0((id)objc_getClass("NSMutableArray"),"new"); for (size_t i=0;i<n;i++) v1(items,"addObject:",str(labels[i]));
    id control=m1(m0((id)objc_getClass("UISegmentedControl"),"alloc"),"initWithItems:",items); objc_release(items);
    vi(control,"setSelectedSegmentIndex:",0); target(control,delegate,action,1UL<<12); return control;
}
static void provider_changed(id self,SEL sel,id control) {
    (void)sel; State *s=state(self); s->library=(int)number(control,"selectedSegmentIndex");
    s->library_scope=0; vi(s->scope,"setSelectedSegmentIndex:",0); /* Every provider change resets Channel. */
    refresh(self);
}
static void scope_changed(id self,SEL sel,id control) { (void)sel; state(self)->library_scope=(int)number(control,"selectedSegmentIndex"); refresh(self); }

static id find_class(id root,const char *name,unsigned depth) {
    if (!root || depth>12) return nil;
    if (kind(root,name)) return root;
    id children=m0(root,"subviews");
    for (U i=0;i<number(children,"count");i++) { id found=find_class(at(children,i),name,depth+1); if (found) return found; }
    return nil;
}
static id container_for(State *s,id owner) {
    id result=object_field(owner,"emoticonPaletteContainerView",CONTAINER);
    if (result) return result;
    id footer=objc_loadWeakRetained(&s->footer),parent=m0(footer,"superview");
    for (unsigned i=0;parent && i<8;i++,parent=m0(parent,"superview")) if (kind(parent,CONTAINER)) { result=parent; break; }
    objc_release(footer); return result;
}
static void make_panel(id delegate) {
    State *s=state(delegate); if (s->panel) return;
    s->panel=view("UIView",(Rect){{0,0},{320,200}}); v1(s->panel,"setBackgroundColor:",color("secondarySystemBackgroundColor"));
    const char *providers[]={"All","7TV","BTTV","FFZ"},*scopes[]={"Channel","Global"};
    s->provider=segmented(delegate,providers,4,"ssProvider:"); s->scope=segmented(delegate,scopes,2,"ssScope:");
    v1(s->provider,"setAccessibilityLabel:",str("Emote provider")); v1(s->scope,"setAccessibilityLabel:",str("Emote scope"));
    v1(s->panel,"addSubview:",s->provider); v1(s->panel,"addSubview:",s->scope);
    id flow=m0((id)objc_getClass("UICollectionViewFlowLayout"),"new");
    ((void (*)(id,SEL,Size))objc_msgSend)(flow,sel_registerName("setItemSize:"),(Size){56,56});
    ((void (*)(id,SEL,double))objc_msgSend)(flow,sel_registerName("setMinimumInteritemSpacing:"),4.0);
    ((void (*)(id,SEL,double))objc_msgSend)(flow,sel_registerName("setMinimumLineSpacing:"),4.0);
    s->grid=((id (*)(id,SEL,Rect,id))objc_msgSend)(m0((id)objc_getClass("UICollectionView"),"alloc"),sel_registerName("initWithFrame:collectionViewLayout:"),(Rect){{0,76},{320,124}},flow); objc_release(flow);
    ((void (*)(id,SEL,Class,id))objc_msgSend)(s->grid,sel_registerName("registerClass:forCellWithReuseIdentifier:"),objc_getClass("UICollectionViewCell"),str("SSEmoteCell"));
    v1(s->grid,"setDataSource:",delegate); v1(s->grid,"setDelegate:",delegate); v1(s->grid,"setBackgroundColor:",color("clearColor"));
    vb(s->grid,"setAlwaysBounceVertical:",YES); v1(s->panel,"addSubview:",s->grid);
    s->empty=view("UILabel",(Rect){{16,88},{288,60}}); vi(s->empty,"setTextAlignment:",1); vi(s->empty,"setNumberOfLines:",2);
    v1(s->empty,"setTextColor:",color("secondaryLabelColor")); v1(s->panel,"addSubview:",s->empty);
}
static void restore_native(State *s) {
    m0(s->panel,"removeFromSuperview"); m0(s->recent_strip,"removeFromSuperview");
    id footer=objc_loadWeakRetained(&s->footer); vb(objc_getAssociatedObject(footer,&button_key),"setSelected:",NO); objc_release(footer);
    if (s->native_content) {
        vb(s->native_content,"setHidden:",s->native_was_hidden);
        if (kind(s->native_content,"UIScrollView")) ((void (*)(id,SEL,Insets))objc_msgSend)(s->native_content,sel_registerName("setContentInset:"),s->native_inset);
        objc_release(s->native_content); s->native_content=nil;
    }
}
static void layout(id delegate) {
    State *s=state(delegate); if (!s) return;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner),parent=m0(owner,"superview");
    if (!owner || !m0(owner,"window")) { m0(s->strip,"removeFromSuperview"); restore_native(s); objc_release(owner); return; }
    if (s->strip && parent) {
        Rect bounds=rect(owner,"bounds"),position=((Rect (*)(id,SEL,Rect,id))objc_msgSend)(owner,sel_registerName("convertRect:toView:"),bounds,parent);
        frame(s->strip,(Rect){{position.origin.x,position.origin.y-48},{position.size.width,48}});
        if (m0(s->strip,"superview")!=parent) v1(parent,"addSubview:",s->strip);
        vb(s->strip,"setHidden:",!yes(editor,"isFirstResponder") || !number(s->suggestions,"count"));
        v1(parent,"bringSubviewToFront:",s->strip);
    }
    id container=container_for(s,owner),footer=objc_loadWeakRetained(&s->footer);
    if (s->tab && container && footer && m0(container,"window")) {
        Rect bounds=rect(container,"bounds"),foot=((Rect (*)(id,SEL,Rect,id))objc_msgSend)(footer,sel_registerName("convertRect:toView:"),rect(footer,"bounds"),container);
        double height=foot.origin.y>0 && foot.origin.y<bounds.size.height ? foot.origin.y : bounds.size.height-48;
        if (height<0) height=0;
        if (s->tab==1) {
            if (m0(s->panel,"superview")!=container) v1(container,"addSubview:",s->panel);
            frame(s->panel,(Rect){{0,0},{bounds.size.width,height}});
            frame(s->provider,(Rect){{8,6},{bounds.size.width-16,28}}); frame(s->scope,(Rect){{8,40},{bounds.size.width-16,28}});
            frame(s->grid,(Rect){{4,76},{bounds.size.width-8,height>76 ? height-76 : 0}});
            frame(s->empty,(Rect){{12,80},{bounds.size.width-24,50}});
            /* The footer can have a full-height transparent hit-test region.
             * Keeping it above the panel makes visible emotes untappable and
             * forwards their touches to Twitch's keyboard-dismiss action.
             * The panel stops above the actual footer row. */
            v1(container,"bringSubviewToFront:",s->panel);
        } else if (s->tab==2 && s->recent_strip && number(s->entries,"count")) {
            if (m0(s->recent_strip,"superview")!=container) v1(container,"addSubview:",s->recent_strip);
            frame(s->recent_strip,(Rect){{0,0},{bounds.size.width,48}}); v1(container,"bringSubviewToFront:",s->recent_strip);
        }
    }
    objc_release(footer); objc_release(owner);
}
static void third_party_tab(id self,SEL sel,id sender) {
    (void)sel;(void)sender; State *s=state(self); restore_native(s); s->tab=1; make_panel(self);
    id owner=objc_loadWeakRetained(&s->owner),container=container_for(s,owner);
    id content=find_class(container,"UICollectionView",0);
    if (content && content!=s->grid) { s->native_content=objc_retain(content); s->native_was_hidden=yes(content,"isHidden"); vb(content,"setHidden:",YES); }
    id footer=objc_loadWeakRetained(&s->footer); vb(objc_getAssociatedObject(footer,&button_key),"setSelected:",YES); objc_release(footer);
    INC(palette_opens); refresh(self); objc_release(owner);
}
static void install_footer(id footer,id owner) {
    if (!footer || !owner) return;
    id delegate=delegate_for(owner); State *s=state(delegate); if (!s) return;
    id previous=objc_loadWeakRetained(&s->footer);
    if (previous!=footer) { restore_native(s); s->tab=0; objc_destroyWeak(&s->footer); objc_initWeak(&s->footer,footer); }
    objc_release(previous); associate(footer,&footer_key,delegate);
    id stack=object_field(footer,"emoteButtonsStackView","UIStackView");
    if (!stack || objc_getAssociatedObject(footer,&button_key)) return;
    id button=m0((id)objc_getClass("UIButton"),"new");
    id icon=m1((id)objc_getClass("UIImage"),"systemImageNamed:",str("face.smiling"));
    ((void (*)(id,SEL,id,U))objc_msgSend)(button,sel_registerName("setImage:forState:"),icon,(U)0);
    v1(button,"setAccessibilityLabel:",str("Third-party emotes")); v1(button,"setAccessibilityIdentifier:",str("StreamsideThirdPartyEmotes"));
    target(button,delegate,"ssThirdParty:",1UL<<6); v1(stack,"addArrangedSubview:",button); associate(footer,&button_key,button); objc_release(button);
}
static void find_footer(id owner) {
    id container=object_field(owner,"emoticonPaletteContainerView",CONTAINER);
    id footer=find_class(container,FOOTER,0); if (footer) install_footer(footer,owner);
}
static void refresh(id delegate) {
    State *s=state(delegate); if (!s || s->busy) return;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!owner || !m0(owner,"window")) { layout(delegate); objc_release(owner); return; }
    id room=room_for(owner);
    if (!equal(room,s->room)) {
        expand(delegate); objc_release(s->room); s->room=objc_retain(room); s->library_scope=0; vi(s->scope,"setSelectedSegmentIndex:",0);
    }
    find_footer(owner);
    if (yes(editor,"isFirstResponder") && !m0(editor,"markedTextRange")) {
        SSSpan old[MAX_TOKENS]; size_t n; Range caret=selection(editor);
        id plain=expanded_copy(editor,&caret,old,&n),text=m0(plain,"string"); U length=number(text,"length");
        uint16_t units[4096]; SSSpan completion={0,0}; id matches=nil;
        if (length<=4096 && !caret.length) {
            ((void (*)(id,SEL,uint16_t *,Range))objc_msgSend)(text,sel_registerName("getCharacters:range:"),units,(Range){0,length});
            if (ss_completion_span(units,length,caret.location,ss_composer_suggestion_mode(),&completion)) {
                Range query={completion.start,completion.length}; if (units[query.location]==':') { query.location++;query.length--; }
                matches=tas_emotes_picker_copy(s->room,0,-1,sub(text,query),24); s->completion=(Range){completion.start,completion.length};
            }
        }
        if (!equal(matches,s->suggestions)) {
            objc_release(s->suggestions); s->suggestions=matches;
            if (!s->strip) { s->strip=view("UIScrollView",(Rect){{0,0},{320,48}}); vb(s->strip,"setShowsHorizontalScrollIndicator:",NO); v1(s->strip,"setBackgroundColor:",color("secondarySystemBackgroundColor")); }
            fill_strip(s->strip,delegate,matches);
        } else { if (matches) objc_release(matches); refresh_strip_images(s->strip); }
        objc_release(plain);
    } else if (s->suggestions) { objc_release(s->suggestions); s->suggestions=nil; vb(s->strip,"setHidden:",YES); }
    if (s->tab) {
        id items=s->tab==1 ? tas_emotes_picker_copy(s->room,s->library,s->library_scope,nil,6500) : recents(s);
        if (!equal(items,s->entries)) {
            objc_release(s->entries); s->entries=items;
            if (s->tab==1) m0(s->grid,"reloadData");
            else {
                if (!s->recent_strip) { s->recent_strip=view("UIScrollView",(Rect){{0,0},{320,48}}); v1(s->recent_strip,"setBackgroundColor:",color("secondarySystemBackgroundColor")); }
                fill_strip(s->recent_strip,delegate,items);
                id buttons=m0(s->recent_strip,"subviews"); for (U i=0;i<number(buttons,"count");i++) {
                    id b=at(buttons,i);
                    ((void (*)(id,SEL,id,SEL,U))objc_msgSend)(b,sel_registerName("removeTarget:action:forControlEvents:"),delegate,sel_registerName("ssPick:"),(U)(1UL<<6));
                    target(b,delegate,"ssRecent:",1UL<<6);
                }
            }
        } else if (items) objc_release(items);
        if (s->tab==1) {
            vb(s->empty,"setHidden:",number(s->entries,"count")!=0);
            v1(s->empty,"setText:",str(s->library_scope ? "No global emotes available." : "No channel emotes available yet.\nUse Reload Emotes to refresh."));
            id cells=m0(s->grid,"visibleCells"); for (U i=0;i<number(cells,"count");i++) {
                id c=at(cells,i),path=m1(s->grid,"indexPathForCell:",c); U index=number(path,"item");
                if (path && index<number(s->entries,"count")) set_thumbnail(objc_getAssociatedObject(c,&cell_key),at(s->entries,index));
            }
        } else refresh_strip_images(s->recent_strip);
    }
    layout(delegate); objc_release(owner);
}
static void tick(id self,SEL sel,id notification) {
    (void)sel;(void)notification; State *s=state(self); if (!s) return;
    s->scheduled=NO; render(self); refresh(self);
    id owner=objc_loadWeakRetained(&s->owner);
    if (owner && m0(owner,"window") && (s->tab || yes(editor_for(owner),"isFirstResponder"))) {
        s->scheduled=YES;
        ((void (*)(id,SEL,SEL,id,double))objc_msgSend)(self,sel_registerName("performSelector:withObject:afterDelay:"),sel_registerName("ssTick:"),nil,1.0);
    }
    objc_release(owner);
}
static void image_changed(id self,SEL sel,id notification) {
    (void)sel;(void)notification; State *s=state(self); if (!s) return;
    render(self); refresh(self);
}
static void start_tick(id delegate) {
    State *s=state(delegate); if (!s || s->scheduled) return;
    s->scheduled=YES; ((void (*)(id,SEL,SEL,id,double))objc_msgSend)(delegate,sel_registerName("performSelector:withObject:afterDelay:"),sel_registerName("ssTick:"),nil,1.0);
}
static void delegate_dealloc(id self,SEL sel) {
    State *s=state(self);
    ((void (*)(id,SEL,id))objc_msgSend)((id)objc_getClass("NSObject"),sel_registerName("cancelPreviousPerformRequestsWithTarget:"),self);
    v1(m0((id)objc_getClass("NSNotificationCenter"),"defaultCenter"),"removeObserver:",self);
    if (s) {
        restore_native(s); m0(s->strip,"removeFromSuperview");
        id values[]={s->room,s->strip,s->suggestions,s->panel,s->grid,s->provider,s->scope,s->entries,s->empty,s->recent_strip};
        for (size_t i=0;i<sizeof(values)/sizeof(values[0]);i++) if (values[i]) objc_release(values[i]);
        objc_destroyWeak(&s->owner); objc_destroyWeak(&s->footer); free(s);
    }
    ((void (*)(id,SEL))original_dealloc)(self,sel);
}
static id delegate_for(id owner) {
    id existing=objc_getAssociatedObject(owner,&state_key); if (existing || !delegate_class) return existing;
    id delegate=m0((id)delegate_class,"new"); State *s=calloc(1,sizeof(*s));
    if (!s) { objc_release(delegate); return nil; }
    objc_initWeak(&s->owner,owner); objc_initWeak(&s->footer,nil);
    Ivar iv=class_getInstanceVariable(delegate_class,"_state"); memcpy((char *)delegate+ivar_getOffset(iv),&s,sizeof(s));
    associate(owner,&state_key,delegate);
    id undo=m0(editor_for(owner),"undoManager"); associate(undo,&undo_key,delegate);
    ((void (*)(id,SEL,id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSNotificationCenter"),"defaultCenter"),sel_registerName("addObserver:selector:name:object:"),delegate,sel_registerName("ssImages:"),str(IMAGE_NOTICE),nil);
    s->room=objc_retain(room_for(owner)); objc_release(delegate); return objc_getAssociatedObject(owner,&state_key);
}

static void did_change(id owner,SEL sel,id editor) {
    id delegate=delegate_for(owner); State *s=state(delegate);
    if (s && s->busy) return;
    if (s && !m0(editor,"markedTextRange")) expand(delegate);
    ((void (*)(id,SEL,id))original_change)(owner,sel,editor);
    INC(edited); if (s) { render(delegate); refresh(delegate); start_tick(delegate); }
}
static void did_select(id owner,SEL sel,id editor) {
    id delegate=delegate_for(owner); State *s=state(delegate);
    if (s && s->busy) return;
    if (s && !m0(editor,"markedTextRange")) expand(delegate);
    ((void (*)(id,SEL,id))original_selection)(owner,sel,editor);
    if (s) { render(delegate); refresh(delegate); }
}
static BOOL should_change(id owner,SEL sel,id editor,Range range,id replacement) {
    id delegate=delegate_for(owner); State *s=state(delegate);
    if (!s || s->busy || m0(editor,"markedTextRange")) return ((BOOL (*)(id,SEL,id,Range,id))original_should_change)(owner,sel,editor,range,replacement);
    SSSpan spans[MAX_TOKENS]; size_t n; Range mapped=range;
    id plain=expanded_copy(editor,&mapped,spans,&n); objc_release(plain);
    if (!n) return ((BOOL (*)(id,SEL,id,Range,id))original_should_change)(owner,sel,editor,range,replacement);
    /* Deleting a preview removes its complete emote code. */
    replace_plain(delegate,mapped,replacement); return NO;
}
static void did_begin(id owner,SEL sel,id editor) {
    ((void (*)(id,SEL,id))original_begin)(owner,sel,editor);
    id delegate=delegate_for(owner); if (delegate) { render(delegate); refresh(delegate); start_tick(delegate); }
}
static void did_end(id owner,SEL sel,id editor) {
    id delegate=objc_getAssociatedObject(owner,&state_key); if (delegate) expand(delegate);
    ((void (*)(id,SEL,id))original_end)(owner,sel,editor); if (delegate) refresh(delegate);
}
static void send_message(id owner,SEL sel) {
    id delegate=delegate_for(owner); if (delegate) { id editor=editor_for(owner); m0(editor,"unmarkText"); expand(delegate); ((void (*)(id,SEL,id))original_change)(owner,sel_registerName("textViewDidChange:"),editor); remember_typed(delegate); }
    ((void (*)(id,SEL))original_send)(owner,sel);
    if (delegate) { render(delegate); refresh(delegate); }
}
static void emoticon_tapped(id owner,SEL sel) {
    id delegate=delegate_for(owner); if (delegate) expand(delegate);
    ((void (*)(id,SEL))original_emoticon)(owner,sel);
    find_footer(owner); if (delegate) { render(delegate); refresh(delegate); start_tick(delegate); }
}
static void apply_input(id owner,SEL sel,id model) {
    id delegate=objc_getAssociatedObject(owner,&state_key); if (delegate) expand(delegate);
    ((void (*)(id,SEL,id))original_apply)(owner,sel,model);
    delegate=delegate_for(owner); if (delegate) { refresh(delegate); render(delegate); }
}
static void moved(id owner,SEL sel) {
    ((void (*)(id,SEL))original_move)(owner,sel);
    id delegate=delegate_for(owner); if (delegate) { refresh(delegate); start_tick(delegate); }
}
static void input_layout(id owner,SEL sel) {
    ((void (*)(id,SEL))original_layout)(owner,sel);
    id delegate=objc_getAssociatedObject(owner,&state_key); if (delegate) { find_footer(owner); layout(delegate); }
}
static id owner_above(id child) {
    for (unsigned i=0;child && i<20;i++,child=m0(child,"superview")) if (kind(child,INPUT)) return child;
    return nil;
}
static void footer_apply(id footer,SEL sel,id model) {
    ((void (*)(id,SEL,id))original_footer_apply)(footer,sel,model);
    install_footer(footer,owner_above(footer));
}
static void footer_moved(id footer,SEL sel) {
    ((void (*)(id,SEL))original_footer_move)(footer,sel);
    install_footer(footer,owner_above(footer));
}
static void container_layout(id container,SEL sel) {
    ((void (*)(id,SEL))original_container_layout)(container,sel);
    id footer=find_class(container,FOOTER,0),owner=owner_above(container);
    if (owner) install_footer(footer,owner);
    id delegate=objc_getAssociatedObject(footer,&footer_key); if (delegate) layout(delegate);
}
static void footer_action(id footer,SEL sel) {
    const char *names[]={"keyboardButtonPressed","recentEmotesButtonPressed","channelEmotesButtonPressed","allEmotesButtonPressed","backspaceButtonPressed"};
    size_t action=0; for (;action<5;action++) if (!strcmp(sel_getName(sel),names[action])) break;
    if (action==5) return;
    id delegate=objc_getAssociatedObject(footer,&footer_key); State *s=state(delegate);
    if (s) { if (action!=4) { restore_native(s); s->tab=0; } expand(delegate); }
    ((void (*)(id,SEL))original_footer_actions[action])(footer,sel);
    if (!s) return;
    if (action==1) {
        s->tab=2;
        id owner=objc_loadWeakRetained(&s->owner),container=container_for(s,owner),content=find_class(container,"UICollectionView",0);
        if (content && content!=s->grid) {
            s->native_content=objc_retain(content); s->native_was_hidden=yes(content,"isHidden");
            s->native_inset=((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("contentInset"));
            id recent=recents(s); BOOL has=number(recent,"count")>0; objc_release(recent);
            Insets inset=s->native_inset; if (has) inset.top+=48;
            ((void (*)(id,SEL,Insets))objc_msgSend)(content,sel_registerName("setContentInset:"),inset);
            if (has) ((void (*)(id,SEL,Point,BOOL))objc_msgSend)(content,sel_registerName("setContentOffset:animated:"),(Point){0,-inset.top},NO);
        }
        objc_release(owner);
    }
    render(delegate); refresh(delegate); start_tick(delegate);
}
static id editor_delegate(id editor) { id owner=owner_above(editor); return owner ? objc_getAssociatedObject(owner,&state_key) : nil; }
static void copy_text(id editor,SEL sel,id sender) {
    id delegate=editor_delegate(editor); if (delegate) expand(delegate);
    ((void (*)(id,SEL,id))original_copy)(editor,sel,sender); if (delegate) render(delegate);
}
static void cut_text(id editor,SEL sel,id sender) {
    id delegate=editor_delegate(editor); if (delegate) expand(delegate);
    ((void (*)(id,SEL,id))original_cut)(editor,sel,sender);
    if (delegate) { id owner=objc_loadWeakRetained(&state(delegate)->owner); ((void (*)(id,SEL,id))original_change)(owner,sel_registerName("textViewDidChange:"),editor); objc_release(owner); render(delegate); refresh(delegate); }
}
static void paste_text(id editor,SEL sel,id sender) {
    id delegate=editor_delegate(editor); if (delegate) expand(delegate);
    ((void (*)(id,SEL,id))original_paste)(editor,sel,sender); if (delegate) { render(delegate); refresh(delegate); }
}
static void undo_edit(id manager,SEL sel) {
    id delegate=objc_getAssociatedObject(manager,&undo_key); if (delegate) expand(delegate);
    IMP original=!strcmp(sel_getName(sel),"undo") ? original_undo : original_redo;
    ((void (*)(id,SEL))original)(manager,sel);
    if (delegate) { State *s=state(delegate); id owner=objc_loadWeakRetained(&s->owner); id editor=editor_for(owner); if (owner) ((void (*)(id,SEL,id))original_change)(owner,sel_registerName("textViewDidChange:"),editor); render(delegate); refresh(delegate); objc_release(owner); }
}
/* Validate complete type encodings, not only selector arity. Unknown app
 * versions leave the original implementation installed and report missing. */
static BOOL hook(const char *classname,const char *name,const char *encoding,IMP replacement,IMP *original) {
    if (*original) return YES;
    Class c=objc_getClass(classname); if (!c) return NO;
    SEL sel=sel_registerName(name); Method m=class_getInstanceMethod(c,sel);
    if (!m || strcmp(method_getTypeEncoding(m),encoding)) return NO;
    *original=method_getImplementation(m);
    if (!class_addMethod(c,sel,replacement,method_getTypeEncoding(m))) method_setImplementation(m,replacement);
    return YES;
}
void ss_composer_retry_hooks(void) {
    if (!tas_emotes_enabled_this_launch()) return;
    if (!delegate_class) {
        if (!objc_getClass("NSObject") || !objc_getClass("NSTextAttachment") || !objc_getClass("NSURLSession")) return;
        delegate_class=objc_allocateClassPair(objc_getClass("NSObject"),"SSComposerDelegate",0);
        attachment_class=objc_allocateClassPair(objc_getClass("NSTextAttachment"),"SSComposerAttachment",0);
        if (!delegate_class || !attachment_class) return;
        class_addIvar(delegate_class,"_state",sizeof(State *),3,"^v");
        original_dealloc=method_getImplementation(class_getInstanceMethod(objc_getClass("NSObject"),sel_registerName("dealloc")));
        struct { const char *selector; IMP imp; const char *types; } methods[]={
            {"dealloc",(IMP)delegate_dealloc,"v@:"}, {"ssPick:",(IMP)picker_button,"v@:@"},
            {"ssRecent:",(IMP)recent_button,"v@:@"}, {"ssProvider:",(IMP)provider_changed,"v@:@"},
            {"ssScope:",(IMP)scope_changed,"v@:@"}, {"ssThirdParty:",(IMP)third_party_tab,"v@:@"},
            {"ssTick:",(IMP)tick,"v@:@"}, {"ssImages:",(IMP)image_changed,"v@:@"},
            {"collectionView:numberOfItemsInSection:",(IMP)item_count,"q@:@q"},
            {"collectionView:cellForItemAtIndexPath:",(IMP)cell,"@@:@@"},
            {"collectionView:didSelectItemAtIndexPath:",(IMP)selected_cell,"v@:@@"}
        };
        for (size_t i=0;i<sizeof(methods)/sizeof(methods[0]);i++) class_addMethod(delegate_class,sel_registerName(methods[i].selector),methods[i].imp,methods[i].types);
        objc_registerClassPair(delegate_class); objc_registerClassPair(attachment_class);
        images=m0((id)objc_getClass("NSCache"),"new"); vi(images,"setCountLimit:",96); vi(images,"setTotalCostLimit:",16*1024*1024);
        pending=m0((id)objc_getClass("NSMutableDictionary"),"new"); failed=m0((id)objc_getClass("NSMutableDictionary"),"new");
        id config=m0((id)objc_getClass("NSURLSessionConfiguration"),"ephemeralSessionConfiguration");
        vi(config,"setHTTPMaximumConnectionsPerHost:",4); ((void (*)(id,SEL,double))objc_msgSend)(config,sel_registerName("setTimeoutIntervalForRequest:"),10.0);
        image_session=objc_retain(m1((id)objc_getClass("NSURLSession"),"sessionWithConfiguration:",config));
    }
    /* Install input callbacks as a group: rendering requires both validation
     * and didChange serialization. A partial compatible ABI cannot render. */
    Class c=objc_getClass(INPUT);
    const char *required[]={"textViewDidChange:","textViewDidChangeSelection:","textView:shouldChangeTextInRange:replacementText:","sendButtonTapped"};
    const char *types[]={"v24@0:8@16","v24@0:8@16","B48@0:8@16{_NSRange=QQ}24@40","v16@0:8"};
    for (size_t i=0;i<4;i++) { Method m=class_getInstanceMethod(c,sel_registerName(required[i])); if (!m || strcmp(method_getTypeEncoding(m),types[i])) return; }
    const char *edit_actions[]={"copy:","cut:","paste:"};
    for (size_t i=0;i<3;i++) { Method m=class_getInstanceMethod(objc_getClass(ENTRY),sel_registerName(edit_actions[i])); if (!m || strcmp(method_getTypeEncoding(m),"v24@0:8@16")) return; }
    hook(INPUT,required[0],types[0],(IMP)did_change,&original_change);
    hook(INPUT,required[1],types[1],(IMP)did_select,&original_selection);
    hook(INPUT,required[2],types[2],(IMP)should_change,&original_should_change);
    hook(INPUT,required[3],types[3],(IMP)send_message,&original_send);
    hook(INPUT,"textViewDidBeginEditing:","v24@0:8@16",(IMP)did_begin,&original_begin);
    hook(INPUT,"textViewDidEndEditing:","v24@0:8@16",(IMP)did_end,&original_end);
    hook(INPUT,"emoticonButtonTapped","v16@0:8",(IMP)emoticon_tapped,&original_emoticon);
    hook(INPUT,"apply:","v24@0:8@16",(IMP)apply_input,&original_apply);
    hook(INPUT,"didMoveToWindow","v16@0:8",(IMP)moved,&original_move);
    hook(INPUT,"layoutSubviews","v16@0:8",(IMP)input_layout,&original_layout);
    hook(FOOTER,"apply:","v24@0:8@16",(IMP)footer_apply,&original_footer_apply);
    hook(FOOTER,"didMoveToWindow","v16@0:8",(IMP)footer_moved,&original_footer_move);
    hook(CONTAINER,"layoutSubviews","v16@0:8",(IMP)container_layout,&original_container_layout);
    const char *actions[]={"keyboardButtonPressed","recentEmotesButtonPressed","channelEmotesButtonPressed","allEmotesButtonPressed","backspaceButtonPressed"};
    for (size_t i=0;i<5;i++) hook(FOOTER,actions[i],"v16@0:8",(IMP)footer_action,&original_footer_actions[i]);
    hook(ENTRY,"copy:","v24@0:8@16",(IMP)copy_text,&original_copy);
    hook(ENTRY,"cut:","v24@0:8@16",(IMP)cut_text,&original_cut);
    hook(ENTRY,"paste:","v24@0:8@16",(IMP)paste_text,&original_paste);
    hook("NSUndoManager","undo","v16@0:8",(IMP)undo_edit,&original_undo);
    hook("NSUndoManager","redo","v16@0:8",(IMP)undo_edit,&original_redo);
}
void ss_composer_status(char *buffer,size_t capacity) {
    if (!buffer || !capacity) return;
    snprintf(buffer,capacity,"\nStreamside composer (this launch)\n"
        "Hooks (editor/selection/validation/send/footer/copy/undo): %s/%s/%s/%s/%s/%s/%s\n"
        "Mode: %s\nEdits/previews/insertions/picker opens: %llu/%llu/%llu/%llu\n"
        "Identity layout misses/image failures: %llu/%llu\n"
        "Picker taps (grid/strip), missing selection/lookup: %llu/%llu, %llu/%llu\n"
        "Insertion veto/range miss/unchanged edit: %llu/%llu/%llu\n",
        original_change ? "installed":"missing",original_selection ? "installed":"missing",original_should_change ? "installed":"missing",
        original_send ? "installed":"missing",original_footer_apply ? "installed":"missing",original_copy ? "installed":"missing",original_undo && original_redo ? "installed":"missing",
        ss_composer_suggestion_mode()==0 ? "automatic" : ss_composer_suggestion_mode()==1 ? "colon":"off",
        (unsigned long long)GET(edited),(unsigned long long)GET(previewed),(unsigned long long)GET(insertions),(unsigned long long)GET(palette_opens),
        (unsigned long long)GET(identity_misses),(unsigned long long)GET(image_failures),
        (unsigned long long)GET(grid_taps),(unsigned long long)GET(strip_taps),
        (unsigned long long)GET(selection_missing),(unsigned long long)GET(lookup_misses),
        (unsigned long long)GET(validation_vetoes),(unsigned long long)GET(range_misses),(unsigned long long)GET(unchanged_edits));
}
