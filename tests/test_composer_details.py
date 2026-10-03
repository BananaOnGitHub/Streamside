"""Production attachment-menu and picker hold routing at the UIKit boundary."""
import os
import shutil
import unittest
import test_composer as composer
from test_composer_library import replace_body

HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include "SSComposer.c"
struct Fake {
    const char *cls,*text,*action,*encoding;
    id value,host,metadata,window,attachment,gesture,target,native,image,button,label;
    id codes[8],attachments[8]; uint16_t units[8];
    U count,gesture_state; Range range; State *context;
    IMP imp; BOOL cancels;
    unsigned refs;
};
static struct Fake objects[256],classes[32],owner,editor,delegate,source,attachment,foreign,metadata,window,item,menu,fallback,other;
static struct Fake reused_cell;
static id expected_metadata=&metadata;
static U used,class_count,scheduled,shown,forwarded,added,replaced;
static BOOL has_method,accept_sheet=YES;
static State context;
static id fresh(const char *cls) { assert(used<256);id o=&objects[used++];o->cls=cls;return o; }
Class objc_getClass(const char *name) {
    for(U i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name))return &classes[i];
    assert(class_count<32);classes[class_count].cls=name;return &classes[class_count++];
}
SEL sel_registerName(const char *s) { return s; }
Class object_getClass(id o) { return o; }
Ivar class_getInstanceVariable(Class c,const char *name) {
    (void)c;
    if(!strcmp(name,"_state"))return (Ivar)(uintptr_t)offsetof(struct Fake,context);
    if(!strcmp(name,"textEntryView"))return (Ivar)(uintptr_t)offsetof(struct Fake,value);
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return (ptrdiff_t)(uintptr_t)iv; }
size_t class_getInstanceSize(Class c) { (void)c;return sizeof(struct Fake); }
id objc_retain(id o) { if(o)o->refs++;return o; }
void objc_release(id o) { if(o && o->refs)o->refs--; }
id objc_loadWeakRetained(id *p) { return objc_retain(*p); }
id objc_getAssociatedObject(id o,const void *k) {
    if(!o)return nil;
    if(k==&state_key)return o->host;
    if(k==&button_key || k==&attachment_metadata_key)return o->metadata;
    if(k==&cell_key)return o->image;
    if(k==&grid_button_key)return o->button;
    assert(!"unexpected association");return nil;
}
void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t policy) {
    assert(policy==1);
    if(k==&cell_key)o->image=v;else if(k==&grid_button_key)o->button=v;
    else {assert(k==&button_key);o->metadata=v;}
}
Range ss_test_item_range(id o) { return o->range; }
BOOL tas_emote_ui_present_details(id view,id data) {
    assert(view==&owner && data==expected_metadata);
    assert(!context.details_attachment); /* Suppression returned before presentation. */
    if(accept_sheet)shown++;return accept_sheet;
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"stringWithUTF8String:")){result=fresh("NSString");result->text=va_arg(args,const char *);}
    else if(!strcmp(sel,"isKindOfClass:"))result=(id)(uintptr_t)!strcmp(o->cls,va_arg(args,Class)->cls);
    else if(!strcmp(sel,"respondsToSelector:")){(void)va_arg(args,SEL);result=(id)(uintptr_t)YES;}
    else if(!strcmp(sel,"objectForKey:")){id k=va_arg(args,id);result=!strcmp(k->text,"native") ? o->native : nil;}
    else if(!strcmp(sel,"objectAtIndex:")){U i=va_arg(args,U);assert(i<o->count);result=o->codes[i];}
    else if(!strcmp(sel,"count") || !strcmp(sel,"item"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"dequeueReusableCellWithReuseIdentifier:forIndexPath:")){assert(va_arg(args,id));assert(va_arg(args,id));result=&reused_cell;}
    else if(!strcmp(sel,"contentView"))result=o;
    else if(!strcmp(sel,"initWithFrame:"))result=o;
    else if(!strcmp(sel,"setContentMode:") || !strcmp(sel,"setTag:") || !strcmp(sel,"setTextAlignment:"))(void)va_arg(args,I);
    else if(!strcmp(sel,"setFont:") || !strcmp(sel,"setTextColor:") || !strcmp(sel,"setText:") || !strcmp(sel,"setAccessibilityLabel:"))(void)va_arg(args,id);
    else if(!strcmp(sel,"secondaryLabelColor") || !strcmp(sel,"systemFontOfSize:"))result=o;
    else if(!strcmp(sel,"addSubview:")){id v=va_arg(args,id);if(!strcmp(v->cls,"UILabel"))o->label=v;}
    else if(!strcmp(sel,"viewWithTag:")){assert(va_arg(args,I)==301);result=o->label;}
    else if(!strcmp(sel,"addTarget:action:forControlEvents:")){o->target=va_arg(args,id);o->action=va_arg(args,SEL);assert(va_arg(args,U)==1UL<<6);}
    else if(!strcmp(sel,"attributedText"))result=&source;
    else if(!strcmp(sel,"string"))result=o;
    else if(!strcmp(sel,"length"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"characterAtIndex:")){U i=va_arg(args,U);assert(i<o->count);result=(id)(uintptr_t)o->units[i];}
    else if(!strcmp(sel,"attribute:atIndex:effectiveRange:")){
        id k=va_arg(args,id);U i=va_arg(args,U);assert(i<o->count);assert(!va_arg(args,Range *));
        if(!strcmp(k->text,ATTACHMENT_KEY))result=o->codes[i];else {assert(!strcmp(k->text,"NSAttachment"));result=o->attachments[i];}
    }
    else if(!strcmp(sel,"window"))result=o->window;
    else if(!strcmp(sel,"textAttachment"))result=o->attachment;
    else if(!strcmp(sel,"performSelector:withObject:afterDelay:")){
        assert(o==&delegate && !strcmp(va_arg(args,SEL),"ssDetails:"));assert(!va_arg(args,id));assert(va_arg(args,double)==0);scheduled++;
    }
    else if(!strcmp(sel,"configurationWithMenu:")){assert(va_arg(args,id)==&menu);result=&fallback;}
    else if(!strcmp(sel,"alloc"))result=fresh(o->cls);
    else if(!strcmp(sel,"initWithTarget:action:")){o->target=va_arg(args,id);o->action=va_arg(args,SEL);result=o;}
    else if(!strcmp(sel,"setCancelsTouchesInView:"))o->cancels=va_arg(args,int);
    else if(!strcmp(sel,"addGestureRecognizer:")){assert(!o->gesture);o->gesture=va_arg(args,id);o->gesture->value=o;}
    else if(!strcmp(sel,"view"))result=o->value;
    else if(!strcmp(sel,"state"))result=(id)(uintptr_t)o->gesture_state;
    else assert(!"unexpected details selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static id native_menu(id o,SEL sel,id e,id i,id m) {
    assert(o==&owner && !strcmp(sel,"menu") && (e==&editor || e==&other) && i==&item && m==&menu);forwarded++;return &other;
}
static BOOL native_interact(id o,SEL sel,id e,id a,Range r,I interaction) {
    assert(o==&owner && !strcmp(sel,"interact") && e==&editor && a==&foreign && r.length==1 && interaction==1);forwarded++;return NO;
}
Method class_getInstanceMethod(Class c,SEL sel) { (void)sel;return has_method ? c : NULL; }
const char *method_getTypeEncoding(Method m) { return ((id)m)->encoding; }
IMP method_getImplementation(Method m) { return ((id)m)->imp; }
BOOL class_addMethod(Class c,SEL sel,IMP imp,const char *types) {
    assert(c==objc_getClass(INPUT) && !strcmp(sel,"optional"));
    if(has_method)return NO;c->encoding=types;c->imp=imp;added++;return YES;
}
IMP method_setImplementation(Method m,IMP imp) { IMP previous=((id)m)->imp;((id)m)->imp=imp;replaced++;return previous; }
int main(void) {
    owner.cls=INPUT;owner.value=&editor;owner.host=&delegate;owner.window=&window;
    editor.cls="UITextView";editor.window=&window;delegate.context=&context;delegate_class=objc_getClass("SSComposerDelegate");context.owner=&owner;
    source.count=3;source.units[0]='x';source.units[1]=0xfffc;source.units[2]=0xfffc;
    source.codes[1]=&metadata;source.attachments[1]=&attachment;source.attachments[2]=&foreign;
    attachment.metadata=&metadata;item.attachment=&attachment;item.range=(Range){1,1};
    /* Modern menus suppress the generic image actions; duplicate callbacks
     * coalesce and presentation happens after UIKit returns. No editor writes. */
    assert(!composer_item_menu(&owner,"menu",&editor,&item,&menu));
    assert(!composer_item_menu(&owner,"menu",&editor,&item,&menu));
    assert(scheduled==1 && shown==0 && attachment.refs==1);
    composer_details(&delegate,"ssDetails:",nil);
    assert(shown==1 && !context.details_attachment && !attachment.refs);
    assert(source.count==3 && source.units[1]==0xfffc && source.attachments[1]==&attachment);
    /* Foreign attachments, links and stale/out-of-bounds attachment ranges
     * retain the native implementation (or UIKit's default menu/preview). */
    item.attachment=&foreign;item.range=(Range){2,1};
    assert(composer_item_menu(&owner,"menu",&editor,&item,&menu)==&fallback);
    original_item_menu=(IMP)native_menu;
    assert(composer_item_menu(&owner,"menu",&editor,&item,&menu)==&other && forwarded==1);
    item.attachment=nil;assert(composer_item_menu(&owner,"menu",&editor,&item,&menu)==&other);
    item.attachment=&attachment;item.range=(Range){8,1};assert(composer_item_menu(&owner,"menu",&editor,&item,&menu)==&other);
    item.range=(Range){1,2};assert(composer_item_menu(&owner,"menu",&editor,&item,&menu)==&other);
    item.range=(Range){1,1};assert(composer_item_menu(&owner,"menu",&other,&item,&menu)==&other);
    /* A removed attachment or detached input cannot present a stale sheet. */
    assert(!composer_item_menu(&owner,"menu",&editor,&item,&menu));source.attachments[1]=&foreign;
    composer_details(&delegate,"ssDetails:",nil);assert(shown==1 && !attachment.refs);
    source.attachments[1]=&attachment;
    assert(!composer_item_menu(&owner,"menu",&editor,&item,&menu));editor.window=nil;
    composer_details(&delegate,"ssDetails:",nil);assert(shown==1 && !attachment.refs);editor.window=&window;
    /* iOS 16 attachment delegate: no sheet on a plain tap, holds/preview open
     * the same details; native attachments still receive Twitch's answer. */
    U before=scheduled;
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&attachment,(Range){1,1},0));assert(scheduled==before);
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&attachment,(Range){1,1},1));
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&attachment,(Range){1,1},2));assert(scheduled==before+1);
    composer_details(&delegate,"ssDetails:",nil);assert(shown==2);
    assert(composer_attachment_interaction(&owner,"interact",&editor,&foreign,(Range){2,1},1));
    original_attachment_interaction=(IMP)native_interact;
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&foreign,(Range){2,1},1));
    /* A hold reads the tile's CURRENT reuse metadata, fires once at Began,
     * cancels tap-to-insert, and leaves scrolling's cancellation intact. */
    struct Fake button={.cls="UIButton",.metadata=&metadata};
    add_emote_hold(&button,&delegate);id gesture=button.gesture;
    assert(gesture && gesture->cancels && gesture->target==&delegate && !strcmp(gesture->action,"ssEmoteHold:"));
    gesture->gesture_state=0;emote_hold(&delegate,"hold",gesture);assert(shown==2);
    gesture->gesture_state=1;emote_hold(&delegate,"hold",gesture);assert(shown==3);
    gesture->gesture_state=2;emote_hold(&delegate,"hold",gesture);
    gesture->gesture_state=3;emote_hold(&delegate,"hold",gesture);assert(shown==3);
    button.metadata=nil;gesture->gesture_state=1;emote_hold(&delegate,"hold",gesture);assert(shown==3);
    button.metadata=&metadata;metadata.native=&foreign;emote_hold(&delegate,"hold",gesture);assert(shown==3);metadata.native=nil;
    owner.window=nil;emote_hold(&delegate,"hold",gesture);assert(shown==3);owner.window=&window;
    accept_sheet=NO;emote_hold(&delegate,"hold",gesture);assert(shown==3 && GET(details_holds)==3);
    assert(strip_cancel_touch(nil,NULL,&button));
    accept_sheet=YES;
    struct Fake entries={.count=2,.codes={&metadata,&foreign}},collection={0},path={0};
    context.entries=&entries;
    assert(cell(&delegate,"cell",&collection,&path)==&reused_cell);
    id library_button=reused_cell.button,library_gesture=library_button->gesture;
    assert(library_gesture && library_gesture->cancels && library_button->metadata==&metadata);
    assert(!strcmp(library_button->action,"ssGridPick:"));
    path.count=1;expected_metadata=&foreign;
    assert(cell(&delegate,"cell",&collection,&path)==&reused_cell);
    assert(reused_cell.button==library_button && library_button->gesture==library_gesture && library_button->metadata==&foreign);
    library_gesture->gesture_state=1;emote_hold(&delegate,"hold",library_gesture);assert(shown==4);
    /* Optional hooks add absent methods, chain compatible implementations,
     * and leave an unknown native ABI completely untouched. */
    IMP original=NULL;Class input=objc_getClass(INPUT);
    assert(optional_input_hook("optional","@40@0:8@16@24@32",(IMP)composer_item_menu,&original));
    assert(added==1 && !original);
    has_method=YES;input->encoding="unknown";input->imp=(IMP)native_menu;
    assert(!optional_input_hook("optional","@40@0:8@16@24@32",(IMP)composer_item_menu,&original));assert(!original && !replaced);
    input->encoding="@40@0:8@16@24@32";
    assert(optional_input_hook("optional",input->encoding,(IMP)composer_item_menu,&original));assert(original==(IMP)native_menu && replaced==1);
    return 0;
}
'''


class ComposerDetailsTests(unittest.TestCase):
    def test_hold_details_menu_suppression_native_fallback_and_lifecycle(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = (composer.ROOT / "src" / "SSComposer.c").read_text()
        source = replace_body(source, "static void set_thumbnail(id image_view,id metadata)",
                              '(void)image_view;(void)metadata;(void)thumbnail_url_key;(void)thumbnail_record_key;')
        # Returning a struct through the host's variadic fake differs from arm64
        # objc_msgSend; adapt only that boundary, not routing or ownership logic.
        source = source.replace('Range range=((Range (*)(id,SEL))objc_msgSend)(item,sel_registerName("range"));',
                                'extern Range ss_test_item_range(id); Range range=ss_test_item_range(item);')
        composer.ComposerTests().compile_run(HARNESS.replace('#include "SSComposer.c"', source),
                                             [zig, "cc", "-fblocks"], runtime=True)

    def test_chat_and_composer_share_sheet_and_borrowed_metadata_lifetime(self):
        source = (composer.ROOT / "src" / "TASEmoteUI.c").read_text()
        # Registration is UIKit infrastructure. Exercise the real presenter,
        # navigation-sheet construction, associations and chat-ID adapter.
        source = replace_body(source, 'static BOOL register_details(void)',
                              '(void)g_details_load;(void)details_load;(void)details_close;'
                              '(void)details_rows;(void)details_cell;(void)details_select;return YES;')
        composer.ComposerTests().compile_run(SHEET.replace('#include "TASEmoteUI.c"', source),
                                             ["cc", "-std=gnu11", "-Wno-cast-function-type"], runtime=True)


SHEET = r'''
#include <assert.h>
#include <stdarg.h>
#include "TASEmoteUI.c"
struct Fake { const char *cls; id next,value,metadata; unsigned refs; };
static struct Fake classes[8],objects[16],root,child,metadata;
static unsigned class_count,used,presentations,copies;
Class objc_getClass(const char *name) {
    for(unsigned i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name))return &classes[i];
    assert(class_count<8);classes[class_count].cls=name;return &classes[class_count++];
}
SEL sel_registerName(const char *s) { return s; }
id objc_retain(id o) { if(o)o->refs++;return o; }
void objc_release(id o) {
    if(!o)return;
    assert(o->refs);if(--o->refs)return;
    if(o->metadata)objc_release(o->metadata);
    if(o->value)objc_release(o->value);
}
void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t policy) {
    assert(k==&g_metadata_key && policy==1);o->metadata=objc_retain(v);
}
id tas_emotes_metadata_copy(uint64_t number) { assert(number==9000000001ULL);copies++;return objc_retain(&metadata); }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;
    va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"isKindOfClass:"))result=(id)(uintptr_t)!strcmp(o->cls,va_arg(args,Class)->cls);
    else if(!strcmp(sel,"nextResponder"))result=o->next;
    else if(!strcmp(sel,"presentedViewController"))result=o->value;
    else if(!strcmp(sel,"alloc")){assert(used<16);result=&objects[used++];result->cls=o->cls;result->refs=1;}
    else if(!strcmp(sel,"initWithStyle:")){assert(va_arg(args,NSInteger)==0);result=o;}
    else if(!strcmp(sel,"initWithRootViewController:")){o->value=objc_retain(va_arg(args,id));result=o;}
    else if(!strcmp(sel,"setModalPresentationStyle:"))assert(va_arg(args,NSInteger)==1);
    else if(!strcmp(sel,"respondsToSelector:")){assert(!strcmp(va_arg(args,SEL),"sheetPresentationController"));result=nil;}
    else if(!strcmp(sel,"presentViewController:animated:completion:")){
        assert(o==&root && !o->value);o->value=objc_retain(va_arg(args,id));assert(va_arg(args,int));assert(!va_arg(args,id));presentations++;
    }
    else assert(!"unexpected shared sheet selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
int main(void) {
    root.cls="UIViewController";child.cls="UITextView";child.next=&root;
    metadata.cls="NSDictionary";metadata.refs=1;g_details_class=objc_getClass("TASProviderEmoteController");
    assert(!tas_emote_ui_present_details(nil,&metadata));
    assert(!tas_emote_ui_present_details(&child,nil));
    assert(metadata.refs==1 && !presentations);
    assert(tas_emote_ui_present_details(&child,&metadata));
    assert(presentations==1 && metadata.refs==2 && root.value->value->metadata==&metadata);
    assert(!tas_emote_ui_present_details(&child,&metadata));assert(metadata.refs==2);
    objc_release(root.value);root.value=nil;assert(metadata.refs==1);
    assert(show_details(&child,9000000001ULL));assert(copies==1 && presentations==2 && metadata.refs==2);
    objc_release(root.value);root.value=nil;assert(metadata.refs==1);
    child.next=nil;assert(!show_details(&child,9000000001ULL));assert(copies==2 && metadata.refs==1);
    return 0;
}
'''
