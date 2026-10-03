"""Run production preview/deletion code against a deferred image/UIKit boundary."""
import os
import shutil
import unittest
import test_composer as composer
from test_composer_library import replace_body


HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
struct Fake;
static void ss_test_request(struct Fake *);
#include "SSComposer.c"
struct Fake {
    const char *cls;
    U length;
    uint16_t units[256];
    id codes[256],attachments[256];
    id value,host,metadata,bitmap,name,url,identifier;
    State *context;
    Range selected;
    Rect bounds;
    BOOL marked,responder;
};
static struct Fake objects[8192],classes[32],editor,owner,delegate,footer,source,typing,meta,cache,bitmap;
static U used,class_count;
static unsigned requests,storage_edits,selection_sets,layouts,displays,notified,validated,fallbacks;
static BOOL available,accept=YES,emit_change=YES;
static Range validated_range;
static id last_plain;
static State context;
static id create(const char *cls) { assert(used<8192);id o=&objects[used++];o->cls=cls;return o; }
static id ascii(const char *s) { id o=create("NSString");o->length=strlen(s);for(U i=0;i<o->length;i++)o->units[i]=(unsigned char)s[i];return o; }
static BOOL matches(id o,const char *s) { if(!o || o->length!=strlen(s))return NO;for(U i=0;i<o->length;i++)if(o->units[i]!=(unsigned char)s[i])return NO;return YES; }
Class objc_getClass(const char *name) {
    for(U i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name))return &classes[i];
    assert(class_count<32);classes[class_count].cls=name;return &classes[class_count++];
}
Class object_getClass(id o) { return o; }
SEL sel_registerName(const char *s) { return s; }
const char *sel_getName(SEL s) { return s; }
Ivar class_getInstanceVariable(Class c,const char *name) {
    (void)c;
    if(!strcmp(name,"_state"))return (Ivar)(uintptr_t)offsetof(struct Fake,context);
    if(!strcmp(name,"textEntryView"))return (Ivar)(uintptr_t)offsetof(struct Fake,value);
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return (ptrdiff_t)(uintptr_t)iv; }
size_t class_getInstanceSize(Class c) { (void)c;return sizeof(struct Fake); }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_loadWeakRetained(id *p) { return *p; }
id objc_getAssociatedObject(id o,const void *k) {
    if(!o)return nil;
    return k==&attachment_metadata_key ? o->metadata : o->host;
}
void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t policy) {
    assert(policy==1 && k==&attachment_metadata_key);o->metadata=v;
}
static void ss_test_request(id metadata) { assert(metadata==&meta);requests++; }
static Range ss_test_selection(id o) { return o->selected; }
static void ss_test_set_bounds(id o,Rect r) { o->bounds=r; }
static id duplicate(id o,const char *cls) { id result=create(cls);memcpy(result,o,sizeof(*o));result->cls=cls;return result; }
static void replace(id o,Range r,id v,BOOL attributed) {
    assert(r.location+r.length<=o->length && o->length-r.length+v->length<256);
    U tail=o->length-r.location-r.length;
    memmove(o->units+r.location+v->length,o->units+r.location+r.length,tail*sizeof(uint16_t));
    memmove(o->codes+r.location+v->length,o->codes+r.location+r.length,tail*sizeof(id));
    memmove(o->attachments+r.location+v->length,o->attachments+r.location+r.length,tail*sizeof(id));
    for(U i=0;i<v->length;i++) {
        o->units[r.location+i]=v->units[i];
        o->codes[r.location+i]=attributed ? v->codes[i] : nil;
        o->attachments[r.location+i]=attributed ? v->attachments[i] : nil;
    }
    o->length=o->length-r.length+v->length;
}
static BOOL same(id a,id b,BOOL attributed) {
    if(!a || !b || a->length!=b->length)return NO;
    for(U i=0;i<a->length;i++)if(a->units[i]!=b->units[i] || (attributed && (a->codes[i]!=b->codes[i] || a->attachments[i]!=b->attachments[i])))return NO;
    return YES;
}
static void keyboard_delete(void) {
    Range r=editor.selected;
    if(!r.length && r.location) {
        r.location--;r.length=1;
        if(source.units[r.location]>=0xdc00 && source.units[r.location]<=0xdfff && r.location && source.units[r.location-1]>=0xd800 && source.units[r.location-1]<=0xdbff){r.location--;r.length++;}
    }
    if(!r.length)return;
    id empty=ascii("");
    if(!should_change(&owner,"textView:shouldChangeTextInRange:replacementText:",&editor,r,empty))return;
    replace(&source,r,empty,NO);editor.selected=(Range){r.location,0};
    if(emit_change)did_change(&owner,"textViewDidChange:",&editor);
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"new") || !strcmp(sel,"alloc"))result=create(o->cls);
    else if(!strcmp(sel,"copy") || !strcmp(sel,"mutableCopy"))result=duplicate(o,o->cls);
    else if(!strcmp(sel,"initWithAttributedString:")){id v=va_arg(args,id);const char *cls=o->cls;memcpy(o,v,sizeof(*o));o->cls=cls;result=o;}
    else if(!strcmp(sel,"attributedText"))result=&source;
    else if(!strcmp(sel,"text"))result=editor_text(o,sel);
    else if(!strcmp(sel,"textStorage"))result=editor_storage(o,sel);
    else if(!strcmp(sel,"string"))result=o;
    else if(!strcmp(sel,"stringWithUTF8String:"))result=ascii(va_arg(args,const char *));
    else if(!strcmp(sel,"length"))result=(id)(uintptr_t)o->length;
    else if(!strcmp(sel,"isKindOfClass:")){Class c=va_arg(args,Class);result=(id)(uintptr_t)!strcmp(o->cls,c->cls);}
    else if(!strcmp(sel,"isMainThread"))result=(id)(uintptr_t)YES;
    else if(!strcmp(sel,"isFirstResponder"))result=(id)(uintptr_t)o->responder;
    else if(!strcmp(sel,"markedTextRange"))result=o->marked ? &typing : nil;
    else if(!strcmp(sel,"respondsToSelector:")){(void)va_arg(args,SEL);result=(id)(uintptr_t)YES;}
    else if(!strcmp(sel,"characterAtIndex:")){U i=va_arg(args,U);assert(i<o->length);result=(id)(uintptr_t)o->units[i];}
    else if(!strcmp(sel,"getCharacters:range:")){uint16_t *dst=va_arg(args,uint16_t *);Range r=va_arg(args,Range);assert(r.location+r.length<=o->length);memcpy(dst,o->units+r.location,r.length*2);}
    else if(!strcmp(sel,"substringWithRange:") || !strcmp(sel,"attributedSubstringFromRange:")){
        Range r=va_arg(args,Range);assert(r.location+r.length<=o->length);result=create(!strcmp(sel,"substringWithRange:") ? "NSString" : "NSAttributedString");result->length=r.length;
        memcpy(result->units,o->units+r.location,r.length*2);memcpy(result->codes,o->codes+r.location,r.length*sizeof(id));memcpy(result->attachments,o->attachments+r.location,r.length*sizeof(id));
    }
    else if(!strcmp(sel,"attributedStringWithAttachment:")){id a=va_arg(args,id);result=create("NSAttributedString");result->length=1;result->units[0]=0xfffc;result->attachments[0]=a;}
    else if(!strcmp(sel,"attribute:atIndex:effectiveRange:")){
        id k=va_arg(args,id);U i=va_arg(args,U);(void)va_arg(args,Range *);assert(i<o->length);
        if(matches(k,ATTACHMENT_KEY))result=o->codes[i];else {assert(matches(k,"NSAttachment"));result=o->attachments[i];}
    }
    else if(!strcmp(sel,"replaceCharactersInRange:withString:") || !strcmp(sel,"replaceCharactersInRange:withAttributedString:")){
        Range r=va_arg(args,Range);id v=va_arg(args,id);replace(o,r,v,!strcmp(sel,"replaceCharactersInRange:withAttributedString:"));
    }
    else if(!strcmp(sel,"removeAttribute:range:")){
        id k=va_arg(args,id);Range r=va_arg(args,Range);for(U i=r.location;i<r.location+r.length;i++){if(matches(k,ATTACHMENT_KEY))o->codes[i]=nil;else {assert(matches(k,"NSAttachment"));o->attachments[i]=nil;}}
    }
    else if(!strcmp(sel,"addAttribute:value:range:")){
        id k=va_arg(args,id),v=va_arg(args,id);Range r=va_arg(args,Range);assert(r.location+r.length<=o->length);
        if(matches(k,ATTACHMENT_KEY))for(U i=r.location;i<r.location+r.length;i++)o->codes[i]=v;
        else assert(matches(k,"NSFont") || matches(k,"NSColor"));
    }
    else if(!strcmp(sel,"isEqual:") || !strcmp(sel,"isEqualToAttributedString:"))result=(id)(uintptr_t)same(o,va_arg(args,id),!strcmp(sel,"isEqualToAttributedString:"));
    else if(!strcmp(sel,"objectForKey:")){
        id k=va_arg(args,id);
        if(o==&meta){if(matches(k,"name"))result=o->name;else if(matches(k,"id"))result=o->identifier;else if(matches(k,"url"))result=o->url;}
        else if(o==&cache && matches(k,"image"))result=&bitmap;
        else if(o==images && available)result=&cache;
    }
    else if(!strcmp(sel,"image"))result=o->bitmap;
    else if(!strcmp(sel,"setImage:"))o->bitmap=va_arg(args,id);
    else if(!strcmp(sel,"layoutManager"))result=&typing;
    else if(!strcmp(sel,"invalidateLayoutForCharacterRange:actualCharacterRange:")){Range r=va_arg(args,Range);assert(r.location==0 && r.length==source.length);assert(!va_arg(args,Range *));layouts++;}
    else if(!strcmp(sel,"invalidateDisplayForCharacterRange:")){Range r=va_arg(args,Range);assert(r.location==0 && r.length==source.length);displays++;}
    else if(!strcmp(sel,"typingAttributes") || !strcmp(sel,"labelColor"))result=&typing;
    else if(!strcmp(sel,"systemFontOfSize:")){assert(va_arg(args,double)==17.0);result=&typing;}
    else if(!strcmp(sel,"setTypingAttributes:")){(void)va_arg(args,id);}
    else if(!strcmp(sel,"setObject:forKey:")){(void)va_arg(args,id);(void)va_arg(args,id);}
    else if(!strcmp(sel,"beginEditing"))storage_edits++;
    else if(!strcmp(sel,"endEditing")){}
    else if(!strcmp(sel,"setSelectedRange:")){o->selected=va_arg(args,Range);selection_sets++;}
    else if(!strcmp(sel,"cancelPreviousPerformRequestsWithTarget:selector:object:")){}
    else if(!strcmp(sel,"performSelector:withObject:afterDelay:")){SEL action=va_arg(args,SEL);assert(!strcmp(action,"ssPreview:"));assert(!va_arg(args,id));assert(va_arg(args,double)==0.0);}
    else if(!strcmp(sel,"deleteBackward")){assert(o==&editor);keyboard_delete();}
    else {fprintf(stderr,"unexpected selector: %s\n",sel);assert(0);}
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id tas_emotes_named_copy(id room,id name) { (void)room;return matches(name,"Wide") ? &meta : nil; }
static id raw_text(id o,SEL sel) { (void)o;(void)sel;return &source; }
static BOOL validate(id o,SEL sel,id input,Range r,id value) {
    (void)o;(void)sel;(void)value;assert(input==&editor);validated_range=r;validated++;
    /* The native validation sees expanded text/storage, while live UIKit
     * still owns the displayed range and selection. */
    assert(same(m0(input,"text"),m0(input,"textStorage"),NO));return accept;
}
static void notify(id o,SEL sel,id input) { (void)o;(void)sel;assert(input==&editor);last_plain=m0(m0(input,"text"),"copy");notified++; }
static void fallback(id o,SEL sel) { (void)o;(void)sel;fallbacks++; }
static void reset(const char *text,U caret,BOOL focused) {
    memset(&source,0,sizeof(source));id v=ascii(text);replace(&source,(Range){0,0},v,NO);source.cls="NSTextStorage";
    editor.selected=(Range){caret,0};editor.responder=focused;editor.marked=NO;
    context.preview_scheduled=NO;available=NO;accept=YES;emit_change=YES;
}
static void menu(void) { footer_action(&footer,"backspaceButtonPressed"); }
static void ready(void) { preview_ready(&delegate,"ssPreview:",nil); }
int main(void) {
    (void)request_native_catalog;(void)unified_matches;
    editor.cls="UITextView";owner.value=&editor;owner.host=&delegate;delegate.context=&context;footer.host=&delegate;context.owner=&owner;
    delegate_class=objc_getClass("SSComposerDelegate");attachment_class=objc_getClass("SSComposerAttachment");images=create("NSCache");
    meta.name=ascii("Wide");meta.url=ascii("https://example/emote");meta.identifier=ascii("7tv:wide");
    original_text=(IMP)raw_text;original_storage=(IMP)raw_text;original_should_change=(IMP)validate;original_change=(IMP)notify;original_footer_actions[4]=(IMP)fallback;
    /* Exact code at the caret, no delimiter and no image: reserve width on
     * the next run-loop turn, never in the active UIKit edit callback. */
    reset("Wide",4,YES);schedule_preview(&delegate);render(&delegate);assert(source.length==4 && !storage_edits);
    ready();assert(source.length==1 && source.units[0]==0xfffc && editor.selected.location==1 && requests==1);
    id placeholder=source.attachments[0];assert(!placeholder->bitmap && matches(source.codes[0],"Wide"));
    assert(placeholder->bounds.size.width==66 && placeholder->bounds.size.height==22);
    unsigned writes=storage_edits,carets=selection_sets;
    /* A later bitmap hydrates the same character, leaving storage and caret
     * untouched; cache eviction does not cause another download. */
    available=YES;image_changed(&delegate,"ssImages:",nil);ready();
    assert(source.attachments[0]==placeholder && placeholder->bitmap==&bitmap && storage_edits==writes && selection_sets==carets && layouts==1 && displays==1);
    available=NO;render(&delegate);assert(requests==1 && source.attachments[0]==placeholder);
    /* Typing past an exact match turns the expanded, no-longer-exact word
     * back into literal text. Partial words stay editable. */
    replace(&source,(Range){1,0},ascii("X"),NO);editor.selected=(Range){2,0};render(&delegate);
    assert(matches(&source,"WideX") && editor.selected.location==5);menu();assert(matches(&source,"Wide") && validated_range.length==1);ready();
    /* Software keyboard and menu delete a blank or loaded attachment as a
     * full code; late image notifications cannot recreate a deleted word. */
    keyboard_delete();assert(source.length==0 && validated_range.location==0 && validated_range.length==4 && last_plain->length==0);ready();
    available=YES;image_changed(&delegate,"ssImages:",nil);ready();assert(!source.length);
    reset("Wide ",5,NO);unsigned notifications=notified;menu();assert(source.length==1 && source.units[0]==0xfffc && matches(last_plain,"Wide") && notified==notifications+1);
    menu();assert(!source.length && validated_range.length==4 && !fallbacks && notified==notifications+2);
    /* Unfocused editors that omit didChange get exactly one native update. */
    reset("Wide",4,NO);emit_change=NO;notifications=notified;menu();assert(!source.length && notified==notifications+1 && validated_range.length==4);
    /* UTF-16 emoji offsets and ordinary composed-character deletion survive. */
    reset("",0,NO);uint16_t units[]={0xd83d,0xde00,' ','W','i','d','e'};source.length=7;memcpy(source.units,units,sizeof(units));editor.selected=(Range){7,0};
    menu();assert(source.length==3 && validated_range.location==3 && validated_range.length==4);menu();assert(source.length==2);menu();assert(!source.length && validated_range.length==2);
    /* Selected ranges span whole codes; native validation veto still wins. */
    reset("Wide Wide",9,NO);render(&delegate);assert(source.length==3);editor.selected=(Range){0,3};menu();assert(!source.length && validated_range.length==9);
    reset("Wide",4,YES);render(&delegate);accept=NO;notifications=notified;menu();assert(source.length==1 && editor.selected.location==1 && notified==notifications);ready();
    /* Interior carets/overlapping selections and marked IME text remain
     * literal. The existing native footer handles marked composition. */
    reset("Wide",2,YES);render(&delegate);assert(matches(&source,"Wide"));editor.selected=(Range){1,2};render(&delegate);assert(matches(&source,"Wide"));
    reset("Wide",4,YES);editor.marked=YES;render(&delegate);menu();assert(matches(&source,"Wide") && fallbacks==1);
    assert(validated>=10 && !native_read && !context.busy);return 0;
}
'''


class PreviewTests(unittest.TestCase):
    def test_immediate_placeholders_image_hydration_and_both_backspace_paths(self):
        zig = os.environ.get("ZIG", shutil.which("zig"))
        if not zig:
            self.skipTest("Zig unavailable")
        source = (composer.ROOT / "src/SSComposer.c").read_text()
        source = source.replace("static Range selection(id editor) {", "static Range ss_test_selection(id);\nstatic Range selection(id editor) {")
        source = replace_body(source, "static Range selection(id editor)", "return ss_test_selection(editor);")
        for signature, body in (
            ("static void refresh(id delegate)", "(void)delegate;"),
            ("static void start_tick(id delegate)", "(void)delegate;"),
            ("static void restore_native(State *s)", "(void)s;"),
            ("static void scroll_to_recents(State *s)", "(void)s;"),
            ("static id delegate_for(id owner)", "return objc_getAssociatedObject(owner,&state_key);"),
            ("static void image_request(id metadata)", "ss_test_request(metadata);"),
        ):
            source = replace_body(source, signature, body)
        # Typed geometry returns use arm64 objc_msgSend ABI in production.
        # Host tests replace only that UIKit boundary, retaining real layout math.
        source = source.replace('aspect=((double (*)(id,SEL))objc_msgSend)(key(metadata,"aspect"),sel_registerName("doubleValue"))', 'aspect=3.0')
        source = source.replace('Size z=((Size (*)(id,SEL))objc_msgSend)(m0(attachment,"image"),sel_registerName("size"));', 'Size z={22,22};')
        source = source.replace('((void (*)(id,SEL,Rect))objc_msgSend)(attachment,sel_registerName("setBounds:"),(Rect){{0,-4},{width,height}});', 'ss_test_set_bounds(attachment,(Rect){{0,-4},{width,height}});')
        source = source.replace("static void render(id delegate) {", "static void ss_test_set_bounds(id,Rect);\nstatic void render(id delegate) {")
        composer.ComposerTests().compile_run(HARNESS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)
