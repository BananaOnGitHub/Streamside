"""Exercise bounded provenance using original decoder returns, including nil."""
import os
import shutil
import unittest
import test_composer as composer

HARNESS = r'''
#define _GNU_SOURCE
#include <stdarg.h>
#include <assert.h>
#include "TASEmoteImageProbe.c"
struct Fake { const char *kind; const void *bytes; unsigned long length; id images; };
static struct Fake data={"NSData","GIF89aPRIVATE_BYTES",18,0};
static struct Fake still={"UIImage",0,0,0},animated={"GIF",0,4,0},poster={"UIImage",0,0,0};
SEL sel_registerName(const char *s) { return s; }
static id dispatch(id object,SEL sel,...) {
    if (!object) return nil;
    va_list ap;va_start(ap,sel);id result=nil;
    if (!strcmp(sel,"respondsToSelector:")) { const char *s=va_arg(ap,const char *);result=(id)(uintptr_t)(!strcmp(s,"length") || !strcmp(s,"count") || !strcmp(s,"frameCount")); }
    else if (!strcmp(sel,"length") || !strcmp(sel,"count") || !strcmp(sel,"frameCount")) result=(id)(uintptr_t)object->length;
    else if (!strcmp(sel,"bytes")) result=(id)object->bytes;
    else if (!strcmp(sel,"images")) result=object->images;
    else assert(!"unexpected selector");
    va_end(ap);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id objc_storeWeak(id *slot,id value) { *slot=value;return value; }
id objc_loadWeakRetained(id *slot) { return *slot; }
void objc_release(id object) { (void)object; }
static unsigned original_calls,rows;
static bool gif_nil;
static char trace[8192];
void tas_emote_probe_record(uint64_t number,unsigned layer,const char *event,const char *state,bool visible) {
    (void)layer;(void)visible;assert(number==9000000001ULL);
    size_t used=strlen(trace);snprintf(trace+used,sizeof(trace)-used,"%s %s\n",event,state);rows++;
}
static id original_gif(id self,SEL sel,id input,unsigned long optimal,BOOL predraw) {
    (void)self;assert(!strcmp(sel,"gif") && input==&data && optimal==7 && predraw);original_calls++;return gif_nil ? nil : &animated;
}
static id original_ui(id self,SEL sel,id input) { (void)self;assert(!strcmp(sel,"ui") && input==&data);original_calls++;return &still; }
static id original_poster(id self,SEL sel) { assert(self==&animated && !strcmp(sel,"poster"));original_calls++;return &poster; }
int main(void) {
    char description[512];gif_init=(IMP)original_gif;ui_init=(IMP)original_ui;poster_get=(IMP)original_poster;
    tas_image_probe_response(9000000001ULL,&data);
    gif_nil=true;assert(hook_gif(nil,"gif",&data,7,YES)==nil);
    assert(hook_ui(nil,"ui",&data)==&still && original_calls==2);
    tas_image_probe_assignment(9000000001ULL,1,&still,"chat-task-static-result");
    assert(strstr(trace,"decoder=GIF result=nil") && strstr(trace,"decoder=UIImage result=image"));
    assert(strstr(trace,"assigned-body-prior-attempt") && strstr(trace,"first-observed"));
    tas_image_probe_assignment(9000000001ULL,2,&still,"chat-task-static-result");assert(strstr(trace,"reuse=reused"));
    /* A subsequent successful GIF does not retroactively explain the still. */
    gif_nil=false;assert(hook_gif(nil,"gif",&data,7,YES)==&animated);
    assert(hook_poster(&animated,"poster")==&poster && original_calls==4);
    tas_image_probe_origin(&poster,description,sizeof(description));assert(strstr(description,"decoder=GIF-poster"));
    trace[0]=0;tas_image_probe_assignment(9000000001ULL,3,&still,"chat-task-static-result");assert(strstr(trace,"decoder=GIF result=nil"));
    assert(!strstr(trace,"PRIVATE_BYTES") && !strstr(trace,"0x"));
    Origin *o=find_locked(&still,now());assert(o);o->time-=EXPIRY;
    tas_image_probe_origin(&still,description,sizeof(description));assert(strstr(description,"decode=unknown"));
    /* Weak deallocation prevents recycled identity from inheriting provenance. */
    o=find_locked(&animated,now());assert(o);objc_storeWeak(&o->weak,nil);
    tas_image_probe_origin(&animated,description,sizeof(description));assert(strstr(description,"unknown"));
    struct Fake too_big={"NSData",NULL,MAX_BYTES+1,0};assert(!fingerprint(&too_big).bytes && oversize==1);
    /* Without a validated current donor map, even a nonnull caller remains
     * unknown. No obsolete UUID/return offset is treated as current evidence. */
    assert(!strcmp(tas_image_probe_caller(NULL),"unknown") && rows>5);
    assert(!strcmp(tas_image_probe_caller((void *)(uintptr_t)1),"unknown"));
    return 0;
}
'''

class ImageProvenanceTests(unittest.TestCase):
    def test_original_results_body_match_poster_reuse_expiry_and_weak_identity(self):
        zig=os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        composer.ComposerTests().compile_run(HARNESS,[zig,"cc","-fblocks","-DTAS_EMOTE_DIAGNOSTIC=1","-fsanitize=address,undefined"],runtime=True)
