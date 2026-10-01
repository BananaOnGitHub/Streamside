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
#include <dlfcn.h>

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
#define NATIVE_AUTOCOMPLETE "_TtC6Twitch28ChatEmoteAutocompleteManager"
#define NATIVE_INFO "_TtCC6Twitch28ChatEmoteAutocompleteManagerP33_CEF95AD68D7B2CB9CDF93771963981BE9EmoteInfo"
#define NATIVE_SELECTOR "_TtC6Twitch29ChatSuggestionsListController"
static char state_key,footer_key,button_key,cell_key,grid_button_key,undo_key,attachment_metadata_key,recent_host_key;
static char selector_key;
static Class delegate_class,attachment_class,strip_class;
static IMP original_dealloc,original_change,original_selection,original_should_change;
static IMP original_begin,original_end,original_send,original_apply,original_move,original_layout,original_emoticon;
static IMP original_footer_apply,original_footer_move,original_container_layout,original_collection_layout;
static IMP original_flow_elements,original_flow_header;
static IMP original_selector_layout;
static IMP original_footer_actions[5],original_copy,original_cut,original_paste,original_undo,original_redo;
static IMP original_text,original_storage;
static id images,pending,failed,image_session;
static uint64_t edited,previewed,insertions,palette_opens,identity_misses,image_failures;
static uint64_t grid_taps,strip_taps,selection_missing,lookup_misses,validation_vetoes,range_misses,unchanged_edits;
static uint64_t native_snapshots,native_catalog_count,native_catalog_misses,native_insertions,selector_suppressions;
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
    id room,strip,suggestions,panel,grid,provider,scope,entries,empty,recent_strip,recent_entries;
    id footer; /* objc weak storage: the emote keyboard may be recreated */
    id native_content; /* retained only while an overlay uses it */
    id recent_content; /* objc weak storage: follows the native scroll view */
    double recent_height;
    BOOL placing_recents,recent_highlight_active;
    id recent_colors[6]; /* retained native footer appearance while overridden */
    Range completion;
    int library,library_scope,tab;
    BOOL busy,scheduled,preview_scheduled,native_was_hidden;
    id native_manager,stock_selector; /* weak, scoped to this input's chat */
    id native_entries,native_by_code,native_snapshot;
    uintptr_t native_marker;
    U native_generation;
    BOOL native_pending,native_ready,colon_selector,stock_hidden,stock_saved_hidden,stock_height_saved;
    double stock_height;
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
static void schedule_preview(id delegate);

/* Twitch 30.4.2's autocomplete publication bypasses its ObjC wrappers.
 * Read its catalog on its serial backgroundQueue, using the runtime's own
 * Array/String/URL bridging. Never interpret Swift string storage, construct
 * Swift models, or patch executable instructions. See NATIVE_EMOTES.md. */
