from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_emote_ui import RUNTIME
ROOT = Path(__file__).resolve().parent.parent

MODEL = r'''
#include "SSComposerModel.h"
#include <assert.h>
int main(void) {
    /* Emoji before and between names count as two UTF-16 units, native
     * attachments as one. Carets, selection endpoints and deletion roundtrip. */
    SSSpan spans[]={{3,5},{11,9}};
    for (size_t p=0;p<=24;p++) {
        size_t shown=ss_display_position(p,spans,2),plain=ss_plain_position(shown,spans,2);
        if ((p>3 && p<8) || (p>11 && p<20)) assert(plain>=p);
        else assert(plain==p);
    }
    assert(ss_plain_position(3,spans,2)==3);
    assert(ss_plain_position(4,spans,2)==8);
    assert(ss_plain_position(7,spans,2)==11);
    assert(ss_plain_position(8,spans,2)==20);
    assert(ss_plain_position(8,spans,2)-ss_plain_position(7,spans,2)==9);
    uint16_t text[]={0xd83d,0xde00,' ',':','m','o','d',' ','x'}; SSSpan match;
    assert(ss_completion_span(text,9,7,1,&match)); assert(match.start==3 && match.length==4);
    assert(!ss_completion_span(text,9,6,1,&match)); /* inside word */
    assert(!ss_completion_span(text,9,7,2,&match)); /* disabled */
    uint16_t colon[]={':'}; assert(ss_completion_span(colon,1,1,1,&match) && match.length==1);
    uint16_t automatic[]={'m','o','d'};
    assert(ss_completion_span(automatic,3,3,0,&match));
    assert(!ss_completion_span(automatic,3,3,1,&match));
    assert(!ss_completion_span(automatic,3,1,0,&match));
    uint16_t url[]={'h','t','t','p',':','/','/','m','o','d'};
    assert(!ss_completion_span(url,10,10,0,&match));
    uint16_t preview[]={0xfffc,'m','o','d'};
    assert(ss_completion_span(preview,4,4,0,&match) && match.start==1);
    assert(!ss_completion_span(NULL,0,0,0,&match));
    assert(!ss_completion_span(text,9,100,0,&match));
    assert(ss_provider_matches(0,0) && ss_provider_matches(2,0));
    assert(ss_provider_matches(0,1) && !ss_provider_matches(1,1));
    assert(ss_provider_matches(1,2) && ss_provider_matches(2,3));
    assert(!ss_provider_matches(0,4));
    assert(ss_ascii_prefix("MODCHECK","mod") && ss_ascii_prefix("modCheck","MOD"));
    assert(!ss_ascii_prefix("mo","mod") && !ss_ascii_prefix("mod","moo"));
    unsigned char identity[56]={0}; uint32_t room=12345; uint64_t presence=1;
    memcpy(identity,&room,4); assert(!ss_identity_room(identity,56));
    memcpy(identity+16,&presence,8); identity[4]=255; /* padding is irrelevant */
    assert(ss_identity_room(identity,56)==12345);
    assert(!ss_identity_room(identity,55) && !ss_identity_room(NULL,56));
    /* A provider name at the caret remains text while it is being typed or
     * selected. Space commits it; UTF-16 offsets still include emoji. */
    assert(!ss_preview_token_safe(3,12,16,12,0));
    assert(!ss_preview_token_safe(3,12,16,6,0));
    assert(!ss_preview_token_safe(3,12,16,2,4));
    assert(ss_preview_token_safe(3,12,16,13,0));
    assert(ss_preview_token_safe(3,12,16,12,1));
    assert(ss_preview_token_safe(3,12,16,1,0));
    assert(!ss_preview_token_safe(3,12,16,17,0));
    return 0;
}
'''
EDITOR = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake { const char *cls; U length; uint16_t units[256]; id codes[256]; unsigned native[256]; };
static struct Fake cls={"NSString",0,{0},{0},{0}}, editor={"UITextView",0,{0},{0},{0}};
static struct Fake source={"NSAttributedString",0,{0},{0},{0}}, storage={"NSTextStorage",0,{0},{0},{0}}, strings[128];
static struct Fake ui_font={"UIFont",0,{0},{0},{0}},ui_color={"UIColor",0,{0},{0},{0}};
static struct Fake body_font={"UIFont",0,{0},{0},{0}},theme={"UIColor",0,{0},{0},{0}},typing={"NSDictionary",0,{0},{0},{0}};
static size_t used;
static unsigned storage_edits,styled;
static id ascii(const char *s) { id o=&strings[used++]; assert(used<128); o->cls="NSString"; o->length=strlen(s); for(U i=0;i<o->length;i++)o->units[i]=(unsigned char)s[i]; return o; }
static BOOL matches(id o,const char *s) { if(!o || o->length!=strlen(s))return NO; for(U i=0;i<o->length;i++)if(o->units[i]!=(unsigned char)s[i])return NO;return YES; }
Class objc_getClass(const char *name) {
    if(!strcmp(name,"NSString"))return &cls;
    if(!strcmp(name,"UIFont"))return &ui_font;
    if(!strcmp(name,"UIColor"))return &ui_color;
    assert(!"unexpected class");return nil;
}
SEL sel_registerName(const char *s) { return s; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil; va_list args; va_start(args,sel); id result=nil;
    if(!strcmp(sel,"attributedText"))result=&source;
    else if(!strcmp(sel,"string"))result=o;
    else if(!strcmp(sel,"characterAtIndex:")) { U i=va_arg(args,U);assert(i<o->length);result=(id)(uintptr_t)o->units[i]; }
    else if(!strcmp(sel,"labelColor"))result=&theme;
    else if(!strcmp(sel,"systemFontOfSize:")) { double size=va_arg(args,double);assert(size==17.0);result=&body_font; }
    else if(!strcmp(sel,"textStorage"))result=&storage;
    else if(!strcmp(sel,"typingAttributes"))result=&typing;
    else if(!strcmp(sel,"setTypingAttributes:")) { id attrs=va_arg(args,id);assert(attrs && attrs->cls && !strcmp(attrs->cls,"NSMutableAttributedString")); }
    else if(!strcmp(sel,"setObject:forKey:")) { id value=va_arg(args,id),key=va_arg(args,id);assert(value && (matches(key,"NSFont") || matches(key,"NSColor")));styled++; }
    else if(!strcmp(sel,"addAttribute:value:range:")) { id key=va_arg(args,id),value=va_arg(args,id);Range r=va_arg(args,Range);assert(value && r.location==0 && r.length==o->length && (matches(key,"NSFont") || matches(key,"NSColor")));styled++; }
    else if(!strcmp(sel,"beginEditing"))storage_edits++;
    else if(!strcmp(sel,"endEditing"))storage_edits++;
    else if(!strcmp(sel,"setSelectedRange:")) { Range r=va_arg(args,Range); assert(r.location==1 && r.length==0); }
    else if(!strcmp(sel,"replaceCharactersInRange:withAttributedString:")) {
        Range r=va_arg(args,Range); id value=va_arg(args,id);
        assert(o==&storage && r.location==0 && r.length==storage.length);
        storage.length=value->length; memcpy(storage.units,value->units,storage.length*2);
    }
    else if(!strcmp(sel,"mutableCopy")) { result=malloc(sizeof(*result)); memcpy(result,o,sizeof(*result)); result->cls="NSMutableAttributedString"; }
    else if(!strcmp(sel,"stringWithUTF8String:")) result=ascii(va_arg(args,const char *));
    else if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(args,Class); result=(id)(uintptr_t)!strcmp(o->cls,c->cls); }
    else if(!strcmp(sel,"length")) result=(id)(uintptr_t)o->length;
    else if(!strcmp(sel,"attribute:atIndex:effectiveRange:")) { id k=va_arg(args,id); U i=va_arg(args,U); (void)va_arg(args,Range *); assert(matches(k,ATTACHMENT_KEY) && i<o->length); result=o->codes[i]; }
    else if(!strcmp(sel,"replaceCharactersInRange:withString:")) {
        Range r=va_arg(args,Range); id v=va_arg(args,id); assert(r.location+r.length<=o->length);
        size_t tail=o->length-r.location-r.length;
        memmove(o->units+r.location+v->length,o->units+r.location+r.length,tail*2);
        memmove(o->codes+r.location+v->length,o->codes+r.location+r.length,tail*sizeof(id));
        memmove(o->native+r.location+v->length,o->native+r.location+r.length,tail*sizeof(unsigned));
        id inherited=o->codes[r.location]; unsigned native=o->native[r.location];
        for(U i=0;i<v->length;i++){o->units[r.location+i]=v->units[i];o->codes[r.location+i]=inherited;o->native[r.location+i]=native;}
        o->length+=v->length-r.length;
    } else if(!strcmp(sel,"removeAttribute:range:")) {
        id k=va_arg(args,id); Range r=va_arg(args,Range); assert(r.location+r.length<=o->length);
        for(U i=r.location;i<r.location+r.length;i++) { if(matches(k,ATTACHMENT_KEY))o->codes[i]=nil; else if(matches(k,"NSAttachment"))o->native[i]=0; else assert(0); }
    } else assert(!"unexpected editor selector");
    va_end(args); return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
