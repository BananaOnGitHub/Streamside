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
Class objc_allocateClassPair(Class c,const char *name,size_t bytes) { (void)c;(void)name;(void)bytes;return nil; }
void objc_registerClassPair(Class c) { (void)c; }
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

SCROLL = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake { Rect frame; Size content; Point offset; BOOL options[8]; I dismiss; };
static struct Fake base,owned,palette,scroll,button,background;
static unsigned allocated,registered;
static IMP cancellation;
Class objc_getClass(const char *name) {
    if(!strcmp(name,"UIScrollView"))return &base;
    if(!strcmp(name,"UIColor"))return &palette;
    assert(!"unexpected scroll class");return nil;
}
SEL sel_registerName(const char *s) { return s; }
Method class_getInstanceMethod(Class c,SEL sel) { assert(c==&base && !strcmp(sel,"touchesShouldCancelInContentView:"));return (Method)1; }
const char *method_getTypeEncoding(Method m) { assert(m);return "B24@0:8@16"; }
Class objc_allocateClassPair(Class c,const char *name,size_t bytes) { assert(c==&base && !strcmp(name,"SSComposerScrollView") && !bytes);allocated++;return &owned; }
BOOL class_addMethod(Class c,SEL sel,IMP imp,const char *types) {
    assert(c==&owned && !strcmp(sel,"touchesShouldCancelInContentView:") && !strcmp(types,"B24@0:8@16"));cancellation=imp;return YES;
}
void objc_registerClassPair(Class c) { assert(c==&owned && cancellation);registered++; }
static id dispatch(id o,SEL sel,...) {
    assert(o);va_list args;va_start(args,sel);id result=nil;
    const char *names[]={"setScrollEnabled:","setCanCancelContentTouches:","setDelaysContentTouches:",
        "setAlwaysBounceHorizontal:","setAlwaysBounceVertical:","setDirectionalLockEnabled:",
        "setShowsHorizontalScrollIndicator:","setShowsVerticalScrollIndicator:"};
    unsigned option=0;for(;option<8;option++)if(!strcmp(sel,names[option]))break;
    if(option<8)o->options[option]=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"alloc")) { assert(o==&owned);result=&scroll; }
    else if(!strcmp(sel,"initWithFrame:")) { o->frame=va_arg(args,Rect);result=o; }
    else if(!strcmp(sel,"secondarySystemBackgroundColor"))result=&background;
    else if(!strcmp(sel,"setBackgroundColor:"))assert(va_arg(args,id)==&background);
    else if(!strcmp(sel,"setKeyboardDismissMode:"))o->dismiss=va_arg(args,I);
    else if(!strcmp(sel,"setContentSize:"))o->content=va_arg(args,Size);
    else if(!strcmp(sel,"setContentOffset:"))o->offset=va_arg(args,Point);
    else assert(!"unexpected scroll selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
int main(void) {
    /* The real factory registers an isolated subclass. Swipes starting on
     * UIButton tiles may cancel tracking; ordinary touch-up selection stays
     * on the button. Twitch's own scroll views are never changed. */
    id row=make_strip();assert(row==&scroll && allocated==1 && registered==1);
    assert(scroll.options[0] && scroll.options[1] && !scroll.options[2]);
    assert(scroll.options[3] && !scroll.options[4] && scroll.options[5]);
    assert(scroll.options[6] && !scroll.options[7] && scroll.dismiss==0);
    assert(((BOOL (*)(id,SEL,id))cancellation)(row,"touchesShouldCancelInContentView:",&button));
    assert(((BOOL (*)(id,SEL,id))cancellation)(row,"touchesShouldCancelInContentView:",&background));
    assert(!GET(strip_taps) && !GET(insertions)); /* requesting drag cancellation is not an emote tap */
    set_strip_extent(row,24);assert(scroll.content.width==1536 && scroll.content.height==48);
    assert(scroll.content.width>scroll.frame.size.width && scroll.content.height==scroll.frame.size.height);
    scroll.offset=(Point){1216,0};set_strip_extent(row,2);
    assert(scroll.content.width==128 && scroll.offset.x==0 && scroll.offset.y==0); /* new search resets stale offset */
    assert(make_strip()==row && allocated==1 && registered==1);
    return 0;
}
'''

RECENTS = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake {
    const char *cls;
    id parent,host,views[6],children[4],tint,background,heading,title;
    State *context;
    Rect frame,bounds;
    Insets inset,adjusted;
    Point offset;
    U count;
    BOOL hidden;
};
static struct Fake classes[16]; static U class_count;
static unsigned inset_sets,offset_sets,original_layouts;
static State *current;
Class objc_getClass(const char *name) {
    for(U i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name))return &classes[i];
    assert(class_count<16);classes[class_count].cls=name;return &classes[class_count++];
}
Class object_getClass(id o) { return o; }
SEL sel_registerName(const char *s) { return s; }
Ivar class_getInstanceVariable(Class c,const char *name) {
    (void)c;
    if(!strcmp(name,"_state"))return (Ivar)(uintptr_t)offsetof(struct Fake,context);
    const char *names[]={"$__lazy_storage_$_recentEmotesButton","$__lazy_storage_$_channelEmotesButton",
        "$__lazy_storage_$_allEmotesButton","recentEmotesHighlight","channelEmotesHighlight","allEmotesHighlight"};
    for(U i=0;i<6;i++)if(!strcmp(name,names[i]))return (Ivar)(uintptr_t)(offsetof(struct Fake,views)+i*sizeof(id));
    if(!strcmp(name,"titleLabel"))return (Ivar)(uintptr_t)offsetof(struct Fake,title);
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return (ptrdiff_t)(uintptr_t)iv; }
size_t class_getInstanceSize(Class c) { (void)c;return sizeof(struct Fake); }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_loadWeakRetained(id *p) { return *p; }
id objc_initWeak(id *p,id o) { *p=o;return o; }
void objc_destroyWeak(id *p) { *p=nil; }
id objc_getAssociatedObject(id o,const void *key) { return o && key==&recent_host_key ? o->host : nil; }
void objc_setAssociatedObject(id o,const void *key,id value,uintptr_t policy) { assert(key==&recent_host_key && policy==1);o->host=value; }
void *ss_test_field(id o,const char *name) {
    assert(o);
    if(!strcmp(name,"frame"))return &o->frame;
    if(!strcmp(name,"bounds"))return &o->bounds;
    if(!strcmp(name,"contentInset"))return &o->inset;
    if(!strcmp(name,"adjustedContentInset"))return &o->adjusted;
    if(!strcmp(name,"contentOffset"))return &o->offset;
    assert(!"unexpected geometry getter");return NULL;
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(args,Class);result=(id)(uintptr_t)(!strcmp(o->cls,c->cls) || (!strcmp(c->cls,"UIView") && !strcmp(o->cls,"UIButton"))); }
    else if(!strcmp(sel,"respondsToSelector:")) { (void)va_arg(args,SEL);result=(id)1; }
    else if(!strcmp(sel,"supplementaryViewForElementKind:atIndexPath:")) { (void)va_arg(args,id);(void)va_arg(args,id);result=o->heading; }
    else if(!strcmp(sel,"mainBundle"))result=o;
    else if(!strcmp(sel,"localizedStringForKey:value:table:")) { result=va_arg(args,id);(void)va_arg(args,id);(void)va_arg(args,id); }
    else if(!strcmp(sel,"text"))result=o->tint;
    else if(!strcmp(sel,"collectionViewLayout"))result=o;
    else if(!strcmp(sel,"invalidateLayout")) { }
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"stringWithUTF8String:")) { (void)va_arg(args,const char *);result=objc_getClass("NSString"); }
    else if(!strcmp(sel,"indexPathForItem:inSection:")) { (void)va_arg(args,I);(void)va_arg(args,I);result=o; }
    else if(!strcmp(sel,"isEqual:"))result=(id)(uintptr_t)(o==va_arg(args,id));
    else if(!strcmp(sel,"subviews"))result=o;
    else if(!strcmp(sel,"objectAtIndex:")) { U i=va_arg(args,U);assert(i<o->count);result=o->children[i]; }
    else if(!strcmp(sel,"superview"))result=o->parent;
    else if(!strcmp(sel,"addSubview:"))va_arg(args,id)->parent=o;
    else if(!strcmp(sel,"removeFromSuperview"))o->parent=nil;
    else if(!strcmp(sel,"bringSubviewToFront:"))assert(va_arg(args,id)->parent==o);
    else if(!strcmp(sel,"setFrame:"))o->frame=va_arg(args,Rect);
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"tintColor"))result=o->tint;
    else if(!strcmp(sel,"backgroundColor"))result=o->background;
    else if(!strcmp(sel,"setTintColor:"))o->tint=va_arg(args,id);
    else if(!strcmp(sel,"setBackgroundColor:"))o->background=va_arg(args,id);
    else if(!strcmp(sel,"setContentInset:")) {
        Insets value=va_arg(args,Insets);double safe=o->adjusted.top-o->inset.top;
        o->inset=value;o->adjusted=value;o->adjusted.top+=safe;inset_sets++;
        if(o->host) place_recent_strip(current,o); /* UIKit can reenter during mutation. */
    } else if(!strcmp(sel,"setContentOffset:") || !strcmp(sel,"setContentOffset:animated:")) {
        o->offset=va_arg(args,Point);o->bounds.origin=o->offset;offset_sets++;
        if(!strcmp(sel,"setContentOffset:animated:"))assert(!va_arg(args,int));
    } else assert(!"unexpected recent selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
/* Named struct arguments preserve the host ABI; a nonvariadic objc_msgSend
 * cast cannot safely call our variadic mock for floating-point aggregates. */
void ss_test_frame(id o,Rect value) { dispatch(o,"setFrame:",value); }
void ss_test_inset(id o,Insets value) { dispatch(o,"setContentInset:",value); }
void ss_test_offset(id o,Point value) { dispatch(o,"setContentOffset:",value); }
void ss_test_offset_animated(id o,Point value,BOOL animated) { dispatch(o,"setContentOffset:animated:",value,animated); }
static void native_layout(id o,SEL sel) { (void)o;(void)sel;original_layouts++; }
int main(void) {
    struct Fake ordinary={.cls="UIColor"},active={.cls="UIColor"};
    struct Fake buttons[6]={0},footer={.cls="UIView"};
    for(U i=0;i<6;i++) { buttons[i].cls=i<3 ? "UIButton":"UIView";buttons[i].tint=&ordinary;footer.views[i]=&buttons[i]; }
    buttons[1].tint=&active;buttons[4].background=&active; /* native Channel selected; native Recent empty */
    struct Fake items={.count=3},clip={.cls="UIView"},row={.cls="UIScrollView",.parent=&clip};
    struct Fake native={.cls="UICollectionView",.bounds={{0,-20},{390,220}},.inset={8,2,4,6},.adjusted={20,2,4,6},.offset={0,-20}};
    State s={.recent_strip=&row,.recent_clip=&clip,.recent_entries=&items,.footer=&footer};current=&s;
    struct Fake delegate={.context=&s},container={.cls="UIView",.children={&native},.count=1};delegate_class=&delegate;
    original_collection_layout=(IMP)native_layout;
    /* No Recent button press: tab remains the default native library. */
    bind_recents(&delegate,&container);
    assert(!s.tab && clip.parent==&native && row.parent==&clip && s.recent_content==&native && native.host==&delegate);
    assert(native.inset.top==56 && native.inset.bottom==4 && native.offset.y==-68);
    assert(clip.frame.origin.y==-48 && row.frame.origin.y==0 && row.frame.size.width==390 && row.frame.size.height==48);
    assert(s.recent_highlight_active && buttons[3].background==&active && !buttons[4].background);
    assert(buttons[0].tint==&active && buttons[1].tint==&ordinary);
    unsigned offsets=offset_sets,insets=inset_sets;
    row.offset.x=192;
    bind_recents(&delegate,&container);collection_layout(&native,"layoutSubviews");
    assert(offset_sets==offsets && inset_sets==insets && row.offset.x==192 && original_layouts==1);
    struct Fake title={.cls="UILabel",.tint=objc_getClass("NSString")};
    struct Fake heading={.cls=PALETTE_HEADER,.title=&title,.bounds={{0,0},{390,44}},.frame={{0,-48},{390,44}}};native.heading=&heading;
    place_recent_strip(&s,&native);
    assert(s.recent_header_height==44 && clip.frame.origin.y==-4 && row.frame.origin.y==0);
    assert(native.inset.top==56 && offset_sets==offsets && row.offset.x==192);
    title.tint=&ordinary;place_recent_strip(&s,&native); /* A Channel header is never moved. */
    assert(!s.recent_header_height && clip.frame.origin.y==-48 && row.frame.origin.y==0 && offset_sets==offsets);
    title.tint=objc_getClass("NSString");place_recent_strip(&s,&native);
    assert(s.recent_header_height==44 && clip.frame.origin.y==-4 && row.frame.origin.y==0 && offset_sets==offsets);
    /* On a vertical swipe the native title pins, and the row must disappear
     * beneath its lower edge even when the header background is transparent.
     * The full scroll view keeps its geometry/offset inside a clipped viewport;
     * UIKit hit testing rejects the removed area because it is outside that
     * viewport. Unscrolling restores the original row without rebuilding it. */
    for (int delta=0;delta<=60;delta++) {
        heading.frame.origin.y=-48+delta;
        native.bounds.origin.y=-68+delta;
        native.offset.y=native.bounds.origin.y;
        collection_layout(&native,"layoutSubviews");
        double removed=delta>48 ? 48 : delta;
        assert(clip.frame.origin.y==-4+removed && clip.frame.size.height==48-removed);
        assert(row.frame.origin.y==-removed && row.frame.size.height==48);
        assert(clip.frame.origin.y+row.frame.origin.y==-4); /* content never jumps */
        assert(!clip.frame.size.height || clip.frame.origin.y>=heading.frame.origin.y+44);
        assert(row.offset.x==192 && offset_sets==offsets && inset_sets==insets);
    }
    heading.frame.origin.y=-48;native.bounds.origin.y=-68;native.offset.y=-68;
    collection_layout(&native,"layoutSubviews");
    assert(clip.frame.origin.y==-4 && clip.frame.size.height==48 && !row.frame.origin.y);
    native.heading=nil; /* UIKit recycles the title while browsing. */
    /* Native vertical scrolling moves the row with content, never pins it. */
    native.offset.y=100;native.bounds.origin.y=100;collection_layout(&native,"layoutSubviews");
    assert(clip.frame.origin.y+row.frame.origin.y-native.bounds.origin.y==-104 && offset_sets==offsets);
    assert(!s.recent_highlight_active && !buttons[3].background && buttons[4].background==&active);
    assert(buttons[1].tint==&active && buttons[0].tint==&ordinary);
    struct Fake unrelated={.cls="UICollectionView"};collection_layout(&unrelated,"layoutSubviews");
    assert(!unrelated.inset.top && !unrelated.host && original_layouts==65);
    /* Recent navigation includes the provider row; provider overlay retains
     * it inside the hidden native collection, rather than over the grid. */
    scroll_to_recents(&s);assert(native.offset.y==-68);
    s.tab=1;native.hidden=YES;place_recent_strip(&s,&native);
    assert(clip.parent==&native && row.parent==&clip && !s.recent_highlight_active);
    s.tab=0;native.hidden=NO;
    /* Rotation changes width without moving the user's scroll position. */
    native.bounds.size.width=844;native.bounds.origin.y=300;native.offset.y=300;
    offsets=offset_sets;place_recent_strip(&s,&native);
    assert(row.frame.size.width==844 && native.offset.y==300 && offset_sets==offsets);
    /* Empty history removes exactly the owned height, preserving native
     * bottom/side insets and independent changes to the top inset. */
    native.inset.top+=7;native.adjusted.top+=7;items.count=0;
    place_recent_strip(&s,&native);
    assert(!clip.parent && row.parent==&clip && native.inset.top==15 && native.inset.bottom==4 && native.offset.y==300);
    items.count=3;place_recent_strip(&s,&native);assert(native.inset.top==63 && native.offset.y==300);
    struct Fake replacement={.cls="UICollectionView",.bounds={{0,0},{320,200}}};container.children[0]=&replacement;
    bind_recents(&delegate,&container);
    assert(native.inset.top==15 && !native.host && replacement.inset.top==48 && replacement.offset.y==-48);
    assert(clip.parent==&replacement && row.parent==&clip && s.recent_content==&replacement);
    detach_recents(&s);assert(!replacement.inset.top && !replacement.host && !clip.parent && !s.recent_content);
    /* Some opening layouts still report y=0 before safe-area adjustment. */
    replacement.inset.top=8;replacement.adjusted.top=20;replacement.offset.y=0;replacement.bounds.origin.y=0;
    bind_recents(&delegate,&container);assert(replacement.inset.top==56 && replacement.offset.y==-68);
    detach_recents(&s);
    return 0;
}
'''


# Reuse the scroll-view runtime, adding native flow-layout attributes. UIKit
# struct getters use the same typed host seam as the recents placement harness.
HEADERS = RECENTS.split('int main(void) {')[0]
HEADERS = HEADERS.replace('BOOL hidden;', 'BOOL hidden,pinned; I section,item; id content,native_delegate,path,element_kind,first,last; const char *encoding;')
HEADERS = HEADERS.replace('static State *current;', '''static State *current;
static struct Fake copies[32],paths[32],header_kind={.cls="NSString"},footer_kind={.cls="NSString"};
static U copy_count,path_count; static id native_attributes,native_header;
Method class_getInstanceMethod(Class c,SEL sel) { (void)sel;return c && c->encoding ? c : NULL; }
const char *method_getTypeEncoding(Method m) { return ((id)m)->encoding; }
Insets ss_test_section(id o) { return o->inset; }
''')
HEADERS = HEADERS.replace('if(!strcmp(name,"contentInset"))', 'if(!strcmp(name,"sectionInset"))return &o->inset;\n    if(!strcmp(name,"contentInset"))')
HEADERS = HEADERS.replace('else if(!strcmp(sel,"count"))', '''else if(!strcmp(sel,"stringWithUTF8String:")) { const char *text=va_arg(args,const char *);result=!strcmp(text,"UICollectionElementKindSectionHeader") ? &header_kind : &footer_kind; }
    else if(!strcmp(sel,"isEqual:"))result=(id)(uintptr_t)(o==va_arg(args,id));
    else if(!strcmp(sel,"collectionView"))result=o->content;
    else if(!strcmp(sel,"delegate"))result=o->native_delegate;
    else if(!strcmp(sel,"sectionHeadersPinToVisibleBounds"))result=(id)(uintptr_t)o->pinned;
    else if(!strcmp(sel,"representedElementKind"))result=o->element_kind;
    else if(!strcmp(sel,"indexPath"))result=o->path;
    else if(!strcmp(sel,"section"))result=(id)(uintptr_t)o->section;
    else if(!strcmp(sel,"numberOfItemsInSection:")) { assert(va_arg(args,I)>=0);result=(id)(uintptr_t)o->count; }
    else if(!strcmp(sel,"indexPathForItem:inSection:")) { assert(path_count<32);id path=&paths[path_count++];path->item=va_arg(args,I);path->section=va_arg(args,I);result=path; }
    else if(!strcmp(sel,"layoutAttributesForItemAtIndexPath:")) { id path=va_arg(args,id);assert(path->section>=0);result=path->item ? o->last : o->first; }
    else if(!strcmp(sel,"setZIndex:")) { assert(va_arg(args,I)==1024); }
    else if(!strcmp(sel,"copy") || !strcmp(sel,"mutableCopy")) { assert(copy_count<32);copies[copy_count]=*o;result=&copies[copy_count++]; }
    else if(!strcmp(sel,"autorelease"))result=o;
    else if(!strcmp(sel,"replaceObjectAtIndex:withObject:")) { U i=va_arg(args,U);assert(i<o->count);o->children[i]=va_arg(args,id); }
    else if(!strcmp(sel,"count"))''')
HEADERS += r'''
static id native_elements(id flow,SEL sel,Rect bounds) { (void)flow;(void)sel;(void)bounds;return native_attributes; }
static id native_supplementary(id flow,SEL sel,id kind_name,id path) { (void)flow;(void)sel;(void)kind_name;(void)path;return native_header; }
int main(void) {
    State s={.recent_height=48}; struct Fake delegate={.context=&s};delegate_class=&delegate;
    struct Fake section_path={.section=1};
    struct Fake first={.frame={{10,200},{40,40}}},last={.frame={{250,500},{40,40}}};
    struct Fake header={.frame={{0,348},{390,100}},.path=&section_path,.element_kind=&header_kind};
    struct Fake footer={.frame={{0,560},{390,20}},.path=&section_path,.element_kind=&footer_kind};
    struct Fake content={.host=&delegate,.bounds={{0,280},{390,300}},.count=3,.inset={56,0,0,0},.adjusted={68,0,0,0}};
    struct Fake flow={.content=&content,.pinned=YES,.first=&first,.last=&last,.inset={10,0,20,0}};
    struct Fake attrs={.count=3,.children={&first,&header,&footer}};
    native_attributes=&attrs;native_header=&header;
    original_flow_elements=(IMP)native_elements;original_flow_header=(IMP)native_supplementary;
    original_collection_layout=(IMP)native_layout;
    /* The native pin offset excludes only our 48 points, preserving UIKit's
     * remaining content/safe-area inset. Cells and footers retain identity. */
    id result=flow_elements(&flow,"layoutAttributesForElementsInRect:",content.bounds);
    assert(result!=&attrs && result->children[0]==&first && result->children[2]==&footer);
    assert(result->children[1]->frame.origin.y==300 && header.frame.origin.y==348);
    id direct=flow_header(&flow,"layoutAttributesForSupplementaryViewOfKind:atIndexPath:",&header_kind,&section_path);
    assert(direct!=&header && direct->frame.origin.y==300);
    assert(recent_header_attributes(&flow,direct)==direct); /* No accumulated shifts. */
    /* Upcoming headers stay at their natural section start; the previous
     * header stops at its native section end during the next header handoff. */
    content.bounds.origin.y=-68;header.frame.origin.y=90;
    assert(recent_header_attributes(&flow,&header)==&header);
    content.bounds.origin.y=600;header.frame.origin.y=460;
    assert(recent_header_attributes(&flow,&header)==&header);
    /* Respect Twitch's per-section inset callback only at its inspected ABI. */
    struct Fake native_delegate={.encoding="{UIEdgeInsets=dddd}40@0:8@16@24q32",.inset={30,0,40,0}};
    content.native_delegate=&native_delegate;content.bounds.origin.y=-68;header.frame.origin.y=90;
    assert(recent_header_attributes(&flow,&header)->frame.origin.y==70);
    native_delegate.encoding="unknown";
    assert(recent_header_attributes(&flow,&header)==&header);
    /* Other libraries, non-pinned layouts and empty sections remain native. */
    content.host=nil;assert(flow_elements(&flow,"layoutAttributesForElementsInRect:",content.bounds)==&attrs);
    assert(recent_header_attributes(&flow,&header)==&header);content.host=&delegate;
    flow.pinned=NO;assert(recent_header_attributes(&flow,&header)==&header);flow.pinned=YES;
    content.count=0;assert(recent_header_attributes(&flow,&header)==&header);content.count=3;
    section_path.section=0;s.recent_header_height=100;
    content.bounds.origin.y=-68;header.frame.origin.y=90;
    id frequent=recent_header_attributes(&flow,&header);
    assert(frequent!=&header && frequent->frame.origin.y==42 && header.frame.origin.y==90);
    assert(s.recent_header_start==90 && first.frame.origin.y==200);
    assert(s.recent_header_start+s.recent_header_height-s.recent_height==142); /* row follows title */
    assert(recent_header_attributes(&flow,frequent)==frequent);
    flow.pinned=NO;header.frame.origin.y=90;
    assert(recent_header_attributes(&flow,&header)->frame.origin.y==42);
    flow.pinned=YES;
    content.bounds.origin.y=280;header.frame.origin.y=348;
    assert(recent_header_attributes(&flow,&header)->frame.origin.y==300); /* native pin */
    content.bounds.origin.y=600;header.frame.origin.y=460;
    assert(recent_header_attributes(&flow,&header)==&header); /* native push-off */
    s.recent_height=0;assert(recent_header_attributes(&flow,&header)==&header);
    assert(first.frame.origin.y==200 && last.frame.origin.y==500 && footer.frame.origin.y==560);
    return 0;
}
'''


# Exercise the real strip/button builders with UIKit-owned indicator subviews.
# Image decoding/networking are stubbed; target/action and hierarchy are real.
RECENT_ACTIONS = RECENTS.split('int main(void) {')[0]
RECENT_ACTIONS = RECENT_ACTIONS.replace('BOOL hidden;', 'BOOL hidden; id metadata; const char *text,*action; unsigned targets;')
RECENT_ACTIONS = RECENT_ACTIONS.replace('classes[8]', 'classes[16]').replace('class_count<8', 'class_count<16')
RECENT_ACTIONS = RECENT_ACTIONS.replace('static State *current;', '''static State *current;
static struct Fake objects[96];static U object_count;
static id fresh(const char *name) { assert(object_count<96);id result=&objects[object_count++];result->cls=name;return result; }
''')
RECENT_ACTIONS = RECENT_ACTIONS.replace('return o && key==&recent_host_key ? o->host : nil;',
    'return !o ? nil : key==&recent_host_key ? o->host : key==&button_key ? o->metadata : nil;')
RECENT_ACTIONS = RECENT_ACTIONS.replace('assert(key==&recent_host_key && policy==1);o->host=value;',
    'assert(policy==1);if(key==&button_key)o->metadata=value;else { assert(key==&recent_host_key);o->host=value; }')
RECENT_ACTIONS = RECENT_ACTIONS.replace('else if(!strcmp(sel,"count"))', '''else if(!strcmp(sel,"stringWithUTF8String:")) { result=fresh("NSString");result->text=va_arg(args,const char *); }
    else if(!strcmp(sel,"objectForKey:")) { id key=va_arg(args,id);result=!strcmp(key->text,"name") ? o->tint : nil; }
    else if(!strcmp(sel,"alloc"))result=fresh(o->cls);
    else if(!strcmp(sel,"initWithFrame:")) { o->frame=va_arg(args,Rect);result=o; }
    else if(!strcmp(sel,"copy")) { result=fresh(o->cls);*result=*o; }
    else if(!strcmp(sel,"systemFontOfSize:") || !strcmp(sel,"secondaryLabelColor"))result=o;
    else if(!strcmp(sel,"setContentMode:") || !strcmp(sel,"setTextAlignment:")) (void)va_arg(args,I);
    else if(!strcmp(sel,"setUserInteractionEnabled:"))assert(!va_arg(args,int));
    else if(!strcmp(sel,"setFont:") || !strcmp(sel,"setTextColor:") || !strcmp(sel,"setText:") || !strcmp(sel,"setAccessibilityLabel:"))assert(va_arg(args,id));
    else if(!strcmp(sel,"setImage:"))assert(!va_arg(args,id));
    else if(!strcmp(sel,"addTarget:action:forControlEvents:")) {
        assert(!strcmp(o->cls,"UIButton"));assert(va_arg(args,id));o->action=va_arg(args,SEL);
        assert(va_arg(args,U)==(1UL<<6));o->targets++;
    } else if(!strcmp(sel,"removeTarget:action:forControlEvents:"))assert(!"UIKit indicator cannot receive target APIs");
    else if(!strcmp(sel,"setContentSize:")) { Size size=va_arg(args,Size);assert(size.width==128 && size.height==48); }
    else if(!strcmp(sel,"count"))''')
RECENT_ACTIONS = RECENT_ACTIONS.replace('else if(!strcmp(sel,"addSubview:"))va_arg(args,id)->parent=o;',
    'else if(!strcmp(sel,"addSubview:")) { id child=va_arg(args,id);assert(o->count<4);o->children[o->count++]=child;child->parent=o; }')
RECENT_ACTIONS = RECENT_ACTIONS.replace('else if(!strcmp(sel,"removeFromSuperview"))o->parent=nil;', '''else if(!strcmp(sel,"removeFromSuperview")) {
        id parent=o->parent;assert(parent);U i=0;while(i<parent->count && parent->children[i]!=o)i++;
        assert(i<parent->count);memmove(parent->children+i,parent->children+i+1,(parent->count-i-1)*sizeof(id));parent->count--;o->parent=nil;
    }''')
RECENT_ACTIONS += r'''
int main(void) {
    struct Fake horizontal={.cls="_UIScrollViewScrollIndicator"},vertical={.cls="_UIScrollViewScrollIndicator"};
    struct Fake name_a={.cls="NSString",.text="First"},name_b={.cls="NSString",.text="Second"};
    struct Fake metadata_a={.cls="NSDictionary",.tint=&name_a},metadata_b={.cls="NSDictionary",.tint=&name_b};
    struct Fake items={.count=2,.children={&metadata_a,&metadata_b}},delegate={.cls="SSComposerDelegate"};
    struct Fake row={.cls="UIScrollView",.count=2,.children={&horizontal,&vertical}};
    horizontal.parent=&row;vertical.parent=&row;original_collection_layout=(IMP)native_layout;
    fill_strip(&row,&delegate,&items,"ssRecent:");
    assert(row.count==4 && row.children[0]==&horizontal && row.children[1]==&vertical);
    id first=row.children[2],second=row.children[3];
    assert(first->metadata==&metadata_a && second->metadata==&metadata_b);
    assert(first->targets==1 && second->targets==1 && !strcmp(first->action,"ssRecent:") && !strcmp(second->action,"ssRecent:"));
    /* Selecting Second moves it to the front. The subsequent history refresh
     * replaces only owned buttons while both UIKit indicators remain alive. */
    items.children[0]=&metadata_b;items.children[1]=&metadata_a;
    fill_strip(&row,&delegate,&items,"ssRecent:");
    assert(row.count==4 && !first->parent && !second->parent);
    assert(row.children[2]->metadata==&metadata_b && row.children[2]->targets==1);
    assert(!strcmp(row.children[2]->action,"ssRecent:") && !strcmp(row.children[3]->action,"ssRecent:"));
    assert(horizontal.parent==&row && vertical.parent==&row && !horizontal.targets && !vertical.targets);
    /* Suggestions retain their distinct completion-replacement action. */
    fill_strip(&row,&delegate,&items,"ssPick:");
    assert(!strcmp(row.children[2]->action,"ssPick:") && row.children[2]->targets==1);
    assert(row.children[0]==&horizontal && row.children[1]==&vertical && row.count==4);
    return 0;
}
'''



def recent_geometry_source():
    source = (ROOT / "src" / "SSComposer.c").read_text()
    source = source.replace('static Rect rect(id o,const char *s) { return ((Rect (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }',
        'extern void *ss_test_field(id,const char *);\nextern Insets ss_test_section(id);\n'
        'extern void ss_test_frame(id,Rect);\nextern void ss_test_inset(id,Insets);\n'
        'extern void ss_test_offset(id,Point);\nextern void ss_test_offset_animated(id,Point,BOOL);\n'
        'static Rect rect(id o,const char *s) { return *(Rect *)ss_test_field(o,s); }')
    source = source.replace('static void frame(id o,Rect r) { ((void (*)(id,SEL,Rect))objc_msgSend)(o,sel_registerName("setFrame:"),r); }',
        'static void frame(id o,Rect r) { ss_test_frame(o,r); }')
    for obj, name, typ in (("flow", "sectionInset", "Insets"), ("content", "contentInset", "Insets"),
                           ("content", "adjustedContentInset", "Insets"), ("content", "contentOffset", "Point"),
                           ("s->grid", "contentOffset", "Point"), ("flow", "collectionViewContentSize", "Size")):
        source = source.replace(f'(({typ} (*)(id,SEL))objc_msgSend)({obj},sel_registerName("{name}"))',
            f'*({typ} *)ss_test_field({obj},"{name}")')
    source = source.replace('((Insets (*)(id,SEL,id,id,I))objc_msgSend)(native_delegate,inset_selector,content,flow,section)',
        'ss_test_section(native_delegate)')
    source = source.replace('((void (*)(id,SEL,Insets))objc_msgSend)(content,sel_registerName("setContentInset:"),inset)',
        'ss_test_inset(content,inset)')
    source = source.replace('((void (*)(id,SEL,Point))objc_msgSend)(content,sel_registerName("setContentOffset:"),offset)',
        'ss_test_offset(content,offset)')
    source = source.replace('((void (*)(id,SEL,Point))objc_msgSend)(s->grid,sel_registerName("setContentOffset:"),position)',
        'ss_test_offset(s->grid,position)')
    source = source.replace('((void (*)(id,SEL,Point,BOOL))objc_msgSend)(content,sel_registerName("setContentOffset:animated:"),offset,NO)',
        'ss_test_offset_animated(content,offset,NO)')
    source = source.replace('((void (*)(id,SEL,Point,BOOL))objc_msgSend)(content,sel_registerName("setContentOffset:animated:"),(Point){0,-inset.top},NO)',
        'ss_test_offset_animated(content,(Point){0,-inset.top},NO)')
    return source

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

    def test_button_drags_can_scroll_the_suggestion_strip(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        self.compile_run(SCROLL, [zig, "cc", "-fblocks"], runtime=True)

    def test_native_library_recents_scroll_by_default_and_preserve_section_navigation(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        # Only the runtime boundary is mocked; placement and scrolling use
        # the production functions, including synchronous UIKit reentry.
        source = recent_geometry_source()
        self.compile_run(RECENTS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)

    def test_native_sticky_headers_keep_their_pin_and_handoff_positions(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        source = recent_geometry_source()
        self.compile_run(HEADERS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)

    def test_recent_history_refresh_never_wires_uikit_scroll_indicators(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production composer harness")
        source = (ROOT / "src" / "SSComposer.c").read_text()
        start = source.index('static void set_thumbnail(')
        end = source.index('\n}', start) + 2
        source = source[:start] + 'static void set_thumbnail(id image,id metadata) { (void)metadata;(void)thumbnail_url_key;(void)thumbnail_record_key;v1(image,"setImage:",nil); }' + source[end:]
        self.compile_run(RECENT_ACTIONS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)

    def compile_run(self, content, compiler, runtime=False):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            if runtime:
                (directory / "objc").mkdir()
                for h in ("objc.h", "runtime.h", "message.h"):
                    (directory / "objc" / h).write_text(RUNTIME + '\nsize_t class_getInstanceSize(Class);\nBOOL class_addIvar(Class,const char *,size_t,uint8_t,const char *);\nconst char *sel_getName(SEL);\n')
            harness=directory / "composer.c"; binary=directory / "composer"
            if runtime:
                content += '\nvoid *_NSConcreteGlobalBlock[32];\n'
            harness.write_text(content)
            compiled = subprocess.run(compiler + ["-Wall", "-Wextra", "-Werror", "-ffunction-sections", "-fdata-sections",
                "-Wl,--gc-sections", *(["-Wno-cast-function-type-mismatch"] if runtime else []), "-I", str(directory), "-I", str(ROOT / "src"), str(harness), "-o", str(binary)],
                capture_output=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr.decode(errors="replace"))
            result = subprocess.run([binary], capture_output=True, env={**os.environ,"ASAN_OPTIONS":"detect_leaks=0"})
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
