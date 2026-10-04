"""Deferred catalog completions after the creating autorelease pool drains."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_emote_ui import RUNTIME

ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include "TASEmotes.c"
struct Fake { const char *cls; char *value; int refs; long number; bool pooled; };
static struct Fake classes[] = {
    {.cls="NSString",.refs=-1}, {.cls="NSURL",.refs=-1},
    {.cls="NSURLSession",.refs=-1}, {.cls="NSHTTPURLResponse",.refs=-1},
    {.cls="NSData",.refs=-1}, {.cls="NSError",.refs=-1},
    {.cls="NSJSONSerialization",.refs=-1}, {.cls="NSDictionary",.refs=-1},
    {.cls="NSArray",.refs=-1}
};
static struct Fake strings[256], session={.cls="NSURLSession",.refs=-1};
static struct Fake endpoint={.cls="NSURL",.refs=-1}, task={.cls="Task",.refs=-1};
static struct Fake response={.cls="NSHTTPURLResponse",.refs=-1,.number=404};
static struct Fake body={.cls="NSData",.refs=-1,.number=201};
static struct Fake error={.cls="NSError",.refs=-1,.number=-999};
static size_t used;
static int unavailable;
struct Block {
    void *isa; int flags, reserved;
    void (*invoke)(void *,id,id,id);
    struct { uintptr_t reserved, size; } *descriptor;
};
static struct Block *pending[32];
static size_t pending_count;
void *_NSConcreteStackBlock[32];
Class objc_getClass(const char *name) {
    for (size_t i=0;i<sizeof(classes)/sizeof(*classes);i++)
        if (!strcmp(classes[i].cls,name)) return &classes[i];
    assert(!"unexpected class"); return nil;
}
SEL sel_registerName(const char *name) { return name; }
id objc_retain(id o) {
    if (o && o->refs>=0) { assert(o->refs>0); o->refs++; }
    return o;
}
void objc_release(id o) {
    if (o && o->refs>=0) { assert(o->refs>0); o->refs--; }
}
static void drain_pool(void) {
    for (size_t i=0;i<used;i++) if(strings[i].pooled) {
        strings[i].pooled=false; objc_release(&strings[i]);
    }
}
static id dispatch(id o,SEL sel,...) {
    if(!o) return nil;
    assert(o->refs!=0 && "message sent to deallocated channel identifier");
    va_list a; va_start(a,sel); id result=nil;
    if(!strcmp(sel,"stringWithUTF8String:")) {
        assert(used<256); result=&strings[used++];
        *result=(struct Fake){.cls="NSString",.value=strdup(va_arg(a,const char *)),.refs=1,.pooled=true};
        assert(result->value);
    } else if(!strcmp(sel,"UTF8String")) result=(id)o->value;
    else if(!strcmp(sel,"sharedSession")) result=unavailable==1 ? nil : &session;
    else if(!strcmp(sel,"URLWithString:")) result=unavailable==2 ? nil : &endpoint;
    else if(!strcmp(sel,"dataTaskWithURL:completionHandler:")) {
        (void)va_arg(a,id); struct Block *block=va_arg(a,struct Block *);
        if(unavailable!=3) {
            /* Match copying a plain C block: captured pointers are borrowed. */
            assert(!(block->flags&(1<<25)) && pending_count<32);
            pending[pending_count]=malloc(block->descriptor->size);
            assert(pending[pending_count]);
            memcpy(pending[pending_count++],block,block->descriptor->size); result=&task;
        }
    } else if(!strcmp(sel,"resume")) assert(o==&task);
    else if(!strcmp(sel,"isKindOfClass:")) result=(id)(uintptr_t)!strcmp(o->cls,va_arg(a,Class)->cls);
    else if(!strcmp(sel,"statusCode") || !strcmp(sel,"length") || !strcmp(sel,"code"))
        result=(id)(uintptr_t)o->number;
    else if(!strcmp(sel,"JSONObjectWithData:options:error:")) result=nil;
    else assert(!"unexpected selector");
    va_end(a); return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
void tas_diag_log(const char *event,const char *detail) { (void)event; (void)detail; }
static void complete(bool cancelled) {
    /* Finish in reverse order to exercise independent request ownership. */
    while(pending_count) {
        struct Block *block=pending[--pending_count];
        block->invoke(block,&body,&response,cancelled ? &error : nil); free(block);
    }
    drain_pool();
    for(size_t i=0;i<used;i++) assert(!strings[i].refs && "catalog request leaked a string");
}
int main(void) {
    const char *room_id="1234567890123";
    Room *room=room_locked(room_id,time(NULL));
    for(unsigned char p=0;p<3;p++) {
        room->pending[p]=true; fetch_provider(room_id,room->generation,p);
    }
    drain_pool(); complete(false);
    for(int p=0;p<3;p++) assert(room->loaded[p] && !room->pending[p]);
    /* The reported BTTV callback: HTTP 200, 201-byte body, after pool drain. */
    response.number=200; room->pending[1]=true;
    fetch_provider(room_id,room->generation,1); drain_pool(); complete(false);
    assert(!room->pending[1] && PROBE_GET(g_fetch_parse_error[1][1])==1);
    room->pending[2]=true; fetch_provider(room_id,room->generation,2);
    drain_pool(); complete(true);
    assert(!room->pending[2] && PROBE_GET(g_fetch_transport_error[2][1])==1);
    /* A room reset must still release an ignored, obsolete completion. */
    fetch_provider(room_id,room->generation,0); drain_pool();
    reset_room_locked(room,false,time(NULL)); complete(false);
    room=room_locked(room_id,time(NULL));
    for(unavailable=1;unavailable<=3;unavailable++) {
        room->pending[0]=true; fetch_provider(room_id,room->generation,0);
        drain_pool(); complete(false); assert(!room->pending[0]);
    }
    unavailable=0; g_global.pending[1]=true;
    fetch_provider(NULL,g_global.generation,1); drain_pool(); complete(false);
    assert(!g_global.pending[1]);
    for(size_t i=0;i<used;i++) free(strings[i].value);
    return 0;
}
'''


class EmoteFetchLifetimeTests(unittest.TestCase):
    def test_request_owns_room_until_completion_and_releases_every_exit(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertIsNotNone(zig, "Zig is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "objc").mkdir()
            runtime = RUNTIME + "\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n"
            (root / "objc/runtime.h").write_text(runtime)
            for name in ("objc.h", "message.h"):
                (root / "objc" / name).write_text('#include "runtime.h"\n')
            harness, binary = root / "lifetime.c", root / "lifetime"
            harness.write_text(HARNESS)
            result = subprocess.run([zig, "cc", "-std=gnu11", "-fblocks", "-Wall", "-Wextra", "-Werror",
                                     "-Wno-cast-function-type", "-ffunction-sections", "-fdata-sections",
                                     "-I", str(root), "-I", str(ROOT / "src"), str(harness),
                                     "-Wl,--gc-sections", "-pthread", "-o", str(binary)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([binary], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