void objc_release(id o) { (void)o; }
int main(void) {
    /* Two Streamside attachments plus a native attachment, emoji, newline and
     * ordinary text. Exercise the production expansion, not a copy of it. */
    uint16_t text[]={0xd83d,0xde00,' ',0xfffc,' ',0xfffc,'\n',0xfffc,'!'};
    source.length=9; memcpy(source.units,text,sizeof(text));
    source.codes[3]=ascii("WideEmote"); source.codes[7]=ascii("modCheck"); source.native[3]=11; source.native[5]=42; source.native[7]=12;
    Range selected={7,1}; SSSpan spans[MAX_TOKENS]; size_t n;
    id plain=expanded_copy(&editor,&selected,spans,&n);
    assert(n==2 && spans[0].start==3 && spans[0].length==9 && spans[1].start==15 && spans[1].length==8);
    assert(selected.location==15 && selected.length==8 && plain->length==24);
    assert(plain->units[0]==0xd83d && plain->units[1]==0xde00);
    assert(plain->units[13]==0xfffc && plain->native[13]==42); /* native untouched */
    assert(plain->units[14]=='\n' && plain->units[23]=='!');
    for(U i=0;i<plain->length;i++) assert(!plain->codes[i]);
    assert(plain->native[3]==0 && plain->native[15]==0);
    assert(source.units[3]==0xfffc && source.native[5]==42 && source.length==9); /* snapshot isolation */
    /* Async image refresh updates presentation without querying the undo
     * manager; the latter threw on-device during NSOperation notification. */
    storage.length=9; visual_text(&editor,plain,(Range){1,0});
    assert(storage_edits==2 && storage.length==24 && storage.units[3]=='W' && styled==4);
    free(plain); return 0;
}
'''

CONTROLS = EDITOR[:EDITOR.index("int main(void)")].replace(
    'assert(!"unexpected class");return nil;',
    'return nil;')
CONTROLS = CONTROLS.replace(
    'else assert(!"unexpected editor selector");',
    'else if(!strcmp(sel,"selectedSegmentIndex")) result=(id)(uintptr_t)o->length;\n'
    '    else if(!strcmp(sel,"setSelectedSegmentIndex:")) o->length=(U)va_arg(args,I);\n'
    '    else assert(!"unexpected editor selector");')
CONTROLS += r'''
static unsigned mutations;
static void marker(void) {}
struct MockMethod { const char *encoding; } method={"v24@0:8@16"};
Class object_getClass(id o) { return o ? &cls : nil; }
Ivar class_getInstanceVariable(Class c,const char *name) { return c && !strcmp(name,"_state") ? (Ivar)1 : NULL; }
ptrdiff_t ivar_getOffset(Ivar i) { assert(i); return offsetof(struct Fake,codes)+255*sizeof(id); }
size_t class_getInstanceSize(Class c) { (void)c; return sizeof(struct Fake); }
Method class_getInstanceMethod(Class c,SEL sel) { (void)sel; return c ? &method : NULL; }
const char *method_getTypeEncoding(Method m) { return ((struct MockMethod *)m)->encoding; }
IMP method_getImplementation(Method m) { (void)m; return marker; }
BOOL class_addMethod(Class c,SEL s,IMP f,const char *types) { (void)c;(void)s;(void)f;(void)types;return NO; }
IMP method_setImplementation(Method m,IMP f) { (void)m;(void)f;mutations++;return marker; }
id objc_loadWeakRetained(id *p) { return *p; }
id objc_initWeak(id *p,id o) { *p=o;return o; }
void objc_destroyWeak(id *p) { *p=nil; }
id objc_retain(id o) { return o; }
id objc_getAssociatedObject(id o,const void *k) { (void)o;(void)k;return nil; }
void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t policy) { (void)o;(void)k;(void)v;(void)policy; }
id tas_emotes_named_copy(id c,id n) { (void)c;(void)n;return nil; }
id tas_emotes_picker_copy(id c,int p,int scope,id q,size_t n) { (void)c;(void)p;(void)scope;(void)q;(void)n;return nil; }
bool tas_emotes_is_provider_image_url(const char *url) { (void)url;return false; }
void *_NSConcreteStackBlock[32];
int main(void) {
    (void)editor; struct Fake delegate={0},control={0},scope={0}; State context={0};
    delegate_class=&cls; delegate.codes[255]=(id)&context; context.scope=&scope;
    for(int provider=0;provider<4;provider++) {
        context.library_scope=1; scope.length=1; control.length=(U)provider;
        provider_changed(&delegate,"ssProvider:",&control);
        assert(context.library==provider && context.library_scope==0 && scope.length==0);
    }
    control.length=1; scope_changed(&delegate,"ssScope:",&control); assert(context.library_scope==1);
    IMP original=NULL;
    assert(!hook("NSString","test:","v16@0:8",marker,&original));
    assert(!original && !mutations); /* same selector, wrong ABI: untouched */
    assert(!hook("Missing","test:","v24@0:8@16",marker,&original));
    assert(hook("NSString","test:","v24@0:8@16",marker,&original));
    assert(original==marker && mutations==1);
    assert(hook("NSString","test:","v24@0:8@16",marker,&original) && mutations==1); /* idempotent */
    return 0;
}
'''

AUTOCORRECT = EDITOR[:EDITOR.index("int main(void)")]
AUTOCORRECT = AUTOCORRECT.replace('static unsigned storage_edits,styled;',
    'static unsigned storage_edits,styled,selection_sets; static BOOL marked,on_main=YES;')
AUTOCORRECT = AUTOCORRECT.replace('if(!strcmp(name,"NSString"))return &cls;',
    'if(!strcmp(name,"NSThread") || !strcmp(name,"NSObject"))return &cls;\n'
    '    if(!strcmp(name,"NSTextStorage"))return &storage;\n    if(!strcmp(name,"NSString"))return &cls;')
AUTOCORRECT = AUTOCORRECT.replace('else if(!strcmp(sel,"textStorage"))result=&storage;',
    'else if(!strcmp(sel,"textStorage"))result=editor_storage(o,sel);\n'
    '    else if(!strcmp(sel,"text"))result=editor_text(o,sel);\n'
    '    else if(!strcmp(sel,"isMainThread"))result=(id)(uintptr_t)on_main;\n'
    '    else if(!strcmp(sel,"markedTextRange"))result=marked ? &typing : nil;')
AUTOCORRECT = AUTOCORRECT.replace('else assert(!"unexpected editor selector");',
    'else if(!strcmp(sel,"objectForKey:"))result=nil;\n'
    '    else if(!strcmp(sel,"alloc")) { result=calloc(1,sizeof(*result));result->cls="NSTextStorage"; }\n'
    '    else if(!strcmp(sel,"initWithAttributedString:")) { id value=va_arg(args,id);memcpy(o,value,sizeof(*o));o->cls="NSTextStorage";result=o; }\n'
    '    else if(!strcmp(sel,"cancelPreviousPerformRequestsWithTarget:selector:object:")) {}\n'
    '    else if(!strcmp(sel,"performSelector:withObject:afterDelay:")) {}\n'
    '    else assert(!"unexpected editor selector");')
AUTOCORRECT = AUTOCORRECT.replace('assert(r.location==1 && r.length==0);',
    '(void)r;selection_sets++;')
AUTOCORRECT += '\nstatic id fake_delegate;\n' + CONTROLS[CONTROLS.index('static unsigned mutations;'):CONTROLS.index('int main(void)')].replace(
    '(void)o;(void)k;return nil;', '(void)o;return k==&state_key ? fake_delegate : nil;')
AUTOCORRECT += r'''
static struct Fake other={"UITextView",0,{0},{0},{0}};
static Range expected_range;
static U expected_length;
static BOOL accept=YES,expected_snapshot=YES,expected_storage_snapshot=YES;
static unsigned validated,notified;
static id raw_text(id o,SEL sel) { (void)sel;return o==&editor ? &source : &other; }
static id raw_storage(id o,SEL sel) { (void)sel;return o==&editor ? &storage : &other; }
static void assert_native_reads(id input) {
    id text=m0(input,"text"),contents=m0(input,"textStorage");
    assert(text->length==expected_length);
    assert(contents->length==(expected_storage_snapshot ? expected_length : source.length));
    if(expected_snapshot) {
        assert(text->units[3]=='W' && !text->codes[3]);
        assert(source.units[3]==0xfffc && storage.units[3]==0xfffc);
    } else assert(contents==&storage && text==&source);
    if(expected_storage_snapshot) assert(contents!=&storage && !strcmp(contents->cls,"NSTextStorage"));
    else assert(contents==&storage);
    assert(m0(&other,"text")==&other && m0(&other,"textStorage")==&other);
    if(expected_snapshot) {
        on_main=NO;assert(m0(input,"text")==&source && m0(input,"textStorage")==&storage);on_main=YES;
    }
}
static BOOL validate(id owner,SEL sel,id input,Range r,id replacement) {
    (void)owner;(void)sel;assert(replacement && r.location==expected_range.location && r.length==expected_range.length);
    assert_native_reads(input);validated++;return accept;
}
static void notify(id owner,SEL sel,id input) { (void)owner;(void)sel;BOOL prior=expected_storage_snapshot;expected_storage_snapshot=NO;assert_native_reads(input);expected_storage_snapshot=prior;notified++; }
int main(void) {
    (void)storage_edits;(void)styled;
    original_text=(IMP)raw_text;original_storage=(IMP)raw_storage;
    original_should_change=(IMP)validate;original_change=(IMP)notify;
    /* An emoji and earlier preview precede a misspelled word. The keyboard
     * wants to fix that word while its caret is farther ahead, after " xy". */
    uint16_t text[]={0xd83d,0xde00,' ',0xfffc,' ','t','e','h',' ','x','y'};
    source.length=11;memcpy(source.units,text,sizeof(text));source.codes[3]=ascii("WideEmote");source.native[3]=11;
    memcpy(&storage,&source,sizeof(source));storage.cls="NSTextStorage";
    id correction=ascii("the");expected_range=(Range){13,3};expected_length=19;
    assert(native_validation(nil,"validate",&editor,(Range){5,3},correction));
    assert(!native_read && !storage_edits && !selection_sets && validated==1);
    assert(source.length==11 && source.units[3]==0xfffc && source.units[6]=='e');
    assert(m0(&editor,"text")==&source && m0(&editor,"textStorage")==&storage);
    /* UIKit applies its own displayed range and preserves its farther caret.
     * didChange only serializes the new value; it never changes selection. */
    source.units[6]='h';source.units[7]='e';storage.units[6]='h';storage.units[7]='e';
    native_changed(nil,"notify",&editor);
    assert(notified==1 && !native_read && !storage_edits && !selection_sets);
    expected_range=(Range){3,9};
    assert(native_validation(nil,"validate",&editor,(Range){3,1},ascii(""))); /* whole-emote deletion */
    accept=NO;expected_range=(Range){13,3};
    assert(!native_validation(nil,"validate",&editor,(Range){5,3},correction)); /* native veto retained */
    assert(!native_read && !storage_edits && !selection_sets);
    /* Marked/IME transactions keep the exact live storage and offsets. */
    marked=YES;accept=YES;expected_snapshot=NO;expected_storage_snapshot=NO;expected_length=11;expected_range=(Range){5,3};
    assert(native_validation(nil,"validate",&editor,(Range){5,3},correction));
    native_changed(nil,"notify",&editor);assert(notified==2 && !native_read);
    marked=NO;expected_storage_snapshot=YES;
    /* Stray inherited metadata on a normal character must not serialize that
     * character as another emote. Only U+FFFC owns an attachment code. */
    source.codes[6]=source.codes[3];SSSpan spans[MAX_TOKENS];size_t n;
    id plain=expanded_copy(&editor,NULL,spans,&n);
    assert(n==1 && plain->length==19 && plain->units[14]=='h');
    assert(!storage_edits && !selection_sets);free(plain);
    /* Exercise the actual delegate entry points. Existing attachments used to
     * make shouldChange return NO and manually replace text/caret. Selection
     * and didChange used to expand and render synchronously. */
    struct Fake delegate={0};State context={0};delegate.codes[255]=(id)&context;
    delegate_class=&cls;fake_delegate=&delegate;expected_snapshot=YES;expected_length=19;expected_range=(Range){13,3};
    assert(should_change(&other,"validate",&editor,(Range){5,3},correction));
    assert(context.preview_scheduled && !storage_edits && !selection_sets);
    did_change(&other,"notify",&editor);assert(context.preview_scheduled && !storage_edits && !selection_sets);
    original_selection=(IMP)notify;
    expected_snapshot=NO;expected_length=11;did_select(&other,"select",&editor);
    assert(context.preview_scheduled && !native_read && !storage_edits && !selection_sets);
    return 0;
}
'''

TOUCHES = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake { id parent,window; Rect frame; BOOL hidden,responder; U count; };
static unsigned adds,fronts;
SEL sel_registerName(const char *s) { return s; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;
    va_list args; va_start(args,sel); id result=nil;
    if(!strcmp(sel,"window"))result=o->window;
    else if(!strcmp(sel,"superview"))result=o->parent;
    else if(!strcmp(sel,"setFrame:"))o->frame=va_arg(args,Rect);
    else if(!strcmp(sel,"addSubview:")) { id child=va_arg(args,id);child->parent=o;adds++; }
    else if(!strcmp(sel,"bringSubviewToFront:")) { id child=va_arg(args,id);assert(child->parent==o);fronts++; }
    else if(!strcmp(sel,"setHidden:"))o->hidden=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"isFirstResponder"))result=(id)(uintptr_t)o->responder;
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"removeFromSuperview"))o->parent=nil;
    else assert(!"unexpected touch layout selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static BOOL contains(Rect r,Point p) {
    return p.x>=r.origin.x && p.y>=r.origin.y && p.x<r.origin.x+r.size.width && p.y<r.origin.y+r.size.height;
}
int main(void) {
    /* Reproduce a visible strip above a 44pt chat parent. UIKit rejects
     * touches outside that ancestor, regardless of clipsToBounds. Exercise
     * production placement with window coordinates, then scene replacement. */
    struct Fake window={.frame={{0,0},{390,844}}},parent={.frame={{0,600},{390,44}}};
    struct Fake owner={.parent=&parent,.window=&window},input={.responder=YES};
    struct Fake strip={.parent=&parent},items={.count=5};
    State s={.strip=&strip,.suggestions=&items};
    Rect position={{8,600},{374,44}},bounds=window.frame;
    Point tap={40,570};assert(!contains(parent.frame,tap));
    place_suggestion_strip(&s,&owner,&input,position,bounds);
    assert(strip.parent==&window && !strip.hidden && adds==1 && fronts==1);
    assert(strip.frame.origin.x==8 && strip.frame.origin.y==552 && strip.frame.size.width==374 && strip.frame.size.height==48);
    assert(contains(window.frame,tap) && contains(strip.frame,tap));
    assert(!contains(strip.frame,(Point){40,610})); /* input remains outside overlay */
    place_suggestion_strip(&s,&owner,&input,position,bounds);assert(adds==1);
    input.responder=NO;place_suggestion_strip(&s,&owner,&input,position,bounds);assert(strip.hidden);
    input.responder=YES;items.count=0;place_suggestion_strip(&s,&owner,&input,position,bounds);assert(strip.hidden);
    items.count=5;position.origin.y=20;place_suggestion_strip(&s,&owner,&input,position,bounds);assert(strip.hidden);
    struct Fake second={.frame={{0,0},{844,390}}};owner.window=&second;
    position=(Rect){{100,280},{644,44}};place_suggestion_strip(&s,&owner,&input,position,second.frame);
    assert(strip.parent==&second && !strip.hidden && adds==2 && strip.frame.origin.y==232);
    owner.window=nil;place_suggestion_strip(&s,&owner,&input,position,second.frame);assert(!strip.parent);
    return 0;
}
'''

