"""Native catalog admission depends on ABI capabilities, not an app version."""
import os
import shutil
import unittest
import test_composer


HARNESS = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake { const char *cls; unsigned char storage[1024]; };
static struct Fake input_class={INPUT,{0}},info_class={NATIVE_INFO,{0}};
static BOOL info_present=YES,code_present=YES,url_present=YES;
static BOOL delegate_present=YES,next_present=YES,missing_symbol;
static ptrdiff_t code_offset=16,url_offset=32,delegate_offset=560,next_offset=576;
static size_t info_size=48,input_size=1024;
static uintptr_t string_witness[9]={[8]=16},array_witness[9]={[8]=sizeof(void *)},url_witness[9]={[8]=8};
static const void *string_metadata[]={string_witness,NULL},*array_metadata[]={array_witness,NULL},*url_metadata[]={url_witness,NULL};
Class objc_getClass(const char *name) {
    /* Any former NSBundle/version read is unexpected and fails this test. */
    if (!strcmp(name,INPUT)) return &input_class;
    if (!strcmp(name,NATIVE_INFO)) return info_present ? &info_class : nil;
    assert(!"unexpected class/version lookup"); return nil;
}
Class object_getClass(id o) { return o ? &input_class : nil; }
SEL sel_registerName(const char *name) { return name; }
static id dispatch(id o,SEL selector,...) {
    if (!o) return nil;
    va_list args;va_start(args,selector);id result=nil;
    if (!strcmp(selector,"isKindOfClass:")) {
        Class cls=va_arg(args,Class);result=(id)(uintptr_t)(cls && !strcmp(o->cls,cls->cls));
    } else assert(!"unexpected message/version query");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
Ivar class_getInstanceVariable(Class cls,const char *name) {
    if (cls==&info_class) {
        if (!strcmp(name,"code")) return code_present ? &code_offset : NULL;
        if (!strcmp(name,"url")) return url_present ? &url_offset : NULL;
    } else if (cls==&input_class) {
        if (!strcmp(name,"delegate")) return delegate_present ? &delegate_offset : NULL;
        if (!strcmp(name,"inputMode")) return next_present ? &next_offset : NULL;
    }
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return *(ptrdiff_t *)iv; }
size_t class_getInstanceSize(Class cls) { return cls==&info_class ? info_size : input_size; }
static id fake_bridge(const void *value,const void *type) { (void)value;(void)type;return nil; }
static MetadataResponse fake_array(uintptr_t request,const void *type) {
    assert(!request && type==&info_class);return (MetadataResponse){array_metadata+1,0};
}
static MetadataResponse fake_url(uintptr_t request) { assert(!request);return (MetadataResponse){url_metadata+1,0}; }
static const void *fake_class_metadata(Class cls) { return cls; }
static void fake_async(void *queue,void (^block)(void)) { (void)queue;(void)block; }
static id fake_weak_load(void *storage) { (void)storage;return nil; }
static void fake_release(id value) { (void)value; }
void *dlsym(void *handle,const char *symbol) {
    (void)handle;if (missing_symbol) return NULL;
    if (!strcmp(symbol,"$ss27_bridgeAnythingToObjectiveCyyXlxlF")) return (void *)fake_bridge;
    if (!strcmp(symbol,"$sSaMa")) return (void *)fake_array;
    if (!strcmp(symbol,"$s10Foundation3URLVMa")) return (void *)fake_url;
    if (!strcmp(symbol,"swift_getObjCClassMetadata")) return (void *)fake_class_metadata;
    if (!strcmp(symbol,"dispatch_async")) return (void *)fake_async;
    if (!strcmp(symbol,"swift_unknownObjectWeakLoadStrong")) return (void *)fake_weak_load;
    if (!strcmp(symbol,"swift_unknownObjectRelease")) return (void *)fake_release;
    if (!strcmp(symbol,"$sSSN")) return (void *)(string_metadata+1);
    assert(!"unexpected dynamic symbol");return NULL;
}
int main(void) {
    info_present=NO;assert(!native_bridge_ready());info_present=YES;
    missing_symbol=YES;assert(!native_bridge_ready());missing_symbol=NO;
    code_present=NO;assert(!native_bridge_ready());code_present=YES;
    url_present=NO;assert(!native_bridge_ready());url_present=YES;
    code_offset=24;assert(!native_bridge_ready());code_offset=16;
    url_offset=24;assert(!native_bridge_ready());url_offset=32;
    info_size=32;assert(!native_bridge_ready());info_size=48;
    url_witness[8]=0;assert(!native_bridge_ready());url_witness[8]=17;assert(!native_bridge_ready());url_witness[8]=8;
    string_witness[8]=8;assert(!native_bridge_ready());string_witness[8]=16;
    array_witness[8]=16;assert(!native_bridge_ready());array_witness[8]=sizeof(void *);
    assert(native_bridge_ready()); /* no app-version query was made */
    assert(native_bridge_ready()); /* admitted metadata can be reused */
    struct Fake owner={INPUT,{0}},foreign={"UnrelatedView",{0}};
    assert(input_delegate_storage(&owner)==(char *)&owner+560);
    delegate_offset=424;next_offset=440;assert(input_delegate_storage(&owner)==(char *)&owner+424);
    delegate_offset=672;next_offset=688;assert(input_delegate_storage(&owner)==(char *)&owner+672);
    assert(!input_delegate_storage(nil) && !input_delegate_storage(&foreign));
    delegate_present=NO;assert(!input_delegate_storage(&owner));delegate_present=YES;
    next_present=NO;assert(!input_delegate_storage(&owner));next_present=YES;
    next_offset=680;assert(!input_delegate_storage(&owner));next_offset=704;assert(!input_delegate_storage(&owner));
    delegate_offset=-8;next_offset=8;assert(!input_delegate_storage(&owner));
    delegate_offset=561;next_offset=577;assert(!input_delegate_storage(&owner));
    delegate_offset=560;next_offset=576;input_size=575;assert(!input_delegate_storage(&owner));
    input_size=552;assert(!input_delegate_storage(&owner));
    input_size=576;assert(input_delegate_storage(&owner)==(char *)&owner+560);
    return 0;
}
'''


class CatalogCompatibilityTests(unittest.TestCase):
    def test_capability_gates_and_relocated_weak_delegate_storage(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        test_composer.ComposerTests().compile_run(
            HARNESS, [zig, "cc", "-fblocks", "-fsanitize=address,undefined"], runtime=True)


if __name__ == "__main__":
    unittest.main()
