from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Small host runtime exercising the production resolver against Twitch's actual
# dictionary shape: NSNumber location -> TWMessageEmoteToken -> NSString ID.
RUNTIME = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
typedef struct Fake *id;
typedef struct Fake *Class;
typedef const char *SEL;
typedef void (*IMP)(void);
typedef void *Ivar;
typedef void *Method;
typedef signed char BOOL;
#define YES 1
#define NO 0
#define nil ((id)0)
Class objc_getClass(const char *);
Class object_getClass(id);
SEL sel_registerName(const char *);
Ivar class_getInstanceVariable(Class,const char *);
ptrdiff_t ivar_getOffset(Ivar);
Method class_getInstanceMethod(Class,SEL);
unsigned method_getNumberOfArguments(Method);
IMP method_getImplementation(Method);
IMP class_getMethodImplementation(Class,SEL);
const char *method_getTypeEncoding(Method);
BOOL class_addMethod(Class,SEL,IMP,const char *);
IMP method_setImplementation(Method,IMP);
Class objc_allocateClassPair(Class,const char *,size_t);
void objc_registerClassPair(Class);
extern id (*objc_msgSend)(id,SEL,...);
'''
HARNESS = r'''
#include <stdarg.h>
#include <assert.h>
#include "TASEmoteUI.c"
struct Fake { const char *class_name, *value; id inner; };
struct LayerFake { struct Fake base; Rect content_frame; id image_data; id requester; };
static struct Fake classes[] = {{"NSString",0,0},{"NSNumber",0,0},
    {"_TtC6Twitch20ImageAttachmentLayer",0,0},{"_TtC6Twitch22MessageStringImageData",0,0}};