class ComposerTests(unittest.TestCase):
    def test_utf16_edits_and_completion_boundaries(self):
        self.compile_run(MODEL, ["cc", "-std=c11", "-fsanitize=address,undefined"])

    def test_native_editor_serializes_codes_and_preserves_other_attachments(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        self.compile_run(EDITOR, [zig, "cc", "-fblocks"], runtime=True)

    def test_provider_switch_resets_channel_and_incompatible_hooks_are_untouched(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        self.compile_run(CONTROLS, [zig, "cc", "-fblocks"], runtime=True)

    def test_suggestions_move_out_of_chat_bounds_into_the_owning_scene(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        self.compile_run(TOUCHES, [zig, "cc", "-fblocks"], runtime=True)

    def test_keyboard_corrections_validate_snapshots_without_replacing_live_text(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        self.compile_run(AUTOCORRECT, [zig, "cc", "-fblocks"], runtime=True)

    def compile_run(self, content, compiler, runtime=False):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            if runtime:
                (directory / "objc").mkdir()
                for h in ("objc.h", "runtime.h", "message.h"):
                    (directory / "objc" / h).write_text(RUNTIME + '\nsize_t class_getInstanceSize(Class);\nBOOL class_addIvar(Class,const char *,size_t,uint8_t,const char *);\nconst char *sel_getName(SEL);\n')
            harness=directory / "composer.c"; binary=directory / "composer"
            harness.write_text(content)
            subprocess.run(compiler + ["-Wall", "-Wextra", "-Werror", "-ffunction-sections", "-fdata-sections",
                "-Wl,--gc-sections", *(["-Wno-cast-function-type-mismatch"] if runtime else []), "-I", str(directory), "-I", str(ROOT / "src"), str(harness), "-o", str(binary)],
                check=True, capture_output=True)
            subprocess.run([binary], check=True, capture_output=True, env={**os.environ,"ASAN_OPTIONS":"detect_leaks=0"})