#if defined(__aarch64__)
#define SWIFT_CALL __attribute__((swiftcall))
#else
#define SWIFT_CALL
#endif
typedef struct { const void *value; uintptr_t state; } MetadataResponse;
typedef id (SWIFT_CALL *BridgeValue)(const void *,const void *);
typedef MetadataResponse (SWIFT_CALL *ArrayMetadata)(uintptr_t,const void *);
typedef MetadataResponse (SWIFT_CALL *ValueMetadata)(uintptr_t);
static BridgeValue bridge_value;
static const void *native_array_type,*native_string_type,*native_url_type;
static void (*queue_async)(void *,void (^)(void));
static id (*native_weak_load)(void *);
static void (*native_unknown_release)(id);
static size_t swift_value_size(const void *metadata) {
    if (!metadata) return 0;
    const uintptr_t *witness=((const uintptr_t *const *)metadata)[-1];
    return witness ? witness[8] : 0;
}
static BOOL native_bridge_ready(void) {
    if (native_array_type) return YES;
    id version=m1(m0((id)objc_getClass("NSBundle"),"mainBundle"),"objectForInfoDictionaryKey:",str("CFBundleShortVersionString"));
    if (!equal(version,str("30.4.2"))) return NO;
    Class info=objc_getClass(NATIVE_INFO); if (!info) return NO;
    bridge_value=(BridgeValue)dlsym(RTLD_DEFAULT,"$ss27_bridgeAnythingToObjectiveCyyXlxlF");
    ArrayMetadata array=(ArrayMetadata)dlsym(RTLD_DEFAULT,"$sSaMa");
    ValueMetadata url=(ValueMetadata)dlsym(RTLD_DEFAULT,"$s10Foundation3URLVMa");
    const void *(*class_metadata)(Class)=(const void *(*)(Class))dlsym(RTLD_DEFAULT,"swift_getObjCClassMetadata");
    queue_async=(void (*)(void *,void (^)(void)))dlsym(RTLD_DEFAULT,"dispatch_async");
    native_weak_load=(id (*)(void *))dlsym(RTLD_DEFAULT,"swift_unknownObjectWeakLoadStrong");
    native_unknown_release=(void (*)(id))dlsym(RTLD_DEFAULT,"swift_unknownObjectRelease");
    native_string_type=dlsym(RTLD_DEFAULT,"$sSSN");
    if (!bridge_value || !array || !url || !class_metadata || !queue_async || !native_string_type || !native_weak_load || !native_unknown_release) return NO;
    const void *array_type=array(0,class_metadata(info)).value,*url_type=url(0).value;
    Ivar code=class_getInstanceVariable(info,"code"),image=class_getInstanceVariable(info,"url");
    size_t size=class_getInstanceSize(info),url_size=swift_value_size(url_type);
    if (!code || !image || ivar_getOffset(code)!=16 || ivar_getOffset(image)<32 ||
        (size_t)ivar_getOffset(image)>size || !url_size || url_size>size-(size_t)ivar_getOffset(image) ||
        swift_value_size(native_string_type)!=16 || swift_value_size(array_type)!=sizeof(void *)) return NO;
    native_array_type=array_type; native_url_type=url_type; return YES;
}
static id connection_for(id owner,id *selector) {
    if (selector) *selector=nil;
    /* The input delegate is a Swift weak class existential, not an ObjC weak
     * id. Use the exact runtime operation called by textViewDidChange. This
     * also reaches SkylineLiveChat, which is not in the responder chain. */
    id context=nil,result=nil;
    Ivar delegate=class_getInstanceVariable(object_getClass(owner),"delegate");
    if (delegate && ivar_getOffset(delegate)==424 && class_getInstanceSize(object_getClass(owner))>=440)
        context=native_weak_load((char *)owner+424);
    for (unsigned pass=0;pass<2 && !result;pass++) {
      id node=pass ? owner : context;
      for (unsigned i=0;node && i<64;i++) {
        id connection=nil;
        if (kind(node,"_TtC6Twitch18ChatViewController")) {
            connection=object_field(node,"connectionController","_TtC6Twitch24ChatConnectionController");
            if (selector) *selector=object_field(node,"suggestionsListController",NATIVE_SELECTOR);
        } else if (kind(node,"_TtC6Twitch15SkylineLiveChat")) {
            id chat=object_field(node,"$__lazy_storage_$_skylineChatView","_TtCC6Twitch15SkylineLiveChat15SkylineChatView");
            connection=object_field(chat,"chatConnectionController","_TtC6Twitch24ChatConnectionController");
            if (selector) *selector=object_field(node,"$__lazy_storage_$_suggestionsListController",NATIVE_SELECTOR);
        } else if (kind(node,"_TtCC6Twitch15SkylineLiveChat15SkylineChatView") ||
                   kind(node,"_TtC6Twitch11IRLChatView")) {
            connection=object_field(node,"chatConnectionController","_TtC6Twitch24ChatConnectionController");
        }
        if (connection) { result=objc_retain(connection); break; }
        node=responds(node,"nextResponder") ? m0(node,"nextResponder") : nil;
      }
    }
    if (context) native_unknown_release(context);
    return result;
}
static BOOL native_image_url(id url) {
    if (!kind(url,"NSString")) return NO;
    id parsed=m1((id)objc_getClass("NSURL"),"URLWithString:",url);
    return equal(m0(parsed,"scheme"),str("https")) && equal(m0(parsed,"host"),str("static-cdn.jtvnw.net")) &&
        ((BOOL (*)(id,SEL,id))objc_msgSend)(m0(parsed,"path"),sel_registerName("hasPrefix:"),str("/emoticons/"));
}
static void set_key(id dictionary,const char *name,id value) {
    if (value) ((void (*)(id,SEL,id,id))objc_msgSend)(dictionary,sel_registerName("setObject:forKey:"),value,str(name));
}
static id snapshot_native(id manager,id *snapshot) {
    if (snapshot) *snapshot=nil;
    Ivar iv=class_getInstanceVariable(object_getClass(manager),"emotes");
    if (!iv || ivar_getOffset(iv)!=16 || class_getInstanceSize(object_getClass(manager))<32) return nil;
    id array=bridge_value((char *)manager+ivar_getOffset(iv),native_array_type);
    if (!kind(array,"NSArray") || number(array,"count")>10000) { objc_release(array); return nil; }
    id result=m0((id)objc_getClass("NSMutableDictionary"),"new");
    Class info_class=objc_getClass(NATIVE_INFO);
    ptrdiff_t code_offset=ivar_getOffset(class_getInstanceVariable(info_class,"code"));
    ptrdiff_t url_offset=ivar_getOffset(class_getInstanceVariable(info_class,"url"));
    for (U i=0;i<number(array,"count");i++) {
        id info=at(array,i); if (object_getClass(info)!=info_class) continue;
        id code=bridge_value((char *)info+code_offset,native_string_type);
        id image=bridge_value((char *)info+url_offset,native_url_type);
        id url=kind(image,"NSURL") ? m0(image,"absoluteString") : nil;
        if (kind(code,"NSString") && number(code,"length") && number(code,"length")<=96 && native_image_url(url)) {
            id item=m0((id)objc_getClass("NSMutableDictionary"),"new");
            set_key(item,"name",code); set_key(item,"url",url); set_key(item,"native",code);
            /* Preserve the CDN's native identifier; never create a provider ID. */
            id parts=m0(image,"pathComponents");
            if (number(parts,"count")>3) set_key(item,"id",at(parts,3));
            set_key(result,((const char *(*)(id,SEL))objc_msgSend)(code,sel_registerName("UTF8String")),item);
            objc_release(item);
        }
        objc_release(image); objc_release(code);
    }
    /* Keep the bridged Array alive with the dictionary. Its immutable native
     * buffer forces Twitch's next publication to copy on write; pointer reuse
     * cannot make a changed catalog look identical to the previous snapshot. */
    if (snapshot) *snapshot=array; else objc_release(array);
    return result;
}
static void stock_update(State *s,id selector) {
    /* Presentation only: Twitch's async completion reloads this table and
     * scrolls to row 0 when its Swift match contains results (30.4.2,
     * 0x100e51c58 / 0x100e51cc8). Returning zero rows here violates that match
     * and makes UITableView raise an exception, even while its view is hidden.
     * Keep native rows, sections and match storage entirely under Twitch. */
    if (!s || !selector) return;
    BOOL suppress=s->colon_selector && s->native_ready && ss_composer_suggestion_mode()!=2;
    id stock=m0(selector,"viewIfLoaded"); if (!stock) return;
    id height=object_field(selector,"$__lazy_storage_$_preferredHeightConstraint","NSLayoutConstraint");
    if (suppress) {
        if (!s->stock_hidden) { s->stock_saved_hidden=yes(stock,"isHidden"); s->stock_hidden=YES; INC(selector_suppressions); }
        vb(stock,"setHidden:",YES);
        if (height) {
            double value=((double (*)(id,SEL))objc_msgSend)(height,sel_registerName("constant"));
            if (!s->stock_height_saved || value>0) { s->stock_height=value; s->stock_height_saved=YES; }
            ((void (*)(id,SEL,double))objc_msgSend)(height,sel_registerName("setConstant:"),0.0);
        }
    } else if (s->stock_hidden) {
        vb(stock,"setHidden:",s->stock_saved_hidden);
        if (height && s->stock_height_saved) ((void (*)(id,SEL,double))objc_msgSend)(height,sel_registerName("setConstant:"),s->stock_height);
        s->stock_hidden=NO; s->stock_height_saved=NO;
        m0(stock,"reloadData");
    }
}
static void selector_layout(id selector,SEL sel) {
    ((void (*)(id,SEL))original_selector_layout)(selector,sel);
    stock_update(state(objc_getAssociatedObject(selector,&selector_key)),selector);
}
static void request_native_catalog(id delegate,id owner) {
    State *s=state(delegate); if (!s || !native_bridge_ready()) return;
    id selector=nil,connection=connection_for(owner,&selector);
    id manager=object_field(connection,"emoteAutocompleteManager",NATIVE_AUTOCOMPLETE);
    id old=objc_loadWeakRetained(&s->native_manager);
    if (old!=manager) {
        objc_destroyWeak(&s->native_manager); objc_initWeak(&s->native_manager,manager);
        s->native_generation++; s->native_marker=0; s->native_ready=NO; s->native_pending=NO;
        objc_release(s->native_entries); s->native_entries=nil;
        objc_release(s->native_by_code); s->native_by_code=nil;
        objc_release(s->native_snapshot); s->native_snapshot=nil;
    }
    objc_release(old);
    id prior=objc_loadWeakRetained(&s->stock_selector);
    if (prior!=selector) {
        BOOL colon=s->colon_selector; s->colon_selector=NO; stock_update(s,prior); s->colon_selector=colon;
        if (prior) associate(prior,&selector_key,nil);
        objc_destroyWeak(&s->stock_selector); objc_initWeak(&s->stock_selector,selector);
        s->stock_hidden=NO; s->stock_height_saved=NO;
    }
    if (selector) associate(selector,&selector_key,delegate);
    objc_release(prior);
    objc_release(connection);
    if (!manager || s->native_pending) return;
    id queue=object_field(manager,"backgroundQueue","OS_dispatch_queue"); if (!queue) { INC(native_catalog_misses); return; }
    s->native_pending=YES;
    id held_delegate=objc_retain(delegate),held_manager=objc_retain(manager);
    U generation=s->native_generation; uintptr_t previous=s->native_marker;
    queue_async(queue,^{
        uintptr_t marker=0; memcpy(&marker,(char *)held_manager+16,sizeof(marker));
        id array=nil,catalog=marker && marker!=previous ? snapshot_native(held_manager,&array) : nil;
        ((void (*)(id,SEL,id))objc_msgSend)(m0((id)objc_getClass("NSOperationQueue"),"mainQueue"),sel_registerName("addOperationWithBlock:"),(id)^{
            State *current=state(held_delegate);
            if (current && current->native_generation==generation) {
                current->native_pending=NO;
                if (catalog) {
                    objc_release(current->native_by_code); current->native_by_code=objc_retain(catalog);
                    objc_release(current->native_entries); current->native_entries=objc_retain(m0(catalog,"allValues"));
                    objc_release(current->native_snapshot); current->native_snapshot=objc_retain(array);
                    current->native_marker=marker; current->native_ready=YES;
                    INC(native_snapshots); __atomic_store_n(&native_catalog_count,number(catalog,"count"),__ATOMIC_RELAXED);
                } else if (marker!=previous) INC(native_catalog_misses);
                /* No refresh here: it would continuously enqueue itself.
                 * The existing one-second tick and edits pick up the snapshot. */
            }
            objc_release(array); objc_release(catalog); objc_release(held_manager); objc_release(held_delegate);
        });
    });
}
static id native_named(State *s,id name) { return m1(s->native_by_code,"objectForKey:",name); }
static id unified_matches(State *s,id query) {
    id native=m0((id)objc_getClass("NSMutableArray"),"new");
    const char *prefix=((const char *(*)(id,SEL))objc_msgSend)(query,sel_registerName("UTF8String"));
    for (U i=0;i<number(s->native_entries,"count");i++) {
        id item=at(s->native_entries,i);
        const char *name=((const char *(*)(id,SEL))objc_msgSend)(key(item,"name"),sel_registerName("UTF8String"));
        if (ss_ascii_prefix(name,prefix)) v1(native,"addObject:",item);
    }
    /* Stable native ordering, then interleave both catalogs so one provider
     * cannot fill the entire compact result window. Native codes win overlap. */
    v1(native,"sortUsingComparator:",(id)^I(id a,id b) {
        return ((I (*)(id,SEL,id))objc_msgSend)(key(a,"name"),sel_registerName("caseInsensitiveCompare:"),key(b,"name"));
    });
    id providers=tas_emotes_picker_copy(s->room,0,-1,query,6500);
    id filtered=m0((id)objc_getClass("NSMutableArray"),"new");
    for (U i=0;i<number(providers,"count");i++) {
        id item=at(providers,i); if (!native_named(s,key(item,"name"))) v1(filtered,"addObject:",item);
    }
    id result=m0((id)objc_getClass("NSMutableArray"),"new");
    for (U i=0;number(result,"count")<64 && (i<number(native,"count") || i<number(filtered,"count"));i++) {
        if (i<number(native,"count")) v1(result,"addObject:",at(native,i));
        if (i<number(filtered,"count") && number(result,"count")<64) v1(result,"addObject:",at(filtered,i));
    }
    objc_release(native); objc_release(filtered); objc_release(providers); return result;
}

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
    if (!utf8 || !(tas_emotes_is_provider_image_url(utf8) || (key(metadata,"native") && native_image_url(url))) || cached_image(metadata) || key(pending,utf8) || number(pending,"count")>=8) return;
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
    U length=number(source,"length"),extra=0; id source_text=m0(source,"string"); *n=0;
    for (U i=0;i<length;i++) {
        if (((uint16_t (*)(id,SEL,U))objc_msgSend)(source_text,sel_registerName("characterAtIndex:"),i)!=0xfffc) continue;
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
/* Twitch's validation reads textStorage and its didChange bridge reads text.
 * Give those synchronous reads expanded names WITHOUT changing the live
 * editor. UIKit must apply its own edits using the original displayed ranges,
 * especially autocorrection of a word behind the caret. Scope to the main thread and
 * exact editor; unrelated editors and normal UIKit reads remain untouched. */
typedef struct NativeRead { id editor,plain,storage; struct NativeRead *previous; } NativeRead;
/* UIKit callbacks run on main. Check before touching this stack scope so a
 * background read can never see a temporary snapshot from the main thread. */
static NativeRead *native_read;
static BOOL main_thread(void) { return yes((id)objc_getClass("NSThread"),"isMainThread"); }
static id editor_text(id editor,SEL sel) {
    if (main_thread() && native_read && native_read->editor==editor) return m0(native_read->plain,"string");
    return ((id (*)(id,SEL))original_text)(editor,sel);
}
static id editor_storage(id editor,SEL sel) {
    if (main_thread() && native_read && native_read->editor==editor && native_read->storage) return native_read->storage;
    return ((id (*)(id,SEL))original_storage)(editor,sel);
}
static BOOL native_validation(id owner,SEL sel,id editor,Range range,id replacement) {
    if (!main_thread() || m0(editor,"markedTextRange")) return ((BOOL (*)(id,SEL,id,Range,id))original_should_change)(owner,sel,editor,range,replacement);
    SSSpan spans[MAX_TOKENS]; size_t n; Range mapped=range;
    id plain=expanded_copy(editor,&mapped,spans,&n);
    /* Keep the getter's concrete UIKit contract as well as its contents.
     * didChange needs only the text snapshot; its storage stays live. */
    id snapshot=n ? m1(m0((id)objc_getClass("NSTextStorage"),"alloc"),"initWithAttributedString:",plain) : nil;
    NativeRead read={editor,plain,snapshot,native_read};
    if (n) native_read=&read;
    BOOL allowed=((BOOL (*)(id,SEL,id,Range,id))original_should_change)(owner,sel,editor,n ? mapped : range,replacement);
    native_read=read.previous; objc_release(snapshot); objc_release(plain); return allowed;
}
static void native_changed(id owner,SEL sel,id editor) {
    if (!main_thread() || m0(editor,"markedTextRange")) { ((void (*)(id,SEL,id))original_change)(owner,sel,editor); return; }
    SSSpan spans[MAX_TOKENS]; size_t n;
    id plain=expanded_copy(editor,NULL,spans,&n);
    NativeRead read={editor,plain,nil,native_read};
    if (n) native_read=&read;
    ((void (*)(id,SEL,id))original_change)(owner,sel,editor);
    native_read=read.previous; objc_release(plain);
}
static void clean_typing_attributes(id editor) {
    id current=m0(editor,"typingAttributes");
    if (!key(current,ATTACHMENT_KEY)) return;
    id attributes=m0(current,"mutableCopy");
    v1(attributes,"removeObjectForKey:",str(ATTACHMENT_KEY)); v1(attributes,"removeObjectForKey:",str("NSAttachment"));
    v1(editor,"setTypingAttributes:",attributes); objc_release(attributes);
}
static void visual_text(id editor,id text,Range selected) {
    /* This is a direct text-storage presentation update, not a user edit.
     * Querying or toggling UITextView's undo manager here can throw while an
     * asynchronous image notification is being delivered (iOS 18.2). */
    id foreground=color("labelColor");
    id font=((id (*)(id,SEL,double))objc_msgSend)((id)objc_getClass("UIFont"),sel_registerName("systemFontOfSize:"),17.0);
    U length=number(text,"length");
    if (length) {
        ((void (*)(id,SEL,id,id,Range))objc_msgSend)(text,sel_registerName("addAttribute:value:range:"),str("NSFont"),font,(Range){0,length});
        ((void (*)(id,SEL,id,id,Range))objc_msgSend)(text,sel_registerName("addAttribute:value:range:"),str("NSColor"),foreground,(Range){0,length});
    }
    id storage=m0(editor,"textStorage"); m0(storage,"beginEditing");
    ((void (*)(id,SEL,Range,id))objc_msgSend)(storage,sel_registerName("replaceCharactersInRange:withAttributedString:"),(Range){0,number(storage,"length")},text);
    m0(storage,"endEditing");
    if (selected.location>length) selected.location=length;
    if (selected.length>length-selected.location) selected.length=length-selected.location;
    select_range(editor,selected);
    id typing=m0(m0(editor,"typingAttributes"),"mutableCopy");
    ((void (*)(id,SEL,id,id))objc_msgSend)(typing,sel_registerName("setObject:forKey:"),font,str("NSFont"));
    ((void (*)(id,SEL,id,id))objc_msgSend)(typing,sel_registerName("setObject:forKey:"),foreground,str("NSColor"));
    v1(editor,"setTypingAttributes:",typing); objc_release(typing);
}
static void expand(id delegate) {
    State *s=state(delegate); if (!s || s->busy || native_read) return;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!editor || m0(editor,"markedTextRange")) { objc_release(owner); return; }
    SSSpan spans[MAX_TOKENS]; size_t n; Range r=selection(editor);
    id plain=expanded_copy(editor,&r,spans,&n);
    if (n) { s->busy=YES; visual_text(editor,plain,r); s->busy=NO; }
    objc_release(plain); objc_release(owner);
}
static void render(id delegate) {
    State *s=state(delegate); if (!s || s->busy || s->preview_scheduled || native_read) return;
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
        /* Leave the word being typed/selected intact until a delimiter commits
         * it. A provider name can also be the prefix of an ordinary word. */
        BOOL existing=NO;
        for (size_t j=0;j<old_n;j++) if (old[j].start==start && old[j].length==end-start) { existing=YES; break; }
        if (!existing && yes(editor,"isFirstResponder") && !ss_preview_token_safe(start,end,length,r.location,r.length)) { start=end; continue; }
        id word=sub(text,(Range){start,end-start});
        id metadata=native_named(s,word) ? nil : tas_emotes_named_copy(s->room,word);
        id cached=metadata ? cached_image(metadata) : nil,attachment=nil;
        BOOL reused=NO;
        /* Reuse our existing decoded preview after cache eviction; do not keep
         * downloading it on every edit or replace identical attachments. */
        U original_position=ss_display_position(start,old,old_n);
        if (metadata && original_position<number(source,"length")) {
            id previous=((id (*)(id,SEL,id,U,Range *))objc_msgSend)(source,sel_registerName("attribute:atIndex:effectiveRange:"),str("NSAttachment"),original_position,NULL);
            id previous_metadata=objc_getAssociatedObject(previous,&attachment_metadata_key);
            if (previous_metadata && equal(key(previous_metadata,"id"),key(metadata,"id"))) { attachment=objc_retain(previous); reused=YES; }
        }
        if (metadata && !attachment) image_request(metadata);
        if (cached || attachment) {
            if (!attachment) { attachment=m0((id)attachment_class,"new"); v1(attachment,"setImage:",key(cached,"image")); associate(attachment,&attachment_metadata_key,metadata); }
            double height=22, width=22,aspect=((double (*)(id,SEL))objc_msgSend)(key(metadata,"aspect"),sel_registerName("doubleValue"));
            if (aspect<=0) { Size z=((Size (*)(id,SEL))objc_msgSend)(m0(attachment,"image"),sel_registerName("size")); if (z.height>0) aspect=z.width/z.height; }
            tas_emote_proportions(&width,&height,aspect);
            ((void (*)(id,SEL,Rect))objc_msgSend)(attachment,sel_registerName("setBounds:"),(Rect){{0,-4},{width,height}});
            /* Reuse the entire attributed character, including font/color.
             * Rebuilding it without those attributes made identical previews
             * compare unequal, rewriting the document on every refresh. */
            id item=reused ? ((id (*)(id,SEL,Range))objc_msgSend)(source,sel_registerName("attributedSubstringFromRange:"),(Range){original_position,1}) :
                m1((id)objc_getClass("NSAttributedString"),"attributedStringWithAttachment:",attachment);
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
        clean_typing_attributes(editor);
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
    BOOL allowed=native_validation(owner,sel_registerName("textView:shouldChangeTextInRange:replacementText:"),editor,range,replacement);
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
            if (changed) { native_changed(owner,sel_registerName("textViewDidChange:"),editor); INC(edited); }
            else { INC(unchanged_edits); allowed=NO; }
        } else { INC(range_misses); allowed=NO; }
    } else INC(validation_vetoes);
    render(delegate); refresh(delegate); objc_release(owner); return allowed;
}
static void choose(id delegate,id metadata,BOOL suggestion) {
    State *s=state(delegate); id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner);
    if (!editor || !metadata) { INC(selection_missing); objc_release(owner); return; }
    BOOL native=key(metadata,"native")!=nil;
    id current=native ? objc_retain(native_named(s,key(metadata,"name"))) : tas_emotes_named_copy(room_for(owner),key(metadata,"name"));
    if (!current) { INC(lookup_misses); refresh(delegate); objc_release(owner); return; }
    metadata=current;
    refresh(delegate);
    if (native) {
        id latest=native_named(s,key(metadata,"name"));
        if (!latest || !equal(key(latest,"id"),key(metadata,"id"))) {
            INC(lookup_misses); objc_release(current); objc_release(owner); return;
        }
    }
    /* The native palette can leave the editor unfocused. Make it the active
     * text input before asking Twitch to validate and apply the edit. */
    m0(editor,"becomeFirstResponder");
    Range r=selection(editor); SSSpan spans[MAX_TOKENS]; size_t n;
    id plain=expanded_copy(editor,&r,spans,&n); objc_release(plain);
    if (suggestion) r=s->completion;
    id code=m1(key(metadata,"name"),"stringByAppendingString:",str(" "));
    /* The same validated UITextInput edit + native didChange path as Twitch's
     * own completion. Its formatter/history/send tokenization owns native IDs.
     * Only provider choices enter Streamside's third-party recent row. */
    if (replace_plain(delegate,r,code)) { if (native) INC(native_insertions); else remember(key(metadata,"name")); INC(insertions); }
    objc_release(current); objc_release(owner);
}

