from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_emote_ui import RUNTIME

ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include <stdarg.h>
#include <assert.h>
#include "TASEmotes.c"
struct Fake { const char *cls, *value; };
static struct Fake classes[] = {{"NSString",0},{"NSDictionary",0},{"NSArray",0}};
static struct Fake root = {"NSDictionary",0}, set = {"NSDictionary",0}, emote = {"NSDictionary",0};
static struct Fake data = {"NSDictionary",0}, host = {"NSDictionary",0}, file = {"NSDictionary",0};
static struct Fake emotes = {"NSArray",0}, files = {"NSArray",0};
static char name_buf[32], id_buf[32];
static struct Fake name = {"NSString",name_buf}, number = {"NSString",id_buf};
static struct Fake filename = {"NSString","2x.webp"}, key_string = {"NSString",0};
static struct Fake room_string = {"NSString","12345"};
static size_t emote_count = 2183;
static char logged[512];
Class objc_getClass(const char *n) {
    for (size_t i=0;i<sizeof(classes)/sizeof(classes[0]);i++) if (!strcmp(classes[i].cls,n)) return &classes[i];
    return nil;
}
SEL sel_registerName(const char *n) { return n; }
static id dispatch(id o, SEL sel, ...) {
    if (!o) return nil;
    va_list args; va_start(args,sel); id result = nil;
    if (!strcmp(sel,"isKindOfClass:")) {
        Class c=va_arg(args,Class); result=(id)(uintptr_t)(c && !strcmp(c->cls,o->cls));
    } else if (!strcmp(sel,"UTF8String")) result=(id)o->value;
    else if (!strcmp(sel,"description")) result=o;
    else if (!strcmp(sel,"stringWithUTF8String:")) { key_string.value=va_arg(args,const char *); result=&key_string; }
    else if (!strcmp(sel,"count")) result=(id)(uintptr_t)(o==&emotes ? emote_count : 1);
    else if (!strcmp(sel,"objectAtIndex:")) {
        size_t index=va_arg(args,size_t);
        if(o==&emotes) {
            snprintf(name_buf,sizeof(name_buf),"Emote%04zu",index);
            snprintf(id_buf,sizeof(id_buf),"id%04zu",index); result=&emote;
        } else result=&file;
    } else if (!strcmp(sel,"objectForKey:")) {
        id key=va_arg(args,id); const char *k=key->value;
        if(o==&root && !strcmp(k,"emote_set")) result=&set;
        else if(o==&set && !strcmp(k,"emotes")) result=&emotes;
        else if(o==&emote && !strcmp(k,"name")) result=&name;
        else if(o==&emote && !strcmp(k,"id")) result=&number;
        else if(o==&emote && !strcmp(k,"data")) result=&data;
        else if(o==&data && !strcmp(k,"host")) result=&host;
        else if(o==&host && !strcmp(k,"files")) result=&files;
        else if(o==&file && !strcmp(k,"name")) result=&filename;
    } else { fprintf(stderr,"unexpected selector: %s on %s\n",sel,o->cls); assert(!"unexpected selector"); }
    va_end(args); return result;
}
id (*objc_msgSend)(id,SEL,...) = dispatch;
void tas_diag_log(const char *event,const char *detail) {
    assert(!strcmp(event,"EMOTE_FETCH")); snprintf(logged,sizeof(logged),"%s",detail);
}
static void complete(Room *r,long status,size_t bytes,bool transport,id parsed) {
    r->pending[0]=true;
    finish_provider(&room_string,r->generation,0,status,bytes,transport ? -1009 : 0,
                    tas_emote_fetch_result(status,bytes,transport,false),parsed);
    assert(!r->pending[0]);
}
int main(void) {
    /* Byte counts and entry counts measured from live channel responses.
     * Exercise production completion, parser, registry and lookup without
     * network dependency or storing real channel names, IDs or API bodies. */
    Room *r=room_locked("12345",time(NULL));
    emote_count=966; complete(r,200,2371044,false,&root);
    assert(r->loaded[0] && r->size==966 && find_word(r,"Emote0965"));
    emote_count=2183; complete(r,200,5229639,false,&root);
    assert(r->loaded[0] && r->size==2183 && find_word(r,"Emote2182"));
    assert(!PROBE_GET(g_fetch_failed[0][1]));
    assert(PROBE_GET(g_fetch_loaded[0][1])==2);
    assert(strstr(logged,"status=200 bytes=5229639") && strstr(logged,"entries=2183"));
    assert(!strstr(logged,"12345") && !strstr(logged,"https://") && !strstr(logged,"Emote"));
    complete(r,200,TAS_EMOTE_MAX_API_BYTES+1,false,&root);
    assert(!r->loaded[0] && r->size==2183 && PROBE_GET(g_fetch_body_error[0][1])==1);
    assert(!PROBE_GET(g_fetch_http_error[0][1]) && strstr(logged,"result=oversized"));
    complete(r,200,0,false,nil);
    assert(PROBE_GET(g_fetch_body_error[0][1])==2 && strstr(logged,"result=empty"));
    complete(r,429,100,false,nil);
    assert(PROBE_GET(g_fetch_http_error[0][1])==1 && strstr(logged,"result=http"));
    complete(r,0,0,true,nil);
    assert(PROBE_GET(g_fetch_transport_error[0][1])==1 && strstr(logged,"error=-1009 result=transport"));
    complete(r,200,100,false,nil);
    assert(PROBE_GET(g_fetch_parse_error[0][1])==1 && strstr(logged,"result=json"));
    complete(r,200,100,false,&data);
    assert(PROBE_GET(g_fetch_parse_error[0][1])==2 && strstr(logged,"result=schema"));
    complete(r,404,100,false,nil);
    assert(r->loaded[0] && PROBE_GET(g_fetch_absent[0][1])==1 && !r->failures[0]);
    assert(tas_emote_fetch_result(404,100,false,true)==TAS_FETCH_HTTP);
    assert(tas_emote_fetch_result(200,TAS_EMOTE_MAX_API_BYTES,false,false)==TAS_FETCH_READY);
    r->pending[0]=true;
    finish_provider(&room_string,r->generation,0,0,0,0,TAS_FETCH_UNAVAILABLE,nil);
    assert(!r->pending[0] && !r->loaded[0] && r->failures[0]==1);
    r->pending[0]=true;
    finish_provider(&room_string,r->generation-1,0,200,100,0,TAS_FETCH_READY,&root);
    assert(r->pending[0] && !r->loaded[0]); /* Ignore superseded responses. */
    emote_count=TAS_EMOTE_MAX_ROOM+1;
    complete(r,200,TAS_EMOTE_MAX_API_BYTES,false,&root);
    assert(r->size==TAS_EMOTE_MAX_ROOM && find_word(r,"Emote3999") && !find_word(r,"Emote4000"));
    reset_room_locked(r,false,time(NULL));
    return 0;
}
'''


class EmoteFetchTests(unittest.TestCase):
    def test_large_sets_failure_categories_pending_state_and_privacy(self) -> None:
        zig = os.environ.get("ZIG") or shutil.which("zig")
        if not zig:
            self.fail("Zig is required to test the production C block-based fetch module")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "objc").mkdir()
            runtime = RUNTIME + "\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n"
            (root / "objc/runtime.h").write_text(runtime)
            (root / "objc/objc.h").write_text('#include "runtime.h"\n')
            (root / "objc/message.h").write_text('#include "runtime.h"\n')
            harness, binary = root / "fetch.c", root / "fetch"
            harness.write_text(HARNESS)
            result = subprocess.run([zig, "cc", "-std=gnu11", "-fblocks", "-Wall", "-Wextra", "-Werror",
                                     "-Wno-cast-function-type", "-ffunction-sections", "-fdata-sections",
                                     "-I", str(root), "-I", str(ROOT / "src"), str(harness),
                                     "-Wl,--gc-sections", "-pthread", "-o", str(binary)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([binary], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
