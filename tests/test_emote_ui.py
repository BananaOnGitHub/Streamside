from __future__ import annotations

import os
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
static struct Fake classes[] = {{"NSString",0,0},{"NSNumber",0,0}};
static struct Fake location = {"NSNumber","12",0};
Class objc_getClass(const char *name) {
    for (int i=0;i<2;i++) if (!strcmp(name,classes[i].class_name)) return &classes[i];
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
                                (!strcmp(probe,"layoutManager") && !strcmp(o->class_name,"NSTextContainer")));
    } else if (!strcmp(sel,"emoteId") || !strcmp(sel,"emoteLocationsMap") || !strcmp(sel,"layoutManager")) result = o->inner;
    else if (!strcmp(sel,"description")) result = o;
    else if (!strcmp(sel,"UTF8String")) result = (id)o->value;
    else if (!strcmp(sel,"numberWithInteger:")) { (void)va_arg(args,long); result = &location; }
    else if (!strcmp(sel,"objectForKey:")) { (void)va_arg(args,id); result = o->inner; }
    else assert(!"unexpected selector in resolver test");
    va_end(args); return result;
}
id (*objc_msgSend)(id,SEL,...) = dispatch;
Class object_getClass(id o) { return o; }
Ivar class_getInstanceVariable(Class cls,const char *name) { (void)cls; (void)name; return NULL; }
ptrdiff_t ivar_getOffset(Ivar ivar) { (void)ivar; return 0; }
id objc_getAssociatedObject(id o,const void *key_value) { (void)key_value; return o ? o->inner : nil; }
double tas_emotes_aspect(uint64_t number) { return number == 9000000001ULL ? 4 : 0; }
static Size native_size(id self,SEL sel,NSInteger index) {
    (void)self; (void)sel; (void)index; return (Size){28,28};
}
static Rect native_attachment(id self,SEL sel,id container,Rect fragment,Point position,NSUInteger index) {
    (void)self; (void)sel; (void)container; (void)fragment; (void)position; (void)index;
    return (Rect){{0,-7},{28,28}};
}
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
    return 0;
}
'''


class EmoteUITests(unittest.TestCase):
    def test_token_map_resolves_provider_ids_and_preserves_native_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "objc").mkdir()
            (root / "objc/runtime.h").write_text(RUNTIME)
            (root / "objc/objc.h").write_text('#include "runtime.h"\n')
            (root / "objc/message.h").write_text('#include "runtime.h"\n')
            harness, binary = root / "ui.c", root / "ui"
            harness.write_text(HARNESS)
            subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                            "-Wno-cast-function-type", "-ffunction-sections", "-fdata-sections",
                            "-fsanitize=address,undefined", "-I", str(root),
                            "-I", str(ROOT / "src"), str(harness), "-Wl,--gc-sections", "-o", str(binary)],
                           check=True, capture_output=True)
            subprocess.run([binary], check=True, capture_output=True,
                           env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"})