static void target(id control,id delegate,const char *action,U events) {
    ((void (*)(id,SEL,id,SEL,U))objc_msgSend)(control,sel_registerName("addTarget:action:forControlEvents:"),delegate,sel_registerName(action),events);
}
static id thumbnail_button(id delegate,id metadata,Rect r,const char *action) {
    id button=view("UIButton",r); associate(button,&button_key,metadata);
    id image=view(objc_getClass("FLAnimatedImageView") ? "FLAnimatedImageView" : "UIImageView",(Rect){{6,3},{r.size.width-12,30}});
    vi(image,"setContentMode:",1); vb(image,"setUserInteractionEnabled:",NO); set_thumbnail(image,metadata);
    v1(button,"addSubview:",image); objc_release(image);
    id label=view("UILabel",(Rect){{2,33},{r.size.width-4,13}});
    v1(label,"setText:",key(metadata,"name")); vi(label,"setTextAlignment:",1);
    v1(label,"setFont:",((id (*)(id,SEL,double))objc_msgSend)((id)objc_getClass("UIFont"),sel_registerName("systemFontOfSize:"),10.0));
    v1(label,"setTextColor:",color("secondaryLabelColor")); v1(button,"addSubview:",label); objc_release(label);
    v1(button,"setAccessibilityLabel:",key(metadata,"name")); target(button,delegate,action,1UL<<6); return button;
}
static BOOL strip_cancel_touch(id self,SEL sel,id content) {
    (void)self;(void)sel;(void)content;
    /* UIScrollView normally refuses to cancel tracking inside UIControls.
     * Every emote tile is a UIButton. Our own strip lets a drag cancel the
     * button so swiping scrolls, while a stationary touch still taps it. */
    return YES;
}
static void configure_strip(id scroll) {
    vb(scroll,"setScrollEnabled:",YES);
    vb(scroll,"setCanCancelContentTouches:",YES);
    vb(scroll,"setDelaysContentTouches:",NO);
    vb(scroll,"setAlwaysBounceHorizontal:",YES);
    vb(scroll,"setAlwaysBounceVertical:",NO);
    vb(scroll,"setDirectionalLockEnabled:",YES);
    vb(scroll,"setShowsHorizontalScrollIndicator:",YES);
    vb(scroll,"setShowsVerticalScrollIndicator:",NO);
    vi(scroll,"setKeyboardDismissMode:",0);
    v1(scroll,"setBackgroundColor:",color("secondarySystemBackgroundColor"));
}
static id make_strip(void) {
    if (!strip_class) {
        Class base=objc_getClass("UIScrollView"); if (!base) return nil;
        Method cancel=class_getInstanceMethod(base,sel_registerName("touchesShouldCancelInContentView:"));
        if (!cancel) return nil;
        Class created=objc_allocateClassPair(base,"SSComposerScrollView",0); if (!created) return nil;
        class_addMethod(created,sel_registerName("touchesShouldCancelInContentView:"),(IMP)strip_cancel_touch,method_getTypeEncoding(cancel));
        objc_registerClassPair(created); strip_class=created;
    }
    id scroll=((id (*)(id,SEL,Rect))objc_msgSend)(m0((id)strip_class,"alloc"),sel_registerName("initWithFrame:"),(Rect){{0,0},{320,48}});
    configure_strip(scroll); return scroll;
}
static void set_strip_extent(id scroll,U count) {
    ((void (*)(id,SEL,Size))objc_msgSend)(scroll,sel_registerName("setContentSize:"),(Size){(double)count*64,48});
    /* A different search starts at its first result. Image-only refreshes do
     * not refill the strip, so they preserve dragging/deceleration/offset. */
    ((void (*)(id,SEL,Point))objc_msgSend)(scroll,sel_registerName("setContentOffset:"),(Point){0,0});
}
static void fill_strip(id scroll,id delegate,id items,const char *action) {
    id children=m0(m0(scroll,"subviews"),"copy");
    for (U i=0;i<number(children,"count");i++) if (objc_getAssociatedObject(at(children,i),&button_key)) m0(at(children,i),"removeFromSuperview"); objc_release(children);
    for (U i=0;i<number(items,"count");i++) {
        /* Wire only the UIButton we create. UIScrollView also owns indicator
         * subviews, which are not UIControls and cannot receive target APIs. */
        id button=thumbnail_button(delegate,at(items,i),(Rect){{(double)i*64,0},{64,48}},action);
        v1(scroll,"addSubview:",button); objc_release(button);
    }
    set_strip_extent(scroll,number(items,"count"));
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
static void grid_button(id self,SEL sel,id sender) { (void)sel; INC(grid_taps); choose(self,objc_getAssociatedObject(sender,&button_key),NO); }
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
        id button=view("UIButton",(Rect){{0,0},{56,56}});
        target(button,self,"ssGridPick:",1UL<<6);
        v1(content,"addSubview:",button); associate(c,&grid_button_key,button); objc_release(button);
    }
    id metadata=index<number(s->entries,"count") ? at(s->entries,index) : nil;
    id button=objc_getAssociatedObject(c,&grid_button_key);
    associate(button,&button_key,metadata);
    v1(button,"setAccessibilityLabel:",key(metadata,"name"));
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
static void restore_recent_highlight(State *s);
static void restore_native(State *s) {
    restore_recent_highlight(s);
    m0(s->panel,"removeFromSuperview");
    id footer=objc_loadWeakRetained(&s->footer); vb(objc_getAssociatedObject(footer,&button_key),"setSelected:",NO); objc_release(footer);
    if (s->native_content) {
        vb(s->native_content,"setHidden:",s->native_was_hidden);
        objc_release(s->native_content); s->native_content=nil;
    }
}
/* The provider Recent row belongs to the native library's scroll content,
 * not the container/footer overlay. It precedes native Recent cells without
 * adding fake Swift sections or changing the collection's data source. Native
 * section anchors already account for contentInset (Twitch 30.4.2). */