static struct Fake location = {"NSNumber","12",0};
Class objc_getClass(const char *name) {
    for (size_t i=0;i<sizeof(classes)/sizeof(classes[0]);i++) if (!strcmp(name,classes[i].class_name)) return &classes[i];
    return nil;
}
SEL sel_registerName(const char *name) { return name; }
static id dispatch(id o,SEL sel,...) {
    if (!o) return nil;
    va_list args; va_start(args,sel); id result = nil;
    if (!strcmp(sel,"isKindOfClass:")) {
        Class cls = va_arg(args,Class);
        result = (id)(uintptr_t)(cls && !strcmp(o->class_name,cls->class_name));
    } else if (!strcmp(sel,"respondsToSelector:")) {
        SEL probe = va_arg(args,SEL);
        result = (id)(uintptr_t)((!strcmp(probe,"emoteId") && !strcmp(o->class_name,"TWMessageEmoteToken")) ||
                                (!strcmp(probe,"emoteLocationsMap") && !strcmp(o->class_name,"MessageString")) ||
                                (!strcmp(probe,"layoutManager") && !strcmp(o->class_name,"NSTextContainer")) ||
                                (!strcmp(probe,"staticURL") && !strcmp(o->class_name,"_TtC6Twitch22MessageStringImageData")) ||
                                ((!strcmp(probe,"host") || !strcmp(probe,"path")) && !strcmp(o->class_name,"NSURL")));
    } else if (!strcmp(sel,"emoteId") || !strcmp(sel,"emoteLocationsMap") || !strcmp(sel,"layoutManager") || !strcmp(sel,"staticURL") || !strcmp(sel,"host")) result = o->inner;
    else if (!strcmp(sel,"path")) { static struct Fake path = {"NSString",0,0}; path.value = o->value; result = &path; }
    else if (!strcmp(sel,"isEqualToString:")) { id other = va_arg(args,id); result = (id)(uintptr_t)(other && !strcmp(o->value,other->value)); }
    else if (!strcmp(sel,"stringWithUTF8String:")) { static struct Fake text = {"NSString",0,0}; text.value = va_arg(args,const char *); result = &text; }
    else if (!strcmp(sel,"longLongValue")) result = (id)(uintptr_t)strtoll(o->value,NULL,10);
    else if (!strcmp(sel,"description")) result = o;
    else if (!strcmp(sel,"UTF8String")) result = (id)o->value;
    else if (!strcmp(sel,"numberWithInteger:")) { (void)va_arg(args,long); result = &location; }
    else if (!strcmp(sel,"objectForKey:")) { (void)va_arg(args,id); result = o->inner; }
    else assert(!"unexpected selector in resolver test");
    va_end(args); return result;
}
id (*objc_msgSend)(id,SEL,...) = dispatch;
Class object_getClass(id o) { return o; }
static ptrdiff_t content_offset = offsetof(struct LayerFake,content_frame);
static ptrdiff_t requester_offset = offsetof(struct LayerFake,requester), wrong_offset;
Ivar class_getInstanceVariable(Class cls,const char *name) {
    if (strcmp(cls->class_name,"_TtC6Twitch20ImageAttachmentLayer")) return NULL;
    if (!strcmp(name,"content")) return &content_offset;
    if (!strcmp(name,"networkImageRequester")) {
        if (cls->value) { wrong_offset = requester_offset + 8; return &wrong_offset; }
        return &requester_offset;
    }
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar ivar) { return *(ptrdiff_t *)ivar; }
id objc_getAssociatedObject(id o,const void *key_value) { (void)key_value; return o ? o->inner : nil; }
double tas_emotes_aspect(uint64_t number) { return number == 9000000001ULL ? 4 : number == 9000000002ULL || number == 9000000003ULL ? 1 : number == 9000000004ULL ? 3 : 0; }
static Size native_size(id self,SEL sel,NSInteger index) {
    (void)self; (void)sel; (void)index; return (Size){28,28};
}
static Rect native_attachment(id self,SEL sel,id container,Rect fragment,Point position,NSUInteger index) {
    (void)self; (void)sel; (void)container; (void)fragment; (void)position; (void)index;
    return (Rect){{0,-7},{28,28}};
}
static Rect painted;
static void native_frame(id self,SEL sel,Rect frame) { (void)self; (void)sel; painted = frame; }
int main(void) {
    struct Fake provider = {"NSString","9000000001",nil};
    struct Fake native = {"NSString","25",nil};
    struct Fake malformed = {"NSString","9000000001junk",nil};
    struct Fake token = {"TWMessageEmoteToken",0,&provider};
    struct Fake map = {"NSDictionary",0,&token};
    struct Fake message = {"MessageString",0,&map};
    assert(synthetic_id(&provider) == 9000000001ULL);
    assert(synthetic_id(&token) == 9000000001ULL);
    assert(!synthetic_id(nil) && !synthetic_id(&malformed));
    assert(message_id_at(&message,12) == 9000000001ULL);
    g_size = (IMP)native_size;
    Size size = message_size(&message,"sizeOfImageAttachmentAtCharacterIndex:",12);
    assert(size.width == 112 && size.height == 28);
    struct Fake manager = {"NSLayoutManager",0,&message};
    struct Fake container = {"NSTextContainer",0,&manager};
    Rect rect = textkit_bounds_with((IMP)native_attachment,nil,"attachmentBounds",&container,(Rect){0},(Point){0},12);
    assert(rect.size.width == 112 && rect.size.height == 28 && rect.origin.y == -7);
    manager.inner = nil;
    rect = textkit_bounds_with((IMP)native_attachment,nil,"attachmentBounds",&container,(Rect){0},(Point){0},12);
    assert(rect.size.width == 28 && rect.size.height == 28);
    token.inner = &native;
    assert(!synthetic_id(&token));
    size = message_size(&message,"sizeOfImageAttachmentAtCharacterIndex:",12);
    assert(size.width == 28 && size.height == 28);
    token.inner = nil; assert(!synthetic_id(&token));
    struct Fake numeric_sender = {"NSNumber","123456",nil};
    struct Fake text_sender = {"NSString","123456",nil};
    struct Fake negative_sender = {"NSNumber","-1",nil};
    struct Fake large_sender = {"NSNumber","4294967296",nil};
    assert(sender_id(&numeric_sender) == 123456 && sender_id(&text_sender) == 123456);
    assert(!sender_id(nil) && !sender_id(&negative_sender) && !sender_id(&large_sender));
    struct Fake host = {"NSString","static-cdn.jtvnw.net",nil};
    struct Fake url = {"NSURL","/emoticons/v2/9000000001/default/dark/1.0",&host};
    struct Fake data = {"_TtC6Twitch22MessageStringImageData",0,&url};
    struct LayerFake layer = {{"_TtC6Twitch20ImageAttachmentLayer",0,0},{{10,20},{28,28}},&data,nil};
    assert(image_layer_id((id)&layer) == 9000000001ULL);
    g_layer_frame = (IMP)native_frame;
    layer_set_frame((id)&layer,"setFrame:",layer.content_frame);
    assert(painted.size.width == 112 && painted.size.height == 28 && painted.origin.x == 10 && painted.origin.y == 20);
    layer_set_frame((id)&layer,"setFrame:",painted); assert(painted.size.width == 112);
    url.value = "/emoticons/v2/25/default/dark/1.0";
    layer_set_frame((id)&layer,"setFrame:",layer.content_frame); assert(painted.size.width == 28);
    url.value = "/emoticons/v2/9000000001/default/dark/1.0";
    host.value = "example.com"; assert(!image_layer_id((id)&layer));
    host.value = "static-cdn.jtvnw.net";
    /* Four own-message definition identities use the same downstream sizing
     * functions as incoming tokens. Native Swift construction is a donor trace,
     * not executable on this host. Animation must not imply square geometry. */
    const char *numbers[]={"9000000002","9000000001","9000000003","9000000004"};
    double widths[]={28,112,28,84};
    manager.inner=&message;token.inner=&provider;
    for(unsigned i=0;i<4;i++) {
        provider.value=numbers[i];
        assert(message_id_at(&message,12)==strtoull(numbers[i],NULL,10));
        size=message_size(&message,"sizeOfImageAttachmentAtCharacterIndex:",12);
        assert(size.width==widths[i] && size.height==28);
        rect=textkit_bounds_with((IMP)native_attachment,nil,"attachmentBounds",&container,(Rect){0},(Point){0},12);
        assert(rect.size.width==widths[i] && rect.size.height==28 && rect.origin.y==-7);
        char path[128];snprintf(path,sizeof(path),"/emoticons/v2/%s/%s/dark/1.0",numbers[i],i>=2 ? "animated" : "static");
        url.value=path;
        assert(image_layer_id((id)&layer)==strtoull(numbers[i],NULL,10));
        layer_set_frame((id)&layer,"setFrame:",layer.content_frame);
        assert(painted.size.width==widths[i] && painted.size.height==28);
        layer_set_frame((id)&layer,"setFrame:",painted);
        assert(painted.size.width==widths[i] && painted.size.height==28);
    }
    url.value="/emoticons/v2/9000000001/default/dark/1.0";
    layer.base.value = "unexpected tuple span"; layer.image_data = (id)(uintptr_t)1;
    assert(!image_layer_id((id)&layer));
    return 0;
}
'''


class EmoteUITests(unittest.TestCase):
    def test_token_map_sender_bridge_and_scoped_image_frames(self) -> None:
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "objc").mkdir()
            (root / "objc/runtime.h").write_text(RUNTIME)
            (root / "objc/objc.h").write_text('#include "runtime.h"\n')
            (root / "objc/message.h").write_text('#include "runtime.h"\n')
            harness, binary = root / "ui.c", root / "ui"
            harness.write_text(HARNESS)
            subprocess.run([zig, "cc", "-fblocks", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                            "-Wno-cast-function-type-mismatch", "-ffunction-sections", "-fdata-sections",
                            "-fsanitize=address,undefined", "-I", str(root),
                            "-I", str(ROOT / "src"), str(harness), "-Wl,--gc-sections", "-o", str(binary)],
                           check=True, capture_output=True)
            subprocess.run([binary], check=True, capture_output=True,
                           env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"})
