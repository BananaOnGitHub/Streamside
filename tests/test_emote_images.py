"""Production image identities and view bindings, across relaunch/cache churn."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_emote_ui import RUNTIME
import test_composer

ROOT = Path(__file__).resolve().parent.parent
IDENTITY = r'''
#include <assert.h>
#include "TASEmotes.c"
static const char *urls[]={"https://cdn.7tv.app/emote/a/2x.gif",
    "https://cdn.7tv.app/emote/b/2x.webp","https://cdn.betterttv.net/emote/c/2x"};
static const char *names[]={"Wide","Smile","Dance"};
int main(int argc,char **argv) {
    assert(argc==2);time_t now=time(NULL);Room *room=room_locked("123",now);
    for(int n=0;n<3;n++) { int i=argv[1][0]=='1' ? n : 2-n;
        add_emote_locked(room,MAX_ROOM,names[i],urls[i],i==2 ? 1 : 0,false,NULL,i ? 1 : 4);
    }
    for(int i=0;i<3;i++) {
        Emote *e=find_word(room,names[i]);assert(e);
        assert(e->fake_id>=900000000000000ULL && e->fake_id<1000000000000000ULL);
        char *url=url_for_id_locked(e->fake_id,now);assert(url && !strcmp(url,urls[i]));free(url);
        printf("%llu\t%s\n",(unsigned long long)e->fake_id,e->url);
    }
    assert(!url_for_id_locked(9000000000ULL,now)); /* old disk-cache namespace */
    uint64_t previous=find_word(room,"Wide")->fake_id;
    reset_room_locked(room,true,now);room=room_locked("123",now);
    const char *replacement="https://cdn.7tv.app/emote/replacement/2x.gif";
    add_emote_locked(room,MAX_ROOM,"Wide",replacement,0,false,NULL,2);
    uint64_t current=find_word(room,"Wide")->fake_id;assert(current!=previous);
    char *url=url_for_id_locked(previous,now);assert(url && !strcmp(url,urls[0]));free(url);
    url=url_for_id_locked(current,now);assert(url && !strcmp(url,replacement));free(url);
    /* Reloading identical metadata retains its cache key. Changing channel
     * or provider cannot steal the old visible cell's bitmap/aspect mapping. */
    reset_room_locked(room,true,now);room=room_locked("123",now);
    add_emote_locked(room,MAX_ROOM,"Wide",replacement,0,false,NULL,2);
    assert(find_word(room,"Wide")->fake_id==current);
    Room *other=room_locked("456",now);
    add_emote_locked(other,MAX_ROOM,"Wide",urls[0],0,false,NULL,4);
    assert(find_word(other,"Wide")->fake_id!=previous);
    add_emote_locked(room,MAX_ROOM,"Wide","https://cdn.betterttv.net/emote/native/2x",1,false,NULL,1);
    assert(find_word(room,"Wide")->fake_id==current); /* rank wins */
    /* Deliberately inject a hash collision: registration must fail closed. */
    const char *collision_url="https://cdn.7tv.app/emote/collision/2x.webp";
    uint64_t collision=image_identity(other->id,"Collision",collision_url);
    g_old[0].emote.fake_id=collision;
    add_emote_locked(other,MAX_ROOM,"Collision",collision_url,0,false,NULL,1);
    assert(!find_word(other,"Collision"));
    tas_emotes_clear_cache();assert(!url_for_id_locked(current,now));
    room=room_locked("123",now);
    add_emote_locked(room,MAX_ROOM,"Wide",replacement,0,false,NULL,2);
    assert(find_word(room,"Wide")->fake_id==current);
    tas_emotes_clear_cache();return 0;
}
'''

THUMBNAILS = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake { const char *text; id url,image,animation,record; unsigned sets,resets; };
static struct Fake string_class,strings[512],cache,image_fixture;
static U string_count,requests;
static id cache_url,cache_record;
Class objc_getClass(const char *name) { assert(!strcmp(name,"NSString"));return &string_class; }
SEL sel_registerName(const char *name) { return name; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;
    va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"stringWithUTF8String:")) { assert(string_count<512);result=&strings[string_count++];result->text=va_arg(args,const char *); }
    else if(!strcmp(sel,"objectForKey:")) {
        id k=va_arg(args,id);
        if(o==&cache) result=cache_url && !strcmp(k->text,cache_url->text) ? cache_record : nil;
        else if(!strcmp(k->text,"url"))result=o->url;
        else if(!strcmp(k->text,"image"))result=o->image;
        else if(!strcmp(k->text,"animation"))result=o->animation;
        else assert(0);
    } else if(!strcmp(sel,"isEqual:")) { id b=va_arg(args,id);result=(id)(uintptr_t)(b && !strcmp(o->text,b->text)); }
    else if(!strcmp(sel,"respondsToSelector:")) { const char *s=va_arg(args,SEL);result=(id)(uintptr_t)!strcmp(s,"setAnimatedImage:"); }
    else if(!strcmp(sel,"setImage:")) { o->image=va_arg(args,id);o->animation=nil;o->sets++;o->resets++; }
    else if(!strcmp(sel,"setAnimatedImage:")) { o->animation=va_arg(args,id);o->sets++;o->resets++; }
    else assert(!"unexpected thumbnail selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id objc_getAssociatedObject(id o,const void *k) {
    assert(o==&image_fixture);return k==&thumbnail_url_key ? o->url : o->record;
}
void objc_setAssociatedObject(id o,const void *k,id value,uintptr_t policy) {
    assert(o==&image_fixture && policy==1);if(k==&thumbnail_url_key)o->url=value;else { assert(k==&thumbnail_record_key);o->record=value; }
}
static void ss_test_request(id metadata) { assert(metadata->url);requests++; }
int main(void) {
    struct Fake a={.text="https://cdn.7tv.app/emote/a/2x.gif"},b={.text="https://cdn.7tv.app/emote/b/2x.gif"};
    struct Fake bitmap_a={0},bitmap_b={0},animation_a={0},animation_b={0};
    struct Fake metadata_a={.url=&a},metadata_b={.url=&b};
    struct Fake record_a={.image=&bitmap_a,.animation=&animation_a},record_b={.image=&bitmap_b,.animation=&animation_b};
    images=&cache;cache_url=&a;cache_record=&record_a;
    set_thumbnail(&image_fixture,&metadata_a);assert(image_fixture.animation==&animation_a && image_fixture.record==&record_a && !requests);
    unsigned updates=image_fixture.sets;
    for(int i=0;i<20;i++)set_thumbnail(&image_fixture,&metadata_a);
    assert(image_fixture.sets==updates && image_fixture.resets==1); /* no frame-clock resets */
    cache_record=nil; /* memory pressure evicts decoded NSCache entries */
    set_thumbnail(&image_fixture,&metadata_a);assert(image_fixture.animation==&animation_a && image_fixture.sets==updates && !requests);
    set_thumbnail(&image_fixture,&metadata_b);assert(!image_fixture.animation && !image_fixture.image && requests==1);
    /* An obsolete A completion cannot paint B. The shared cache only contains
     * A; selection is still made against the image_fixture's current metadata URL. */
    cache_record=&record_a;set_thumbnail(&image_fixture,&metadata_b);assert(!image_fixture.animation && requests==2);
    cache_url=&b;cache_record=&record_b;set_thumbnail(&image_fixture,&metadata_b);
    assert(image_fixture.animation==&animation_b && image_fixture.record==&record_b);
    updates=image_fixture.sets;set_thumbnail(&image_fixture,&metadata_b);assert(image_fixture.sets==updates);
    /* Reusing a formerly animated image_fixture for a still clears its old animation. */
    record_a.animation=nil;cache_url=&a;cache_record=&record_a;set_thumbnail(&image_fixture,&metadata_a);
    assert(!image_fixture.animation && image_fixture.image==&bitmap_a);
    return 0;
}
'''


ANIMATIONS = r'''
#include <stdarg.h>
#include <assert.h>
#include "TASEmoteUI.c"
struct Fake { const char *cls,*value; id inner,animation,link,parent,bound; BOOL hidden,paused; NSUInteger loops; };
struct FakeAttachment { struct Fake base; Rect content; id data,requester,animated; };
static struct Fake classes[]={{.cls="NSString"},{.cls="_TtC6Twitch20ImageAttachmentLayer"},
    {.cls="_TtC6Twitch22MessageStringImageData"},{.cls="TWAnimatedImageLayer"}};
static struct Fake host={.cls="NSString",.value="static-cdn.jtvnw.net"},temporary;
static unsigned bindings,resumes;
Class objc_getClass(const char *name) { for(size_t i=0;i<4;i++)if(!strcmp(classes[i].cls,name))return &classes[i];return nil; }
Class object_getClass(id o) { return o; }
SEL sel_registerName(const char *name) { return name; }
static ptrdiff_t offsets[]={offsetof(struct FakeAttachment,content),offsetof(struct FakeAttachment,requester),offsetof(struct FakeAttachment,animated)};
Ivar class_getInstanceVariable(Class c,const char *name) {
    if(strcmp(c->cls,"_TtC6Twitch20ImageAttachmentLayer"))return NULL;
    if(!strcmp(name,"content"))return offsets;
    if(!strcmp(name,"networkImageRequester"))return offsets+1;
    if(!strcmp(name,"animatedImageLayer"))return offsets+2;
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar i) { return *(ptrdiff_t *)i; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;
    va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(args,Class);result=(id)(uintptr_t)(c && !strcmp(c->cls,o->cls)); }
    else if(!strcmp(sel,"respondsToSelector:")) { (void)va_arg(args,SEL);result=(id)(uintptr_t)YES; }
    else if(!strcmp(sel,"stringWithUTF8String:")) { temporary.cls="NSString";temporary.value=va_arg(args,const char *);result=&temporary; }
    else if(!strcmp(sel,"isEqualToString:")) { id b=va_arg(args,id);result=(id)(uintptr_t)(b && !strcmp(o->value,b->value)); }
    else if(!strcmp(sel,"UTF8String"))result=(id)o->value;
    else if(!strcmp(sel,"host"))result=&host;
    else if(!strcmp(sel,"path"))result=o;
    else if(!strcmp(sel,"staticURL"))result=o->inner;
    else if(!strcmp(sel,"animatedURL"))result=nil;
    else if(!strcmp(sel,"superlayer"))result=o->parent;
    else if(!strcmp(sel,"animatedImage"))result=o->animation;
    else if(!strcmp(sel,"displayLink"))result=o->link;
    else if(!strcmp(sel,"isPaused"))result=(id)(uintptr_t)o->paused;
    else if(!strcmp(sel,"setLoopCountdown:")) { o->loops=va_arg(args,NSUInteger);bindings++; }
    else if(!strcmp(sel,"updateAnimationState")) { if(o->parent && !o->hidden && o->animation) { o->link->paused=NO;resumes++; } }
    else assert(!"unexpected animation selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id objc_getAssociatedObject(id o,const void *k) { assert(k==&g_animation_key);return o->bound; }
void objc_setAssociatedObject(id o,const void *k,id value,uintptr_t policy) { assert(k==&g_animation_key && policy==1);o->bound=value; }
static void native_set(id o,SEL sel,id image) { (void)sel;if(o->animation!=image){o->animation=image;o->loops=3;o->link->paused=YES;} }
int main(void) {
    struct Fake url={.cls="NSURL",.value="/emoticons/v2/900123456789012/default/dark/1.0"};
    struct Fake data={.cls="_TtC6Twitch22MessageStringImageData",.inner=&url};
    struct Fake animation={.cls="FLAnimatedImage"},replacement={.cls="FLAnimatedImage"},link={.cls="CADisplayLink",.paused=YES};
    struct Fake layer={.cls="TWAnimatedImageLayer",.link=&link};
    struct FakeAttachment attachment={.base={.cls="_TtC6Twitch20ImageAttachmentLayer"},.data=&data,.animated=&layer};
    layer.parent=(id)&attachment;g_animated_image=(IMP)native_set;
    animated_set_image(&layer,"setAnimatedImage:",&animation);
    assert(bindings==1 && layer.loops==UINT64_MAX && !link.paused && resumes==1);
    provider_animation((id)&attachment);assert(bindings==1 && resumes==1);
    link.paused=YES;provider_animation((id)&attachment);assert(resumes==2 && !link.paused);
    layer.hidden=YES;link.paused=YES;provider_animation((id)&attachment);assert(link.paused && resumes==2);
    layer.hidden=NO;layer.parent=nil;provider_animation((id)&attachment);assert(link.paused && resumes==2);
    layer.parent=(id)&attachment;animated_set_image(&layer,"setAnimatedImage:",&replacement);
    assert(bindings==2 && layer.loops==UINT64_MAX && !link.paused);
    /* Native Twitch emotes retain their finite loop count and paused state. */
    url.value="/emoticons/v2/25/default/dark/1.0";
    animated_set_image(&layer,"setAnimatedImage:",&animation);assert(layer.loops==3 && link.paused && bindings==2);
    url.value="/emoticons/v2/900123456789012/default/dark/1.0";
    animated_set_image(&layer,"setAnimatedImage:",nil);assert(!layer.bound && !layer.animation);
    return 0;
}
'''


class EmoteImageTests(unittest.TestCase):
    def test_disk_cache_identity_survives_relaunch_order_changes(self):
        zig=os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"objc").mkdir()
            runtime=RUNTIME+'\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n'
            for name in ("runtime.h","objc.h","message.h"):(root/"objc"/name).write_text(runtime)
            harness=root/"identity.c";binary=root/"identity";harness.write_text(IDENTITY)
            result=subprocess.run([zig,"cc","-fblocks","-Wall","-Wextra","-Werror","-Wno-cast-function-type-mismatch","-ffunction-sections","-fdata-sections",
                "-Wl,--gc-sections","-I",str(root),"-I",str(ROOT/"src"),str(harness),"-pthread","-o",str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            first=subprocess.run([binary,"1"],capture_output=True,text=True)
            second=subprocess.run([binary,"2"],capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr);self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual(first.stdout,second.stdout)

    def test_thumbnail_playback_survives_refresh_eviction_and_stale_completion(self):
        zig=os.environ.get("ZIG") or shutil.which("zig");self.assertTrue(zig)
        source=(ROOT/"src"/"SSComposer.c").read_text()
        # Stub transport only; production lookup, association and view binding
        # remain intact. Simulate completions and eviction through the cache.
        start=source.index('static void image_request(');end=source.index('\n}',start)+2
        source=source[:start]+'static void ss_test_request(id);\nstatic void image_request(id metadata) { ss_test_request(metadata); }'+source[end:]
        test_composer.ComposerTests().compile_run(THUMBNAILS.replace('#include "SSComposer.c"',source),[zig,"cc","-fblocks"],runtime=True)

    def test_chat_animation_rebinding_and_visibility_keep_native_emotes_unchanged(self):
        zig=os.environ.get("ZIG") or shutil.which("zig");self.assertTrue(zig)
        test_composer.ComposerTests().compile_run(ANIMATIONS,[zig,"cc","-fblocks","-fsanitize=address,undefined"],runtime=True)


if __name__=="__main__":unittest.main()
