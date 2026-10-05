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
    else if (!strcmp(sel,"posterImage")) result=hook_poster(object,"posterImage");
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
static id original_poster(id self,SEL sel) { assert(self==&animated && (!strcmp(sel,"poster") || !strcmp(sel,"posterImage")));original_calls++;return &poster; }
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
    assert(hook_poster(&animated,"poster")==&poster && original_calls==5);
    tas_image_probe_origin(&poster,description,sizeof(description));assert(strstr(description,"decoder=GIF-poster"));
    trace[0]=0;tas_image_probe_assignment(9000000001ULL,3,&still,"chat-task-static-result");assert(strstr(trace,"decoder=GIF result=nil"));
    assert(!strstr(trace,"PRIVATE_BYTES") && !strstr(trace,"0x"));
    Origin *o=find_locked(&still,now());assert(o);o->seen-=EXPIRY;
    tas_image_probe_origin(&still,description,sizeof(description));assert(strstr(description,"decode=unknown"));
    /* Weak deallocation prevents recycled identity from inheriting provenance. */
    o=find_locked(&animated,now());assert(o);objc_storeWeak(&o->weak,nil);
    tas_image_probe_origin(&animated,description,sizeof(description));assert(strstr(description,"unknown"));
    struct Fake too_big={"NSData",NULL,MAX_BYTES+1,0};assert(!fingerprint(&too_big).bytes && oversize==1);
    unsigned char header[56]={0};uint32_t word=0xfeedfacf;memcpy(header,&word,4);word=1;memcpy(header+16,&word,4);word=24;memcpy(header+20,&word,4);memcpy(header+36,&word,4);word=0x1b;memcpy(header+32,&word,4);
    unsigned char uuid[16]={0x96,0x0f,0x52,0x32,0x0e,0xb5,0x3e,0xcc,0x80,0,0x15,0x74,0x6c,0xb1,0xe3,0x7b};memcpy(header+40,uuid,16);
    assert(donor(header));header[40]^=1;assert(!donor(header));
    assert(!strcmp(tas_image_probe_caller(NULL),"unknown") && rows>5);
    return 0;
}
'''

class ImageProvenanceTests(unittest.TestCase):
    def test_original_results_body_match_poster_reuse_expiry_and_weak_identity(self):
        zig=os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        composer.ComposerTests().compile_run(HARNESS,[zig,"cc","-fblocks","-DTAS_EMOTE_DIAGNOSTIC=1","-fsanitize=address,undefined"],runtime=True)

    def test_constructor_copies_response_and_unknown_identity(self):
        extra = r'''
