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
    IMP imp; BOOL cancels,hidden,marked;
    double duration; Point point; Insets inset; Rect bounds;
    unsigned refs;
};
static struct Fake objects[256],classes[32],owner,editor,delegate,source,attachment,foreign,metadata,window,item,menu,fallback,other;
static struct Fake reused_cell;
static struct Fake manager,container,strip;
static id expected_metadata=&metadata;
static U used,class_count,scheduled,shown,forwarded,added,replaced,impacts;
static Point hit_point;
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
    assert(strip.hidden); /* Hidden before presentation, not a later timer tick. */
    if(accept_sheet)shown++;return accept_sheet;
}
Point ss_test_hold_point(id location,id view) { assert(view==&editor);hit_point=location->point;return hit_point; }
Insets ss_test_hold_inset(id view) { assert(view==&editor);return view->inset; }
U ss_test_hold_glyph(id layout,Point point,id text_container) {
    assert(layout==&manager && text_container==&container);
    assert(point.x==hit_point.x-editor.inset.left && point.y==hit_point.y-editor.inset.top);
    return manager.range.location;
}
Rect ss_test_hold_bounds(id layout,Range range,id text_container) {
    assert(layout==&manager && range.length==1 && text_container==&container);return manager.bounds;
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
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"setHidden:"))o->hidden=va_arg(args,int);
    else if(!strcmp(sel,"markedTextRange"))result=o->marked ? &other : nil;
    else if(!strcmp(sel,"layoutManager"))result=&manager;
    else if(!strcmp(sel,"textContainer"))result=&container;
    else if(!strcmp(sel,"numberOfGlyphs"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"characterIndexForGlyphAtIndex:"))result=(id)(uintptr_t)va_arg(args,U);
    else if(!strcmp(sel,"textAttachment"))result=o->attachment;
    else if(!strcmp(sel,"performSelector:withObject:afterDelay:")){
        assert(o==&delegate && !strcmp(va_arg(args,SEL),"ssDetails:"));assert(!va_arg(args,id));assert(va_arg(args,double)==0);scheduled++;
    }
    else if(!strcmp(sel,"configurationWithMenu:")){assert(va_arg(args,id)==&menu);result=&fallback;}
    else if(!strcmp(sel,"alloc"))result=fresh(o->cls);
    else if(!strcmp(sel,"initWithTarget:action:")){o->target=va_arg(args,id);o->action=va_arg(args,SEL);result=o;}
    else if(!strcmp(sel,"initWithStyle:")){assert(!strcmp(o->cls,"UIImpactFeedbackGenerator") && va_arg(args,I)==0);result=o;}
    else if(!strcmp(sel,"impactOccurred")){assert(!strcmp(o->cls,"UIImpactFeedbackGenerator") && shown==impacts+1);impacts++;}
    else if(!strcmp(sel,"setCancelsTouchesInView:"))o->cancels=va_arg(args,int);
    else if(!strcmp(sel,"setMinimumPressDuration:"))o->duration=va_arg(args,double);
    else if(!strcmp(sel,"setDelegate:"))assert(va_arg(args,id)==&delegate);
    else if(!strcmp(sel,"removeGestureRecognizer:")){assert(o->gesture==va_arg(args,id));o->gesture->value=nil;o->gesture=nil;}
    else if(!strcmp(sel,"addGestureRecognizer:")){assert(!o->gesture);o->gesture=va_arg(args,id);o->gesture->value=o;}
    else if(!strcmp(sel,"view"))result=o->value;
    else if(!strcmp(sel,"superview"))result=o->value;
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
    editor.cls="UITextView";editor.window=&window;delegate.context=&context;delegate_class=objc_getClass("SSComposerDelegate");context.owner=&owner;context.strip=&strip;
    source.count=3;source.units[0]='x';source.units[1]=0xfffc;source.units[2]=0xfffc;
    source.codes[1]=&metadata;source.attachments[1]=&attachment;source.attachments[2]=&foreign;
    attachment.metadata=&metadata;item.attachment=&attachment;item.range=(Range){1,1};
    /* UIKit requests its image menu early. Suppression must never schedule or
     * present details: only the matching 0.5s gesture can authorize that. */
    assert(!composer_item_menu(&owner,"menu",&editor,&item,&menu));
    assert(!composer_item_menu(&owner,"menu",&editor,&item,&menu));
    assert(scheduled==0 && shown==0 && !attachment.refs);
    install_editor_hold(&delegate,&editor);id editor_gesture=context.editor_hold;
    assert(editor_gesture==editor.gesture && editor_gesture->duration==0.5 && !editor_gesture->cancels);
    install_editor_hold(&delegate,&editor);assert(context.editor_hold==editor_gesture);
    editor.inset=(Insets){4,7,0,0};editor_gesture->point=(Point){25,15};
    manager.count=3;manager.range.location=1;manager.bounds=(Rect){{10,5},{24,20}};
    struct Fake touch={.point={25,15}},native_gesture={.value=&editor},child={.value=&editor},child_gesture={.value=&child};
    editor_gesture->point=(Point){0,0}; /* Touch-down must use UITouch, not the recognizer's uninitialized location. */
    assert(composer_hold_receive_touch(&delegate,"receive",editor_gesture,&touch));
    assert(composer_hold_priority(&delegate,"priority",editor_gesture,&native_gesture));
    assert(composer_hold_priority(&delegate,"priority",editor_gesture,&child_gesture));
    assert(!composer_hold_priority(&delegate,"priority",editor_gesture,&other));
    assert(!composer_hold_priority(&delegate,"priority",&native_gesture,editor_gesture));
    assert(!composer_hold_priority(&delegate,"priority",editor_gesture,editor_gesture));
    editor_gesture->point=touch.point;
    assert(composer_hold_should_begin(&delegate,"begin",editor_gesture));
    editor_gesture->gesture_state=0;composer_hold(&delegate,"hold",editor_gesture);assert(!scheduled && !shown);
    editor_gesture->gesture_state=1;composer_hold(&delegate,"hold",editor_gesture);
    composer_hold(&delegate,"hold",editor_gesture);assert(scheduled==1 && !shown && attachment.refs==1);
    composer_details(&delegate,"ssDetails:",nil);
    assert(shown==1 && impacts==1 && !context.details_attachment && !attachment.refs);
    composer_details(&delegate,"ssDetails:",nil);assert(shown==1 && impacts==1);
    assert(source.count==3 && source.units[1]==0xfffc && source.attachments[1]==&attachment);
    editor_gesture->gesture_state=2;composer_hold(&delegate,"hold",editor_gesture);assert(scheduled==1);
    touch.point.x=70;assert(!composer_hold_receive_touch(&delegate,"receive",editor_gesture,&touch));
    assert(!composer_hold_priority(&delegate,"priority",editor_gesture,&native_gesture));
    touch.point.x=25;manager.range.location=0;assert(!composer_hold_receive_touch(&delegate,"receive",editor_gesture,&touch));
    manager.range.location=2;assert(!composer_hold_receive_touch(&delegate,"receive",editor_gesture,&touch));
    manager.range.location=1;editor.marked=YES;assert(!composer_hold_receive_touch(&delegate,"receive",editor_gesture,&touch));editor.marked=NO;
    assert(composer_hold_receive_touch(&delegate,"receive",&other,&touch)); /* Library recognizers are untouched. */
    editor_gesture->point.x=70;assert(!composer_hold_should_begin(&delegate,"begin",editor_gesture)); /* Nearest glyph, outside image. */
    editor_gesture->point.x=25;manager.range.location=0;assert(!composer_hold_should_begin(&delegate,"begin",editor_gesture)); /* Ordinary text. */
    manager.range.location=2;assert(!composer_hold_should_begin(&delegate,"begin",editor_gesture)); /* Foreign attachment. */
    manager.range.location=3;assert(!composer_hold_should_begin(&delegate,"begin",editor_gesture)); /* Past final glyph. */
    manager.range.location=1;editor.marked=YES;assert(!composer_hold_should_begin(&delegate,"begin",editor_gesture));editor.marked=NO;
    assert(composer_hold_should_begin(&delegate,"begin",editor_gesture));
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
    assert(queue_composer_details(&owner,&editor,&attachment,item.range));source.attachments[1]=&foreign;
    composer_details(&delegate,"ssDetails:",nil);assert(shown==1 && !attachment.refs);
    source.attachments[1]=&attachment;
    assert(queue_composer_details(&owner,&editor,&attachment,item.range));editor.window=nil;
    composer_details(&delegate,"ssDetails:",nil);assert(shown==1 && !attachment.refs);editor.window=&window;
    /* Legacy UIKit attachment requests also only suppress its image menu.
     * They cannot shorten the shared hold threshold. */
    U before=scheduled;
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&attachment,(Range){1,1},0));assert(scheduled==before);
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&attachment,(Range){1,1},1));
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&attachment,(Range){1,1},2));assert(scheduled==before);
    editor_gesture->gesture_state=1;composer_hold(&delegate,"hold",editor_gesture);assert(scheduled==before+1);
    composer_details(&delegate,"ssDetails:",nil);assert(shown==2 && impacts==2);
    accept_sheet=NO;strip.hidden=NO;
    assert(queue_composer_details(&owner,&editor,&attachment,(Range){1,1}));
    composer_details(&delegate,"ssDetails:",nil);assert(shown==2 && impacts==2 && !strip.hidden);
    accept_sheet=YES;
    assert(composer_attachment_interaction(&owner,"interact",&editor,&foreign,(Range){2,1},1));
    original_attachment_interaction=(IMP)native_interact;
    assert(!composer_attachment_interaction(&owner,"interact",&editor,&foreign,(Range){2,1},1));
    /* A hold reads the tile's CURRENT reuse metadata, fires once at Began,
     * cancels tap-to-insert, and leaves scrolling's cancellation intact. */
    struct Fake button={.cls="UIButton",.metadata=&metadata};
    add_emote_hold(&button,&delegate);id gesture=button.gesture;
    assert(gesture && gesture->cancels && gesture->target==&delegate && !strcmp(gesture->action,"ssEmoteHold:"));
    assert(gesture->duration==editor_gesture->duration && gesture->duration==0.5);
    gesture->gesture_state=0;emote_hold(&delegate,"hold",gesture);assert(shown==2);
    gesture->gesture_state=1;emote_hold(&delegate,"hold",gesture);assert(shown==3);
    gesture->gesture_state=2;emote_hold(&delegate,"hold",gesture);
    gesture->gesture_state=3;emote_hold(&delegate,"hold",gesture);assert(shown==3);
    button.metadata=nil;gesture->gesture_state=1;emote_hold(&delegate,"hold",gesture);assert(shown==3);
    button.metadata=&metadata;metadata.native=&foreign;emote_hold(&delegate,"hold",gesture);assert(shown==3);metadata.native=nil;
    owner.window=nil;emote_hold(&delegate,"hold",gesture);assert(shown==3);owner.window=&window;
    strip.hidden=NO;accept_sheet=NO;emote_hold(&delegate,"hold",gesture);assert(shown==3 && GET(details_holds)==3 && !strip.hidden);
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
    library_gesture->gesture_state=1;emote_hold(&delegate,"hold",library_gesture);assert(shown==4 && impacts==2);
    struct Fake replacement_editor={.cls="UITextView",.window=&window};
    install_editor_hold(&delegate,&replacement_editor);
    assert(!editor.gesture && !editor_gesture->value && replacement_editor.gesture==context.editor_hold);
    assert(context.editor_hold!=editor_gesture && context.editor_hold->duration==0.5 && !context.editor_hold->cancels);
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
        for before, after in (
            ('Point point=((Point (*)(id,SEL,id))objc_msgSend)(location,sel_registerName("locationInView:"),editor);',
             'extern Point ss_test_hold_point(id,id); Point point=ss_test_hold_point(location,editor);'),
            ('Insets inset=((Insets (*)(id,SEL))objc_msgSend)(editor,sel_registerName("textContainerInset"));',
             'extern Insets ss_test_hold_inset(id); Insets inset=ss_test_hold_inset(editor);'),
            ('U glyph=((U (*)(id,SEL,Point,id))objc_msgSend)(manager,sel_registerName("glyphIndexForPoint:inTextContainer:"),point,container);',
             'extern U ss_test_hold_glyph(id,Point,id); U glyph=ss_test_hold_glyph(manager,point,container);'),
            ('Rect bounds=((Rect (*)(id,SEL,Range,id))objc_msgSend)(manager,sel_registerName("boundingRectForGlyphRange:inTextContainer:"),(Range){glyph,1},container);',
             'extern Rect ss_test_hold_bounds(id,Range,id); Rect bounds=ss_test_hold_bounds(manager,(Range){glyph,1},container);'),
        ):
            self.assertIn(before, source)
            source = source.replace(before, after)
        composer.ComposerTests().compile_run(HARNESS.replace('#include "SSComposer.c"', source),
                                             [zig, "cc", "-fblocks"], runtime=True)

    def test_chat_and_composer_share_sheet_and_borrowed_metadata_lifetime(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = (composer.ROOT / "src" / "TASEmoteUI.c").read_text()
        # Registration is UIKit infrastructure. Exercise the real presenter,
        # navigation-sheet construction, associations and chat-ID adapter.
        source = replace_body(source, 'static BOOL register_details(void)',
                              '(void)g_details_load;(void)details_load;(void)details_close;'
                              '(void)details_rows;(void)details_cell;(void)details_select;return YES;')
        composer.ComposerTests().compile_run(SHEET.replace('#include "TASEmoteUI.c"', source),
                                             [zig, "cc", "-fblocks"], runtime=True)

    def test_browser_handoff_waits_for_owned_sheet_dismissal(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        composer.ComposerTests().compile_run(BROWSER, [zig, "cc", "-fblocks"], runtime=True)


BROWSER = r'''
#include <assert.h>
#include <stdarg.h>
#include "TASEmoteUI.c"
struct Fake {
    const char *cls,*text;
    id nav,presenter,presented,root,metadata,pending;
    unsigned refs; NSInteger row;
    BOOL presenting,dismissing;
};
struct Block { void *isa; int flags,reserved; void (*invoke)(struct Block *); struct Descriptor { uintptr_t reserved,size; } *descriptor; };
void *_NSConcreteStackBlock[32];
static struct Fake classes[16],strings[64],details,nav,stream,home,table,path,metadata,url,url_text,name,application,pasteboard;
static unsigned class_count,string_count,dismissals,opens,copies;
static NSInteger application_state;
static BOOL invalid_url;
static struct Block *completion;
Class objc_getClass(const char *name_value) {
    for(unsigned i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name_value))return &classes[i];
    assert(class_count<16);classes[class_count].cls=name_value;return &classes[class_count++];
}
SEL sel_registerName(const char *s) { return s; }
id objc_retain(id o) { if(o)o->refs++;return o; }
void objc_release(id o) { if(o){assert(o->refs);o->refs--;} }
id objc_getAssociatedObject(id o,const void *k) {
    if(!o)return nil;
    if(k==&g_metadata_key)return o->metadata;
    assert(k==&g_details_dismissing_key);return o->pending;
}
void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t policy) {
    assert(o==&details && k==&g_details_dismissing_key && policy==1);o->pending=v;
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"stringWithUTF8String:")){assert(string_count<64);result=&strings[string_count++];result->cls="NSString";result->text=va_arg(args,const char *);}
    else if(!strcmp(sel,"isKindOfClass:"))result=(id)(uintptr_t)!strcmp(o->cls,va_arg(args,Class)->cls);
    else if(!strcmp(sel,"objectForKey:")){id k=va_arg(args,id);assert(o==&metadata);result=!strcmp(k->text,"url") ? &url_text : &name;}
    else if(!strcmp(sel,"navigationController"))result=o->nav;
    else if(!strcmp(sel,"viewControllers"))result=o;
    else if(!strcmp(sel,"firstObject"))result=o->root;
    else if(!strcmp(sel,"presentingViewController"))result=o->presenter;
    else if(!strcmp(sel,"presentedViewController"))result=o->presented;
    else if(!strcmp(sel,"isBeingPresented"))result=(id)(uintptr_t)o->presenting;
    else if(!strcmp(sel,"isBeingDismissed"))result=(id)(uintptr_t)o->dismissing;
    else if(!strcmp(sel,"deselectRowAtIndexPath:animated:")){assert(o==&table && va_arg(args,id)==&path && va_arg(args,int));}
    else if(!strcmp(sel,"row"))result=(id)(uintptr_t)o->row;
    else if(!strcmp(sel,"URLWithString:")){assert(va_arg(args,id)==&url_text);result=invalid_url ? nil : &url;}
    else if(!strcmp(sel,"sharedApplication"))result=&application;
    else if(!strcmp(sel,"applicationState"))result=(id)(uintptr_t)application_state;
    else if(!strcmp(sel,"dictionary"))result=o;
    else if(!strcmp(sel,"generalPasteboard"))result=&pasteboard;
    else if(!strcmp(sel,"setString:")){id value=va_arg(args,id);assert(value==&name || value==&url_text);copies++;}
    else if(!strcmp(sel,"dismissViewControllerAnimated:completion:")){
        /* A Twitch stream/root dismissal is always a regression. */
        assert(o==&nav && stream.presented==&nav && !completion && va_arg(args,int));
        struct Block *block=(struct Block *)va_arg(args,id);
        if(block){completion=malloc(block->descriptor->size);assert(completion);memcpy(completion,block,block->descriptor->size);}
        o->dismissing=YES;dismissals++;
    }
    else if(!strcmp(sel,"openURL:options:completionHandler:")){
        assert(o==&application && !stream.presented && !details.nav && !nav.dismissing);
        assert(va_arg(args,id)==&url && url.refs==1 && va_arg(args,id));assert(!va_arg(args,id));
        assert(home.presented==&stream);opens++;application_state=2; /* Leave the app only AFTER sheet dismissal. */
    }
    else assert(!"unexpected browser action selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static void setup(void) {
    assert(!completion);
    details=(struct Fake){.cls="TASProviderEmoteController",.nav=&nav,.metadata=&metadata};
    nav=(struct Fake){.cls="UINavigationController",.presenter=&stream,.root=&details};
    stream=(struct Fake){.cls="UIViewController",.presented=&nav};
    home=(struct Fake){.cls="UIViewController",.presented=&stream};
    metadata.cls="NSDictionary";url.refs=1;application_state=0;invalid_url=NO;path.row=2;
}
static void finish(void) {
    /* The sheet and metadata are detached before UIKit invokes its copied
     * completion. Its URL must survive without a controller reference. */
    stream.presented=nil;details.nav=nil;details.metadata=nil;nav.dismissing=NO;
    if(completion){struct Block *block=completion;completion=NULL;objc_release(&url);block->invoke(block);free(block);assert(!url.refs);}
    assert(home.presented==&stream);
}
int main(void) {
    setup();details_select(&details,"select",&table,&path);
    assert(dismissals==1 && opens==0 && url.refs==2 && completion);
    details_select(&details,"select",&table,&path);details_close(&details,"close",nil);
    assert(dismissals==1 && opens==0 && url.refs==2);
    finish();assert(opens==1 && application_state==2);
    application_state=0;details_close(&details,"close",nil);assert(dismissals==1); /* Return cannot dismiss stream. */
    setup();application_state=1;details_select(&details,"select",&table,&path);
    finish();assert(dismissals==2 && opens==1); /* Independent interruption: do not launch from inactive app. */
    setup();invalid_url=YES;details_select(&details,"select",&table,&path);assert(dismissals==2 && url.refs==1 && !details.pending);
    setup();nav.presenting=YES;details_select(&details,"select",&table,&path);assert(dismissals==2 && url.refs==1);
    setup();nav.dismissing=YES;details_select(&details,"select",&table,&path);assert(dismissals==2 && url.refs==1);
    setup();nav.root=&home;details_select(&details,"select",&table,&path);assert(dismissals==2 && url.refs==1);
    setup();stream.presented=&home;details_select(&details,"select",&table,&path);assert(dismissals==2 && url.refs==1);
    setup();details.nav=nil;details_select(&details,"select",&table,&path);assert(dismissals==2 && url.refs==1);
    setup();path.row=0;details_select(&details,"select",&table,&path);
    assert(copies==1 && dismissals==3 && !completion && opens==1);finish();
    setup();path.row=1;details_select(&details,"select",&table,&path);
    assert(copies==2 && dismissals==4 && !completion && opens==1);finish();
    setup();details_close(&details,"close",nil);assert(dismissals==5 && !completion && opens==1);finish();
    setup();path.row=3;details_select(&details,"select",&table,&path);assert(dismissals==5 && opens==1 && !details.pending);
    return 0;
}
'''

SHEET = r'''
#include <assert.h>
#include <stdarg.h>
#include "TASEmoteUI.c"
struct Fake { const char *cls; id next,value,metadata,parent; unsigned refs; };
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
    else if(!strcmp(sel,"parentViewController"))result=o->parent;
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
    assert(!tas_emote_ui_modal_visible(&child));
    assert(tas_emote_ui_present_details(&child,&metadata));
    assert(presentations==1 && metadata.refs==2 && root.value->value->metadata==&metadata);
    assert(tas_emote_ui_modal_visible(&child));
    assert(!tas_emote_ui_present_details(&child,&metadata));assert(metadata.refs==2);
    objc_release(root.value);root.value=nil;assert(metadata.refs==1);
    assert(!tas_emote_ui_modal_visible(&child));
    struct Fake parent={.cls="UIViewController",.value=&metadata};root.parent=&parent;
    assert(tas_emote_ui_modal_visible(&child));root.parent=nil;
    assert(show_details(&child,9000000001ULL));assert(copies==1 && presentations==2 && metadata.refs==2);
    objc_release(root.value);root.value=nil;assert(metadata.refs==1);
    child.next=nil;assert(!show_details(&child,9000000001ULL));assert(copies==2 && metadata.refs==1);
    return 0;
}
'''