static id recent_footer_view(id footer,U index) {
    const char *names[]={"$__lazy_storage_$_recentEmotesButton","$__lazy_storage_$_channelEmotesButton",
        "$__lazy_storage_$_allEmotesButton","recentEmotesHighlight","channelEmotesHighlight","allEmotesHighlight"};
    return index<6 ? object_field(footer,names[index],index<3 ? "UIButton":"UIView") : nil;
}
static void restore_recent_highlight(State *s) {
    if (!s->recent_highlight_active) return;
    id footer=objc_loadWeakRetained(&s->footer);
    for (U i=0;i<6;i++) {
        v1(recent_footer_view(footer,i),i<3 ? "setTintColor:":"setBackgroundColor:",s->recent_colors[i]);
        objc_release(s->recent_colors[i]); s->recent_colors[i]=nil;
    }
    s->recent_highlight_active=NO; objc_release(footer);
}
static void update_recent_highlight(State *s,id content) {
    /* Native scroll callbacks continue to own every native section. The added
     * row also counts as Recent, including when Twitch has no native recents.
     * Override only UIKit colors while that row leads the visible content;
     * never change the Swift model/selected byte used by native navigation. */
    BOOL visible=content && s->recent_height && s->tab!=1 && !yes(content,"isHidden") && rect(content,"bounds").origin.y<0;
    if (!visible) { restore_recent_highlight(s); return; }
    if (s->recent_highlight_active) return;
    id footer=objc_loadWeakRetained(&s->footer);
    id buttons[6]; BOOL complete=YES;
    for (U i=0;i<6;i++) { buttons[i]=recent_footer_view(footer,i); if (!buttons[i]) complete=NO; }
    id native_recent=complete ? m0(buttons[3],"backgroundColor") : nil;
    id active=complete ? m0(buttons[4],"backgroundColor") : nil;
    if (!active && complete) active=m0(buttons[5],"backgroundColor");
    if (complete && !native_recent && active) {
        for (U i=0;i<6;i++) s->recent_colors[i]=objc_retain(m0(buttons[i],i<3 ? "tintColor":"backgroundColor"));
        s->recent_highlight_active=YES;
        v1(buttons[0],"setTintColor:",active);
        v1(buttons[1],"setTintColor:",s->recent_colors[0]); v1(buttons[2],"setTintColor:",s->recent_colors[0]);
        v1(buttons[3],"setBackgroundColor:",active); v1(buttons[4],"setBackgroundColor:",nil); v1(buttons[5],"setBackgroundColor:",nil);
    }
    objc_release(footer);
}
static void place_recent_strip(State *s,id content) {
    if (!s || !content || s->placing_recents) return;
    s->placing_recents=YES;
    double height=number(s->recent_entries,"count") && s->recent_strip ? 48 : 0;
    if (height!=s->recent_height) {
        Insets inset=((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("contentInset"));
        Insets adjusted=responds(content,"adjustedContentInset") ?
            ((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("adjustedContentInset")) : inset;
        Point offset=((Point (*)(id,SEL))objc_msgSend)(content,sel_registerName("contentOffset"));
        BOOL at_top=offset.y<=-adjusted.top+1 || (!s->recent_height && offset.y<=1);
        inset.top+=height-s->recent_height;
        s->recent_height=height; /* Set before UIKit's synchronous callbacks. */
        ((void (*)(id,SEL,Insets))objc_msgSend)(content,sel_registerName("setContentInset:"),inset);
        /* Initial opening includes recents. Changes while browsing preserve
         * the existing offset; repeated layouts never stop a user swipe. */
        if (at_top) {
            adjusted=responds(content,"adjustedContentInset") ?
                ((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("adjustedContentInset")) : inset;
            offset.y=-adjusted.top;
            ((void (*)(id,SEL,Point))objc_msgSend)(content,sel_registerName("setContentOffset:"),offset);
        }
    }
    if (height) {
        Rect bounds=rect(content,"bounds"),position={{bounds.origin.x,-height},{bounds.size.width,height}};
        if (m0(s->recent_strip,"superview")!=content) v1(content,"addSubview:",s->recent_strip);
        Rect old=rect(s->recent_strip,"frame");
        if (memcmp(&old,&position,sizeof(position))) frame(s->recent_strip,position);
        v1(content,"bringSubviewToFront:",s->recent_strip);
    } else m0(s->recent_strip,"removeFromSuperview");
    s->placing_recents=NO; update_recent_highlight(s,content);
}
static void detach_recents(State *s) {
    restore_recent_highlight(s);
    id content=objc_loadWeakRetained(&s->recent_content);
    if (content) {
        associate(content,&recent_host_key,nil);
        if (s->recent_height) {
            Insets inset=((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("contentInset"));
            inset.top-=s->recent_height; s->recent_height=0;
            ((void (*)(id,SEL,Insets))objc_msgSend)(content,sel_registerName("setContentInset:"),inset);
        }
    }
    s->recent_height=0; m0(s->recent_strip,"removeFromSuperview");
    objc_destroyWeak(&s->recent_content); objc_initWeak(&s->recent_content,nil); objc_release(content);
}
static void bind_recents(id delegate,id container) {
    State *s=state(delegate); if (!s || s->placing_recents) return;
    id content=find_class(container,"UICollectionView",0);
    if (content==s->grid) content=nil;
    id previous=objc_loadWeakRetained(&s->recent_content);
    if (previous!=content) {
        detach_recents(s);
        objc_destroyWeak(&s->recent_content); objc_initWeak(&s->recent_content,content);
        if (content) associate(content,&recent_host_key,delegate);
    }
    objc_release(previous); place_recent_strip(s,content);
}
static void refresh_recents(id delegate) {
    State *s=state(delegate); id items=recents(s);
    if (!equal(items,s->recent_entries)) {
        objc_release(s->recent_entries); s->recent_entries=items;
        if (!s->recent_strip && number(items,"count")) s->recent_strip=make_strip();
        if (s->recent_strip) {
            fill_strip(s->recent_strip,delegate,items,"ssRecent:");
        }
    } else { objc_release(items); refresh_strip_images(s->recent_strip); }
}
static void place_suggestion_strip(State *s,id owner,id editor,Rect position,Rect bounds) {
    if (!s->strip) return;
    id window=m0(owner,"window");
    if (!window) { m0(s->strip,"removeFromSuperview"); return; }
    Rect strip={{position.origin.x,position.origin.y-48},{position.size.width,48}};
    BOOL contained=strip.size.width>0 && strip.origin.x>=bounds.origin.x && strip.origin.y>=bounds.origin.y &&
        strip.origin.x+strip.size.width<=bounds.origin.x+bounds.size.width &&
        strip.origin.y+strip.size.height<=bounds.origin.y+bounds.size.height;
    /* A visible child outside the chat parent's bounds never participates in
     * UIKit hit testing, even with clipping disabled. Attach only this narrow
     * strip to the owner's scene window: its full touch area is inside its
     * parent, and chat's tap-to-dismiss recognizers are no longer ancestors. */
    frame(s->strip,strip);
    if (m0(s->strip,"superview")!=window) v1(window,"addSubview:",s->strip);
    vb(s->strip,"setHidden:",!contained || !yes(editor,"isFirstResponder") || !number(s->suggestions,"count"));
    v1(window,"bringSubviewToFront:",s->strip);
}
static void layout(id delegate) {
    State *s=state(delegate); if (!s) return;
    id owner=objc_loadWeakRetained(&s->owner),editor=editor_for(owner),window=m0(owner,"window");
    if (!owner || !window) { m0(s->strip,"removeFromSuperview"); restore_native(s); objc_release(owner); return; }
    if (s->strip) {
        Rect position=((Rect (*)(id,SEL,Rect,id))objc_msgSend)(owner,sel_registerName("convertRect:toView:"),rect(owner,"bounds"),window);
        place_suggestion_strip(s,owner,editor,position,rect(window,"bounds"));
    }
    id container=container_for(s,owner),footer=objc_loadWeakRetained(&s->footer);
    if (container && m0(container,"window")) bind_recents(delegate,container);
    if (s->tab==1 && container && footer && m0(container,"window")) {
        Rect bounds=rect(container,"bounds"),foot=((Rect (*)(id,SEL,Rect,id))objc_msgSend)(footer,sel_registerName("convertRect:toView:"),rect(footer,"bounds"),container);
        double height=foot.origin.y>0 && foot.origin.y<bounds.size.height ? foot.origin.y : bounds.size.height-48;
        if (height<0) height=0;
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
    request_native_catalog(delegate,owner);
    s->colon_selector=NO;
    find_footer(owner);
    if (yes(editor,"isFirstResponder") && !m0(editor,"markedTextRange")) {
        SSSpan old[MAX_TOKENS]; size_t n; Range caret=selection(editor);
        id plain=expanded_copy(editor,&caret,old,&n),text=m0(plain,"string"); U length=number(text,"length");
        uint16_t units[4096]; SSSpan completion={0,0}; id matches=nil;
        if (length<=4096 && !caret.length) {
            ((void (*)(id,SEL,uint16_t *,Range))objc_msgSend)(text,sel_registerName("getCharacters:range:"),units,(Range){0,length});
            if (ss_completion_span(units,length,caret.location,ss_composer_suggestion_mode(),&completion)) {
                Range query={completion.start,completion.length}; if (units[query.location]==':') { s->colon_selector=YES; query.location++;query.length--; }
                matches=unified_matches(s,sub(text,query)); s->completion=(Range){completion.start,completion.length};
            }
        }
        if (!equal(matches,s->suggestions)) {
            objc_release(s->suggestions); s->suggestions=matches;
            if (!s->strip) s->strip=make_strip();
            fill_strip(s->strip,delegate,matches,"ssPick:");
        } else { if (matches) objc_release(matches); refresh_strip_images(s->strip); }
        objc_release(plain);
    } else if (s->suggestions) { objc_release(s->suggestions); s->suggestions=nil; vb(s->strip,"setHidden:",YES); }
    id selector=objc_loadWeakRetained(&s->stock_selector); stock_update(s,selector); objc_release(selector);
    refresh_recents(delegate);
    if (s->tab==1) {
        id items=tas_emotes_picker_copy(s->room,s->library,s->library_scope,nil,6500);
        if (!equal(items,s->entries)) {
            objc_release(s->entries); s->entries=items; m0(s->grid,"reloadData");
        } else if (items) objc_release(items);
        vb(s->empty,"setHidden:",number(s->entries,"count")!=0);
        v1(s->empty,"setText:",str(s->library_scope ? "No global emotes available." : "No channel emotes available yet.\nUse Reload Emotes to refresh."));
        id cells=m0(s->grid,"visibleCells"); for (U i=0;i<number(cells,"count");i++) {
            id c=at(cells,i),path=m1(s->grid,"indexPathForCell:",c); U index=number(path,"item");
            if (path && index<number(s->entries,"count")) set_thumbnail(objc_getAssociatedObject(c,&cell_key),at(s->entries,index));
        }
    }
    layout(delegate); objc_release(owner);
}
static BOOL visible_in_window(id view) {
    if (!m0(view,"window")) return NO;
    for (unsigned i=0;view && i<24;i++,view=m0(view,"superview")) if (yes(view,"isHidden")) return NO;
    return YES;
}
static void tick(id self,SEL sel,id notification) {
    (void)sel;(void)notification; State *s=state(self); if (!s) return;
    s->scheduled=NO; refresh(self);
    id owner=objc_loadWeakRetained(&s->owner);
    id content=objc_loadWeakRetained(&s->recent_content);
    BOOL native_open=content && visible_in_window(content);
    if (owner && m0(owner,"window") && (s->tab || native_open || yes(editor_for(owner),"isFirstResponder"))) {
        s->scheduled=YES;
        ((void (*)(id,SEL,SEL,id,double))objc_msgSend)(self,sel_registerName("performSelector:withObject:afterDelay:"),sel_registerName("ssTick:"),nil,1.0);
    }
    objc_release(content); objc_release(owner);
}
static void image_changed(id self,SEL sel,id notification) {
    (void)sel;(void)notification; State *s=state(self); if (!s) return;
    schedule_preview(self); refresh(self);
}
static void preview_ready(id self,SEL sel,id object) {
    (void)sel;(void)object; State *s=state(self); if (!s) return;
    s->preview_scheduled=NO; render(self); refresh(self);
}
static void schedule_preview(id delegate) {
    State *s=state(delegate); if (!s) return;
    SEL action=sel_registerName("ssPreview:");
    ((void (*)(id,SEL,id,SEL,id))objc_msgSend)((id)objc_getClass("NSObject"),sel_registerName("cancelPreviousPerformRequestsWithTarget:selector:object:"),delegate,action,nil);
    s->preview_scheduled=YES;
    ((void (*)(id,SEL,SEL,id,double))objc_msgSend)(delegate,sel_registerName("performSelector:withObject:afterDelay:"),action,nil,0.35);
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
        s->colon_selector=NO;
        id selector=objc_loadWeakRetained(&s->stock_selector); stock_update(s,selector); associate(selector,&selector_key,nil); objc_release(selector);
        restore_native(s); detach_recents(s); m0(s->strip,"removeFromSuperview");
        id values[]={s->room,s->strip,s->suggestions,s->panel,s->grid,s->provider,s->scope,s->entries,s->empty,s->recent_strip,s->recent_entries,s->native_entries,s->native_by_code,s->native_snapshot};
        for (size_t i=0;i<sizeof(values)/sizeof(values[0]);i++) if (values[i]) objc_release(values[i]);
        objc_destroyWeak(&s->owner); objc_destroyWeak(&s->footer); objc_destroyWeak(&s->recent_content);
        objc_destroyWeak(&s->native_manager); objc_destroyWeak(&s->stock_selector); free(s);
    }
    ((void (*)(id,SEL))original_dealloc)(self,sel);
}
static id delegate_for(id owner) {
    id existing=objc_getAssociatedObject(owner,&state_key); if (existing || !delegate_class) return existing;
    id delegate=m0((id)delegate_class,"new"); State *s=calloc(1,sizeof(*s));
    if (!s) { objc_release(delegate); return nil; }
    objc_initWeak(&s->owner,owner); objc_initWeak(&s->footer,nil); objc_initWeak(&s->recent_content,nil);
    objc_initWeak(&s->native_manager,nil); objc_initWeak(&s->stock_selector,nil);
    Ivar iv=class_getInstanceVariable(delegate_class,"_state"); memcpy((char *)delegate+ivar_getOffset(iv),&s,sizeof(s));
    associate(owner,&state_key,delegate);
    id undo=m0(editor_for(owner),"undoManager"); associate(undo,&undo_key,delegate);
    ((void (*)(id,SEL,id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSNotificationCenter"),"defaultCenter"),sel_registerName("addObserver:selector:name:object:"),delegate,sel_registerName("ssImages:"),str(IMAGE_NOTICE),nil);
    s->room=objc_retain(room_for(owner)); objc_release(delegate); return objc_getAssociatedObject(owner,&state_key);
}

static void did_change(id owner,SEL sel,id editor) {
    id delegate=delegate_for(owner); State *s=state(delegate);
    if (s && s->busy) return;
    if (s) schedule_preview(delegate);
    native_changed(owner,sel,editor);
    INC(edited); if (s) { refresh(delegate); start_tick(delegate); }
}
static void did_select(id owner,SEL sel,id editor) {
    id delegate=delegate_for(owner); State *s=state(delegate);
    if (s && s->busy) return;
    if (s) schedule_preview(delegate);
    ((void (*)(id,SEL,id))original_selection)(owner,sel,editor);
    if (s) clean_typing_attributes(editor);
    if (s) refresh(delegate);
}
static BOOL should_change(id owner,SEL sel,id editor,Range range,id replacement) {
    id delegate=delegate_for(owner); State *s=state(delegate);
    if (!s || s->busy || m0(editor,"markedTextRange")) return ((BOOL (*)(id,SEL,id,Range,id))original_should_change)(owner,sel,editor,range,replacement);
    schedule_preview(delegate);
    /* Validation sees expanded names; UIKit applies the original displayed
     * range. Deleting one attachment naturally deletes one complete emote.
     * Never replaceRange or force selectedRange for keyboard/autocorrect. */
    return native_validation(owner,sel,editor,range,replacement);
}
static void did_begin(id owner,SEL sel,id editor) {
    ((void (*)(id,SEL,id))original_begin)(owner,sel,editor);
    id delegate=delegate_for(owner); if (delegate) { schedule_preview(delegate); refresh(delegate); start_tick(delegate); }
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
    id delegate=objc_getAssociatedObject(owner,&state_key); State *s=state(delegate);
    if (s && !s->preview_scheduled) expand(delegate);
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
    State *s=state(objc_getAssociatedObject(footer,&footer_key));
    if (s) restore_recent_highlight(s);
    ((void (*)(id,SEL,id))original_footer_apply)(footer,sel,model);
    install_footer(footer,owner_above(footer));
    if (s) { id content=objc_loadWeakRetained(&s->recent_content); update_recent_highlight(s,content); objc_release(content); }
}
static void footer_moved(id footer,SEL sel) {
    ((void (*)(id,SEL))original_footer_move)(footer,sel);
    install_footer(footer,owner_above(footer));
}
/* The extra scroll inset reserves the provider row, but must not become the
 * pinning offset for every native header. Recompute only pinned headers from
 * their unchanged native cell geometry. Copies keep UIKit's cached attributes
 * intact, and the absolute calculation is idempotent across both query paths. */
static id recent_header_attributes(id flow,id attributes) {
    id content=m0(flow,"collectionView");
    id delegate=objc_getAssociatedObject(content,&recent_host_key);
    State *s=delegate ? state(delegate) : NULL;
    if (!s || !s->recent_height || !attributes || !yes(flow,"sectionHeadersPinToVisibleBounds") ||
        !equal(m0(attributes,"representedElementKind"),str("UICollectionElementKindSectionHeader"))) return attributes;
    id path=m0(attributes,"indexPath"); I section=(I)number(path,"section");
    I count=((I (*)(id,SEL,I))objc_msgSend)(content,sel_registerName("numberOfItemsInSection:"),section);
    if (count<=0) return attributes;
    id paths=(id)objc_getClass("NSIndexPath");
    id first_path=((id (*)(id,SEL,I,I))objc_msgSend)(paths,sel_registerName("indexPathForItem:inSection:"),0,section);
    id last_path=((id (*)(id,SEL,I,I))objc_msgSend)(paths,sel_registerName("indexPathForItem:inSection:"),count-1,section);
    id first=m1(flow,"layoutAttributesForItemAtIndexPath:",first_path);
    id last=m1(flow,"layoutAttributesForItemAtIndexPath:",last_path);
    if (!first || !last) return attributes;
    Insets section_inset=((Insets (*)(id,SEL))objc_msgSend)(flow,sel_registerName("sectionInset"));
    id native_delegate=m0(content,"delegate");
    SEL inset_selector=sel_registerName("collectionView:layout:insetForSectionAtIndex:");
    Method inset_method=native_delegate ? class_getInstanceMethod(object_getClass(native_delegate),inset_selector) : NULL;
    if (inset_method && !strcmp(method_getTypeEncoding(inset_method),"{UIEdgeInsets=dddd}40@0:8@16@24q32"))
        section_inset=((Insets (*)(id,SEL,id,id,I))objc_msgSend)(native_delegate,inset_selector,content,flow,section);
    Insets inset=responds(content,"adjustedContentInset") ?
        ((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("adjustedContentInset")) :
        ((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("contentInset"));
    Rect position=rect(attributes,"frame"),a=rect(first,"frame"),b=rect(last,"frame");
    double start=a.origin.y-section_inset.top-position.size.height;
    double end=b.origin.y+b.size.height+section_inset.bottom-position.size.height;
    double y=rect(content,"bounds").origin.y+inset.top-s->recent_height;
    if (end<start || position.size.height<=0) return attributes;
    if (y<start) y=start;
    if (y>end) y=end; /* Preserve the following section's push-off boundary. */
    if (position.origin.y==y) return attributes;
    id copy=m0(attributes,"copy"); position.origin.y=y; frame(copy,position);
    return m0(copy,"autorelease");
}
static id flow_elements(id flow,SEL sel,Rect bounds) {
    id original=((id (*)(id,SEL,Rect))original_flow_elements)(flow,sel,bounds);
    id content=m0(flow,"collectionView");
    if (!objc_getAssociatedObject(content,&recent_host_key)) return original;
    id result=nil;
    for (U i=0;i<number(original,"count");i++) {
        id attributes=at(original,i),corrected=recent_header_attributes(flow,attributes);
        if (corrected==attributes) continue;
        if (!result) result=m0(original,"mutableCopy");
        ((void (*)(id,SEL,U,id))objc_msgSend)(result,sel_registerName("replaceObjectAtIndex:withObject:"),i,corrected);
    }
    return result ? m0(result,"autorelease") : original;
}
static id flow_header(id flow,SEL sel,id kind_name,id path) {
    id original=((id (*)(id,SEL,id,id))original_flow_header)(flow,sel,kind_name,path);
    return recent_header_attributes(flow,original);
}
static void collection_layout(id content,SEL sel) {
    ((void (*)(id,SEL))original_collection_layout)(content,sel);
    id delegate=objc_getAssociatedObject(content,&recent_host_key);
    if (delegate) place_recent_strip(state(delegate),content);
}
static void container_layout(id container,SEL sel) {
    ((void (*)(id,SEL))original_container_layout)(container,sel);
    id footer=find_class(container,FOOTER,0),owner=owner_above(container);
    if (owner) install_footer(footer,owner);
    id delegate=objc_getAssociatedObject(footer,&footer_key); if (delegate) layout(delegate);
}
static void scroll_to_recents(State *s) {
    if (s->recent_height) {
        id content=objc_loadWeakRetained(&s->recent_content);
        if (content) {
            Insets inset=((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("adjustedContentInset"));
            ((void (*)(id,SEL,Point,BOOL))objc_msgSend)(content,sel_registerName("setContentOffset:animated:"),(Point){0,-inset.top},NO);
        }
        objc_release(content);
    }
}
static void footer_action(id footer,SEL sel) {
    const char *names[]={"keyboardButtonPressed","recentEmotesButtonPressed","channelEmotesButtonPressed","allEmotesButtonPressed","backspaceButtonPressed"};
    size_t action=0; for (;action<5;action++) if (!strcmp(sel_getName(sel),names[action])) break;
    if (action==5) return;
    id delegate=objc_getAssociatedObject(footer,&footer_key); State *s=state(delegate);
    if (s) { if (action!=4) { restore_native(s); s->tab=0; } expand(delegate); }
    ((void (*)(id,SEL))original_footer_actions[action])(footer,sel);
    if (!s) return;
    render(delegate); refresh(delegate);
    if (action==1) scroll_to_recents(s);
    start_tick(delegate);
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
    hook(NATIVE_SELECTOR,"viewWillLayoutSubviews","v16@0:8",(IMP)selector_layout,&original_selector_layout);
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
            {"ssGridPick:",(IMP)grid_button,"v@:@"},
            {"ssTick:",(IMP)tick,"v@:@"}, {"ssImages:",(IMP)image_changed,"v@:@"}, {"ssPreview:",(IMP)preview_ready,"v@:@"},
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
    const char *read_actions[]={"text","textStorage"};
    for (size_t i=0;i<2;i++) { Method m=class_getInstanceMethod(objc_getClass(ENTRY),sel_registerName(read_actions[i])); if (!m || strcmp(method_getTypeEncoding(m),"@16@0:8")) return; }
    hook(ENTRY,"text","@16@0:8",(IMP)editor_text,&original_text);
    hook(ENTRY,"textStorage","@16@0:8",(IMP)editor_storage,&original_storage);
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
    hook("UICollectionView","layoutSubviews","v16@0:8",(IMP)collection_layout,&original_collection_layout);
    hook("UICollectionViewFlowLayout","layoutAttributesForElementsInRect:","@48@0:8{CGRect={CGPoint=dd}{CGSize=dd}}16",(IMP)flow_elements,&original_flow_elements);
    hook("UICollectionViewFlowLayout","layoutAttributesForSupplementaryViewOfKind:atIndexPath:","@32@0:8@16@24",(IMP)flow_header,&original_flow_header);
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
        "Native text snapshot hooks (text/storage): %s/%s\n"
        "Native library scrolling hook: %s\n"
        "Native library header hooks (elements/header): %s/%s\n"
        "Unified Twitch catalog bridge/selector hooks: %s/%s\n"
        "Twitch catalog snapshots/entries/misses/native insertions/suppressions: %llu/%llu/%llu/%llu/%llu\n"
        "Identity layout misses/image failures: %llu/%llu\n"
        "Picker taps (grid/strip), missing selection/lookup: %llu/%llu, %llu/%llu\n"
        "Insertion veto/range miss/unchanged edit: %llu/%llu/%llu\n",
        original_change ? "installed":"missing",original_selection ? "installed":"missing",original_should_change ? "installed":"missing",
        original_send ? "installed":"missing",original_footer_apply ? "installed":"missing",original_copy ? "installed":"missing",original_undo && original_redo ? "installed":"missing",
        ss_composer_suggestion_mode()==0 ? "automatic" : ss_composer_suggestion_mode()==1 ? "colon":"off",
        (unsigned long long)GET(edited),(unsigned long long)GET(previewed),(unsigned long long)GET(insertions),(unsigned long long)GET(palette_opens),
        original_text ? "installed":"missing",original_storage ? "installed":"missing",
        original_collection_layout ? "installed":"missing",
        original_flow_elements ? "installed":"missing",original_flow_header ? "installed":"missing",
        native_array_type ? "ready":"waiting",original_selector_layout ? "installed":"missing",
        (unsigned long long)GET(native_snapshots),(unsigned long long)GET(native_catalog_count),(unsigned long long)GET(native_catalog_misses),
        (unsigned long long)GET(native_insertions),(unsigned long long)GET(selector_suppressions),
        (unsigned long long)GET(identity_misses),(unsigned long long)GET(image_failures),
        (unsigned long long)GET(grid_taps),(unsigned long long)GET(strip_taps),
        (unsigned long long)GET(selection_missing),(unsigned long long)GET(lookup_misses),
        (unsigned long long)GET(validation_vetoes),(unsigned long long)GET(range_misses),(unsigned long long)GET(unchanged_edits));
}