static struct Fake copy={"UIImage",0,0,0},unknown={"UIImage",0,0,0};
static id returned;
static void *raster=(void *)0x1234;
static unsigned forwarded;
static id original_cg(id self,SEL sel,void *cg) { assert(self==&copy && !strcmp(sel,"cg") && cg==raster);forwarded++;return returned; }
static id original_cg_scale(id self,SEL sel,void *cg,double scale,long orientation) { assert(self==&copy && !strcmp(sel,"cg-scale") && cg==raster && scale==2.5 && orientation==7);forwarded++;return returned; }
static void *original_cg_get(id self,SEL sel) { assert(self==&still && !strcmp(sel,"cg-get"));forwarded++;return raster; }
static id original_response_init(id self,SEL sel,id image,id url) { assert(self==&unknown && !strcmp(sel,"response") && image==&unknown && url==&data);forwarded++;return self; }
static id original_response_get(id self,SEL sel) { assert(self==&unknown && !strcmp(sel,"response-get"));forwarded++;return self; }
int main(void) {
    char description[512];
    gif_init=(IMP)original_gif;ui_init=(IMP)original_ui;
    cg_init=(IMP)original_cg;cg_scale=(IMP)original_cg_scale;cg_get=(IMP)original_cg_get;
    response_init=(IMP)original_response_init;response_get=(IMP)original_response_get;
    /* Unmatched decoded bytes must not be reported as a provider response. */
    decoded(&data,&still,"UIImage",0);
    tas_image_probe_assignment(9000000001ULL,1,&still,"static");
    assert(strstr(trace,"body=decoded-bytes-only") && !strstr(trace,"body=matched-response"));
    uint64_t parent=find_locked(&still,now())->object;
    assert(hook_cg_get(&still,"cg-get")==raster && forwarded==1);
    returned=&copy;assert(hook_cg_scale(&copy,"cg-scale",raster,2.5,7)==&copy && forwarded==2);
    Origin *o=find_locked(&copy,now());assert(o && o->parent==parent && o->serial==1 && o->frames==0 && o->object!=parent);
    uint64_t ordinal=o->object;
    constructed(&copy,raster,"native-task-static-imageio");constructed(&copy,raster,"unknown");
    assert(o->object==ordinal && o->parent==parent && !strcmp(o->creator,"native-task-static-imageio"));
    tas_image_probe_response(9000000001ULL,&data);trace[0]=0;
    tas_image_probe_assignment(9000000001ULL,2,&copy,"static");assert(strstr(trace,"body=matched-response") && strstr(trace,"cache-hit=unknown"));
    /* Weak owner loss makes a recycled raster untrustworthy. */
    for (unsigned i=0;i<ORIGINS;i++) if (origins[i].weak==&still || origins[i].weak==&copy) objc_storeWeak(&origins[i].weak,nil);
    for (unsigned i=0;i<256;i++) if (rasters[i].weak==&still || rasters[i].weak==&copy) objc_storeWeak(&rasters[i].weak,nil);
    assert(hook_cg(&copy,"cg",raster)==&copy && forwarded==3);
    o=find_locked(&copy,now());assert(o && !o->parent && !o->serial && o->object!=ordinal);
    returned=nil;assert(hook_cg_scale(&copy,"cg-scale",raster,2.5,7)==nil && forwarded==4);
    assert(hook_response_init(&unknown,"response",&unknown,&data)==&unknown && forwarded==5);
    assert(hook_response_get(&unknown,"response-get")==&unknown && forwarded==6);
    trace[0]=0;tas_image_probe_assignment(9000000001ULL,3,&unknown,"static");
    assert(strstr(trace,"source=native-response-observed") && strstr(trace,"file=1") && strstr(trace,"cache-hit=unknown"));
    struct Fake unseen={"UIImage",0,0,0};trace[0]=0;
    tas_image_probe_assignment(9000000001ULL,4,&unseen,"static");
    tas_image_probe_assignment(9000000001ULL,5,&unseen,"static");
    assert(strstr(trace,"source=first-seen-at-handoff") && strstr(trace,"decode=unknown") && strstr(trace,"reuse=reused"));
    /* Heavy unrelated constructor traffic cannot evict a live assigned result. */
    struct Fake traffic[ORIGINS+16]={0};ordinal=find_locked(&unseen,now())->object;
    for (unsigned i=0;i<ORIGINS+16;i++) constructed(&traffic[i],NULL,"unknown");
    assert(find_locked(&unseen,now())->object==ordinal);
    /* A fresh poster observation may inherit an old decode without expiring immediately. */
    Attempt old={.serial=9,.frames=4,.time=now()-EXPIRY-10,.kind="GIF",.success=true};
    o=put_locked(&animated,old,"GIF");assert(o);poster_get=(IMP)original_poster;
    assert(hook_poster(&animated,"poster")==&poster);
    tas_image_probe_origin(&poster,description,sizeof(description));assert(strstr(description,"decode=9"));
    assert(!strstr(trace,"PRIVATE_BYTES") && !strstr(trace,"0x"));
    return 0;
}
'''
        harness=HARNESS[:HARNESS.index("int main(void)")]+extra
        zig=os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        composer.ComposerTests().compile_run(harness,[zig,"cc","-fblocks","-DTAS_EMOTE_DIAGNOSTIC=1","-fsanitize=address,undefined"],runtime=True)
