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
    return 0;
}
'''
EDITOR = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake { const char *cls; U length; uint16_t units[256]; id codes[256]; unsigned native[256]; };
static struct Fake cls={"NSString",0,{0},{0},{0}}, editor={"UITextView",0,{0},{0},{0}};
static struct Fake source={"NSAttributedString",0,{0},{0},{0}}, strings[128];
static size_t used;
static id ascii(const char *s) { id o=&strings[used++]; assert(used<128); o->cls="NSString"; o->length=strlen(s); for(U i=0;i<o->length;i++)o->units[i]=(unsigned char)s[i]; return o; }
static BOOL matches(id o,const char *s) { if(!o || o->length!=strlen(s))return NO; for(U i=0;i<o->length;i++)if(o->units[i]!=(unsigned char)s[i])return NO;return YES; }
Class objc_getClass(const char *name) { assert(!strcmp(name,"NSString")); return &cls; }
SEL sel_registerName(const char *s) { return s; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil; va_list args; va_start(args,sel); id result=nil;
    if(!strcmp(sel,"attributedText"))result=&source;
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
    free(plain); return 0;
}
'''

CONTROLS = EDITOR[:EDITOR.index("int main(void)")].replace(
    'assert(!strcmp(name,"NSString")); return &cls;',
    'return !strcmp(name,"NSString") ? &cls : nil;')
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
void objc_release(id o) { (void)o; }
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
