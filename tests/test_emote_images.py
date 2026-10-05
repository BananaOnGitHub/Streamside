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
struct Block { void *isa; int flags,reserved; void (*invoke)(struct Block *,id); };
struct Fake { const char *cls,*value; id inner,animation,link,parent,bound,delegate,window,members[128]; BOOL hidden,paused,invalid,clips; NSUInteger loops,length; float opacity; Rect bounds,projected; double interval,tolerance; struct Block *block; };
struct FakeAttachment { struct Fake base; Rect content; id data,requester,animated,still; };
static struct Fake classes[]={{.cls="NSString"},{.cls="_TtC6Twitch20ImageAttachmentLayer"},
    {.cls="_TtC6Twitch22MessageStringImageData"},{.cls="TWAnimatedImageLayer"},{.cls="UIApplication"},
    {.cls="UIView"},{.cls="NSHashTable"},{.cls="NSTimer"},{.cls="NSRunLoop"},{.cls="CALayer"},{.cls="UIImage"}};
static struct Fake host={.cls="NSString",.value="static-cdn.jtvnw.net"},temporary;
static struct Fake weak_set,snapshot,application,runloop,timers[16];
static unsigned bindings,resumes,created,invalidated,set_calls; static NSInteger app_state;
Class objc_getClass(const char *name) { for(size_t i=0;i<sizeof(classes)/sizeof(classes[0]);i++)if(!strcmp(classes[i].cls,name))return &classes[i];return nil; }
Class object_getClass(id o) { return o; }
SEL sel_registerName(const char *name) { return name; }
static ptrdiff_t offsets[]={offsetof(struct FakeAttachment,content),offsetof(struct FakeAttachment,requester),offsetof(struct FakeAttachment,animated),offsetof(struct FakeAttachment,still)};
Ivar class_getInstanceVariable(Class c,const char *name) {
    if(strcmp(c->cls,"_TtC6Twitch20ImageAttachmentLayer"))return NULL;
    if(!strcmp(name,"content"))return offsets;
    if(!strcmp(name,"networkImageRequester"))return offsets+1;
    if(!strcmp(name,"animatedImageLayer"))return offsets+2;
    if(!strcmp(name,"staticImageLayer"))return offsets+3;
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar i) { return *(ptrdiff_t *)i; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;
    va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(args,Class);result=(id)(uintptr_t)(c && (!strcmp(c->cls,o->cls) || (!strcmp(c->cls,"CALayer") && !strcmp(o->cls,"TWAnimatedImageLayer")))); }
    else if(!strcmp(sel,"respondsToSelector:")) { (void)va_arg(args,SEL);result=(id)(uintptr_t)YES; }
    else if(!strcmp(sel,"stringWithUTF8String:")) { temporary.cls="NSString";temporary.value=va_arg(args,const char *);result=&temporary; }
    else if(!strcmp(sel,"isEqualToString:")) { id b=va_arg(args,id);result=(id)(uintptr_t)(b && !strcmp(o->value,b->value)); }
    else if(!strcmp(sel,"UTF8String"))result=(id)o->value;
    else if(!strcmp(sel,"host"))result=&host;
    else if(!strcmp(sel,"path"))result=o;
    else if(!strcmp(sel,"staticURL"))result=o->inner;
    else if(!strcmp(sel,"animatedURL"))result=nil;
    else if(!strcmp(sel,"superlayer"))result=o->parent;
    else if(!strcmp(sel,"delegate"))result=o->delegate;
    else if(!strcmp(sel,"window"))result=o->window;
    else if(!strcmp(sel,"layer"))result=o->inner;
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"masksToBounds"))result=(id)(uintptr_t)o->clips;
    else if(!strcmp(sel,"animatedImage"))result=o->animation;
    else if(!strcmp(sel,"displayLink"))result=o->link;
    else if(!strcmp(sel,"isPaused"))result=(id)(uintptr_t)o->paused;
    else if(!strcmp(sel,"setLoopCountdown:")) { o->loops=va_arg(args,NSUInteger);bindings++; }
    else if(!strcmp(sel,"loopCountdown"))result=(id)(uintptr_t)o->loops;
    else if(!strcmp(sel,"sharedApplication"))result=&application;
    else if(!strcmp(sel,"applicationState"))result=(id)(uintptr_t)app_state;
    else if(!strcmp(sel,"weakObjectsHashTable"))result=&weak_set;
    else if(!strcmp(sel,"addObject:")) {
        id value=va_arg(args,id);NSUInteger i=0;for(;i<o->length;i++)if(o->members[i]==value)break;
        if(i==o->length){assert(i<128);o->members[o->length++]=value;}
    }
    else if(!strcmp(sel,"removeObject:")) {
        id value=va_arg(args,id);for(NSUInteger i=0;i<o->length;i++)if(o->members[i]==value){memmove(o->members+i,o->members+i+1,(o->length-i-1)*sizeof(id));o->length--;break;}
    }
    else if(!strcmp(sel,"allObjects")){snapshot=*o;result=&snapshot;}
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->length;
    else if(!strcmp(sel,"objectAtIndex:")){NSUInteger i=va_arg(args,NSUInteger);assert(i<o->length);result=o->members[i];}
    else if(!strcmp(sel,"timerWithTimeInterval:repeats:block:")){
        assert(created<16);result=&timers[created++];result->cls="NSTimer";result->interval=va_arg(args,double);assert(va_arg(args,int));result->block=(struct Block *)va_arg(args,id);assert(result->interval==1.0 && result->block);
    }
    else if(!strcmp(sel,"setTolerance:")){o->tolerance=va_arg(args,double);assert(o->tolerance==0.25);}
    else if(!strcmp(sel,"mainRunLoop"))result=&runloop;
    else if(!strcmp(sel,"addTimer:forMode:")){id timer=va_arg(args,id),mode=va_arg(args,id);assert(timer==g_animation_timer && !strcmp(mode->value,"kCFRunLoopCommonModes"));}
    else if(!strcmp(sel,"invalidate")){assert(!o->invalid);o->invalid=YES;invalidated++;}
    else if(!strcmp(sel,"updateAnimationState")) { if(o->parent && !o->hidden && o->animation) { o->link->paused=NO;resumes++; } }
    else assert(!"unexpected animation selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id objc_retain(id o) { assert(!o || o==&weak_set || !strcmp(o->cls,"NSTimer"));return o; }
void objc_release(id o) { assert(!o || (o->invalid && !strcmp(o->cls,"NSTimer"))); }
float ss_test_opacity(id layer) { return layer->opacity; }
Rect ss_test_bounds(id layer) { return layer->bounds; }
Rect ss_test_projection(id layer,Rect bounds,id destination) { (void)bounds;assert(destination);return layer->projected; }
id objc_getAssociatedObject(id o,const void *k) { assert(k==&g_animation_key);return o->bound; }
void objc_setAssociatedObject(id o,const void *k,id value,uintptr_t policy) { assert(k==&g_animation_key && policy==1);o->bound=value; }
static void native_set(id o,SEL sel,id image) { (void)sel;set_calls++;if(o->animation!=image){o->animation=image;o->loops=3;o->link->paused=YES;} }
static void fire(id timer) { timer->block->invoke(timer->block,timer); }
int main(void) {
    struct Fake url={.cls="NSURL",.value="/emoticons/v2/900123456789012/default/dark/1.0"};
    struct Fake data={.cls="_TtC6Twitch22MessageStringImageData",.inner=&url};
    struct Fake animation={.cls="FLAnimatedImage"},replacement={.cls="FLAnimatedImage"},link={.cls="CADisplayLink",.paused=YES};
    struct Fake window_layer={.cls="CALayer",.opacity=1,.bounds={{0,0},{300,600}}},window={.cls="UIWindow",.inner=&window_layer,.bounds={{0,0},{300,600}}};
    struct Fake view={.cls="UIView",.window=&window},root={.cls="CALayer",.opacity=1,.parent=&window_layer,.delegate=&view};
    struct Fake layer={.cls="TWAnimatedImageLayer",.link=&link,.opacity=1,.bounds={{0,0},{28,28}},.projected={{10,10},{28,28}}};
    struct FakeAttachment attachment={.base={.cls="_TtC6Twitch20ImageAttachmentLayer",.opacity=1,.parent=&root},.data=&data,.animated=&layer};
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
    assert(created==1 && weak_set.length==0);fire(g_animation_timer);assert(!g_animation_timer && invalidated==1);
    animated_set_image(&layer,"setAnimatedImage:",&animation);assert(created==2 && weak_set.length==1);
    unsigned before=resumes,writes=set_calls;link.paused=YES;fire(g_animation_timer);
    assert(!link.paused && resumes==before+1 && set_calls==writes); /* No layout/image event required; no decoder reset. */
    NSUInteger before_bindings=bindings;layer.loops=0;link.paused=YES;fire(g_animation_timer);
    assert(layer.loops==UINT64_MAX && !link.paused && bindings==before_bindings+1 && set_calls==writes);
    before=resumes;root.hidden=YES;link.paused=YES;provider_animation((id)&attachment);assert(link.paused && resumes==before);fire(g_animation_timer);
    assert(link.paused && resumes==before && !g_animation_timer);
    root.hidden=NO;provider_animation((id)&attachment);assert(g_animation_timer && !link.paused);
    layer.projected.origin.y=700;link.paused=YES;before=resumes;fire(g_animation_timer);
    assert(link.paused && resumes==before && !g_animation_timer); /* Offscreen viewport. */
    layer.projected.origin.y=10;provider_animation((id)&attachment);
    root.clips=YES;root.bounds=(Rect){{0,0},{5,5}};link.paused=YES;before=resumes;fire(g_animation_timer);
    assert(link.paused && resumes==before && !g_animation_timer); /* Inside window but outside chat viewport. */
    root.clips=NO;provider_animation((id)&attachment);
    root.opacity=0;link.paused=YES;before=resumes;fire(g_animation_timer);
    assert(link.paused && resumes==before && !g_animation_timer);
    root.opacity=1;provider_animation((id)&attachment);
    app_state=2;link.paused=YES;before=resumes;fire(g_animation_timer);assert(link.paused && resumes==before && !g_animation_timer);
    app_state=0;animation_check(nil);assert(!link.paused && g_animation_timer); /* Existing foreground callback restarts recovery. */
    before=resumes;view.window=nil;link.paused=YES;fire(g_animation_timer);assert(link.paused && resumes==before && !g_animation_timer);
    view.window=&window;animation_check(nil);assert(g_animation_timer && !link.paused);
    layer.parent=nil;link.paused=YES;before=resumes;fire(g_animation_timer);
    assert(!g_animation_timer && resumes==before && weak_set.length==1); /* Weak entry survives detach. */
    layer.parent=(id)&attachment;animation_check(nil);assert(g_animation_timer && !link.paused);
    url.value="/emoticons/v2/25/default/dark/1.0";layer.loops=3;link.paused=YES;before=resumes;fire(g_animation_timer);
    assert(!g_animation_timer && weak_set.length==0 && layer.loops==3 && link.paused && resumes==before);
    url.value="/emoticons/v2/900123456789012/default/dark/1.0";provider_animation((id)&attachment);id stale=g_animation_timer;
    weak_set.length=0;fire(stale);assert(!g_animation_timer);before=resumes;fire(stale);assert(resumes==before); /* Weak deallocation and stale timer. */
    return 0;
}
'''


PLAYBACK_MAIN = r"""
static void test_probe_fire(struct Block *block,id timer) { (void)block;probe_sample_all(timer); }
static struct Block test_probe_block={.invoke=test_probe_fire};
id ss_test_probe_block(void) { return (id)&test_probe_block; }
static uint64_t test_generation=1;
static unsigned samples,refresh_calls,static_calls,remove_calls,stop_calls,quiet_events,progress_events;
static unsigned released_events,eviction_events,denial_events,image_events;
static char playback[512];
static char assignment[512];
uint64_t tas_emote_probe_generation(uint64_t number) { return number==900123456789012ULL ? test_generation : 0; }
void tas_emote_probe_playback(uint64_t generation,uint64_t number,const char *state) {
    assert(generation==test_generation && number==900123456789012ULL);
    samples++;snprintf(playback,sizeof(playback),"%s",state);
}
void tas_emote_probe_record(uint64_t number,unsigned layer,const char *event,const char *state,bool visible) {
    assert(number==900123456789012ULL);(void)layer;(void)visible;
    samples++;snprintf(playback,sizeof(playback),"%s",state);
    if (!strcmp(event,"no-frame-change-3s") || !strcmp(event,"no-refresh-3s")) quiet_events++;
    if (!strcmp(event,"last-frame-progress")) { progress_events++;assert(strstr(state,"advances=")); }
    if (!strcmp(event,"layer-released")) released_events++;
    if (!strcmp(event,"tracking-evicted")) { eviction_events++;assert(strstr(state,"weak-layer=live")); }
    if (!strcmp(event,"tracking-limited")) { denial_events++;assert(!layer && strstr(state,"reason=capacity")); }
}
void tas_emote_probe_image(uint64_t number,unsigned layer,const char *event,const char *state) {
    assert(number==900123456789012ULL);(void)layer;(void)event;image_events++;snprintf(assignment,sizeof(assignment),"%s",state);
}
void tas_emote_probe_stage(uint64_t number,const char *stage) { (void)number; (void)stage; }
static void native_refresh(id o,SEL sel,id link) {
    assert(!strcmp(sel,"displayDidRefresh:") && link==o->link); refresh_calls++;
    if (!link->paused && o->advance) o->index=(o->index+1)%4;
}
static void native_static(id o,SEL sel,id image) {
    assert(!strcmp(sel,"setStaticImage:"));static_calls++;
    o->animation=nil;o->inner=image;o->link->paused=YES;
}
static void native_remove(id o,SEL sel) {
    assert(!strcmp(sel,"removeFromSuperlayer"));remove_calls++;
    o->parent=nil;o->link->paused=YES;
}
static void native_stop(id o,SEL sel) { assert(!strcmp(sel,"stopAnimating"));stop_calls++;o->link->paused=YES; }
int main(void) {
    struct Fake url={.cls="NSURL",.value="/emoticons/v2/900123456789012/default/dark/1.0"};
    struct Fake data={.cls="_TtC6Twitch22MessageStringImageData",.inner=&url};
    struct Fake animation={.cls="FLAnimatedImage",.length=4},link={.cls="CADisplayLink"};
    struct Fake window_layer={.cls="CALayer",.opacity=1,.bounds={{0,0},{300,600}}},window={.cls="UIWindow",.inner=&window_layer};
    struct Fake view={.cls="UIView",.window=&window},root={.cls="CALayer",.opacity=1,.parent=&window_layer,.delegate=&view};
    struct Fake layer={.cls="TWAnimatedImageLayer",.animation=&animation,.inner=&animation,.link=&link,.opacity=1,
        .advance=YES,.loops=UINT64_MAX,.bounds={{0,0},{28,28}},.projected={{10,10},{28,28}}};
    struct FakeAttachment attachment={.base={.cls="_TtC6Twitch20ImageAttachmentLayer",.opacity=1,.parent=&root},.data=&data,.animated=&layer};
    (void)native_set;
    layer.parent=(id)&attachment;g_probe_refresh=(IMP)native_refresh;
    /* The animation is already cached; starting tracing must not need setter/layout events. */
    g_animation_layers=&weak_set;weak_set.members[0]=&layer;weak_set.length=1;
    tas_emote_ui_probe_start(); assert(samples==2 && strstr(playback,"ticks=0 advances=0"));
    assert(strstr(playback,"frames=4") && strstr(playback,"contents=1") && strstr(playback,"visibility=visible"));
    assert(strstr(playback,"role=animated") && strstr(playback,"animated-child=visible"));
    assert(!bindings && !resumes && !set_calls);
    for (int i=0;i<4;i++) probe_display_refresh(&layer,"displayDidRefresh:",&link);
    fire(g_probe_timer); assert(refresh_calls==4 && layer.index==0);
    assert(strstr(playback,"ticks=4 advances=4 index=0")); /* Full loop does not alias as stalled. */
    layer.advance=NO;
    for (int i=0;i<3;i++) probe_display_refresh(&layer,"displayDidRefresh:",&link);
    fire(g_probe_timer); assert(strstr(playback,"ticks=7 advances=4"));
    g_probe_playheads[0].last_advance-=4;fire(g_probe_timer);
    assert(quiet_events==1 && progress_events==1);fire(g_probe_timer);assert(quiet_events==1);
    link.paused=YES;fire(g_probe_timer);assert(strstr(playback,"link=paused") && strstr(playback,"gate=resume-eligible") && link.paused);
    layer.link=nil;fire(g_probe_timer);assert(strstr(playback,"link=missing") && strstr(playback,"gate=no-link") && !layer.link);
    root.hidden=YES;fire(g_probe_timer);assert(strstr(playback,"visibility=hidden"));root.hidden=NO;
    app_state=2;fire(g_probe_timer);assert(strstr(playback,"visibility=background"));app_state=0;
    layer.parent=nil;fire(g_probe_timer);assert(strstr(playback,"visibility=detached"));layer.parent=(id)&attachment;
    layer.projected.origin.y=700;fire(g_probe_timer);assert(strstr(playback,"visibility=offscreen"));layer.projected.origin.y=10;
    url.value="/emoticons/v2/25/default/dark/1.0";unsigned before=samples;fire(g_probe_timer);assert(samples==before && !g_probe_playheads[0].layer);
    url.value="/emoticons/v2/900123456789012/default/dark/1.0";fire(g_probe_timer);assert(samples==before+2);
    layer.link=&link;probe_display_refresh(&layer,"displayDidRefresh:",&link);fire(g_probe_timer);
    id same=g_probe_timer;before=samples;test_generation++;tas_emote_ui_probe_start();
    assert(g_probe_timer==same && samples==before && strstr(playback,"ticks=1")); /* Selection never resets. */
    layer.link=&link;g_probe_static=(IMP)native_static;g_probe_remove=(IMP)native_remove;
    g_probe_stop=(IMP)native_stop;probe_stop_animation(&layer,"stopAnimating");assert(stop_calls==1 && link.paused);
    probe_static_image(&layer,"setStaticImage:",&animation);
    assert(static_calls==1 && !layer.animation && link.paused && strstr(playback,"animation=0"));
    assert(image_events==2 && strstr(assignment,"resident-animation=0"));
    assert(strstr(playback,"ticks=1")); /* Clearing an image does not reset cumulative clocks. */
    probe_remove_layer(&layer,"removeFromSuperlayer");assert(remove_calls==1 && !layer.parent);
    assert(strstr(playback,"visibility=detached"));
    g_probe_started.tv_sec-=600;fire(g_probe_timer);assert(g_probe_timer); /* Rolling, not ten minutes after selection. */
    weak_set.length=0;id stale=g_probe_timer;fire(stale);assert(!g_probe_playheads[0].layer && !g_probe_timer && stale->invalid);
    assert(strstr(playback,"weak-layer=gone"));before=samples;fire(stale);assert(samples==before);
    /* A static child is identified by the actual field, even if its class
     * also implements the native animation selectors. Detach preserves role. */
    struct Fake still=layer; still.parent=(id)&attachment;still.inner=&animation;
    attachment.still=&still;probe_snapshot(&still,"static-child-test");
    assert(strstr(playback,"role=static") && strstr(playback,"static-child=visible"));
    still.parent=nil;probe_snapshot(&still,"detached-test");assert(strstr(playback,"role=static"));
    weak_set.length=0;probe_reap(m0(g_probe_layers,"allObjects"));
    /* 64 live visible layers: no free observation identity may be fabricated
     * for a denied 65th layer or later reported as released. */
    struct Fake busy[64];
    for (unsigned i=0;i<64;i++) { busy[i]=layer;busy[i].parent=(id)&attachment;probe_snapshot(&busy[i],"busy-test"); }
    assert(weak_set.length==64);
    unsigned released_before=released_events;before=denial_events;
    probe_snapshot(&still,"denied-test"); /* Detached, not eligible. */
    still.parent=(id)&attachment;probe_snapshot(&still,"denied-test");
    assert(denial_events==before+1 && g_probe_dropped && weak_set.length==64);
    probe_sample_all(nil);assert(released_events==released_before);
    for (unsigned i=0;i<64;i++) assert(g_probe_playheads[i].layer!=&still);
    /* A new visible static child replaces a live hidden observer, explicitly
     * reporting eviction; its native image setter still runs exactly once. */
    busy[0].hidden=YES;before=eviction_events;
    probe_static_image(&still,"setStaticImage:",&animation);
    assert(static_calls==2 && eviction_events==before+1 && g_probe_evicted==1 && weak_set.length==64);
    assert(released_events==released_before && strstr(assignment,"role=static") && strstr(assignment,"tracking=admitted"));
    assert(!bindings && !resumes && !set_calls); /* Every read is observational. */
    return 0;
}
"""


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
        source=(ROOT/"src"/"TASEmoteUI.c").read_text()
        source=source.replace('((float (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("opacity"))','ss_test_opacity(ancestor)')
        for name in ('layer','target'):
            source=source.replace(f'((Rect (*)(id,SEL))objc_msgSend)({name},sel_registerName("bounds"))',f'ss_test_bounds({name})')
        source=source.replace('((Rect (*)(id,SEL,Rect,id))objc_msgSend)(layer,sel_registerName("convertRect:toLayer:"),bounds,target)','ss_test_projection(layer,bounds,target)')
        source=source.replace('((id (*)(id,SEL,double,BOOL,id))objc_msgSend)','((id (*)(id,SEL,...))objc_msgSend)')
        source=source.replace('static void animation_check(id timer);','extern float ss_test_opacity(id);\nextern Rect ss_test_bounds(id);\nextern Rect ss_test_projection(id,Rect,id);\nstatic void animation_check(id timer);')
        test_composer.ComposerTests().compile_run(ANIMATIONS.replace('#include "TASEmoteUI.c"',source),[zig,"cc","-fblocks","-fsanitize=address,undefined"],runtime=True)


    def test_selected_playback_samples_cached_layers_clocks_wraps_and_missing_links(self):
        zig=os.environ.get("ZIG") or shutil.which("zig");self.assertTrue(zig)
        source=(ROOT/"src"/"TASEmoteUI.c").read_text()
        source=source.replace('((float (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("opacity"))','ss_test_opacity(ancestor)')
        for name in ('layer','target'):
            source=source.replace(f'((Rect (*)(id,SEL))objc_msgSend)({name},sel_registerName("bounds"))',f'ss_test_bounds({name})')
        source=source.replace('((Rect (*)(id,SEL,Rect,id))objc_msgSend)(layer,sel_registerName("convertRect:toLayer:"),bounds,target)','ss_test_projection(layer,bounds,target)')
        source=source.replace('((id (*)(id,SEL,double,BOOL,id))objc_msgSend)','((id (*)(id,SEL,...))objc_msgSend)')
        source=source.replace('static void animation_check(id timer);','extern float ss_test_opacity(id);\nextern Rect ss_test_bounds(id);\nextern Rect ss_test_projection(id,Rect,id);\nstatic void animation_check(id timer);')
        # Adapt only NSTimer's block packaging: Zig's host backend cannot emit
        # a global block in this externally visible C entry point. The iOS
        # artifact compiles the real block; its callback body is exercised here.
        source=source.replace('(id)^(id fired) { probe_sample_all(fired); }','ss_test_probe_block()')
        source=source.replace('void tas_emote_ui_probe_start(void) {','extern id ss_test_probe_block(void);\nvoid tas_emote_ui_probe_start(void) {')
        harness=ANIMATIONS[:ANIMATIONS.index('int main(void) {')]+PLAYBACK_MAIN
        harness=harness.replace('BOOL hidden,paused,invalid,clips;', 'BOOL hidden,paused,invalid,clips,advance; NSUInteger index;')
        harness=harness.replace('else if(!strcmp(sel,"displayLink"))', 'else if(!strcmp(sel,"currentFrame"))result=o->inner;\n    else if(!strcmp(sel,"contents"))result=o->inner;\n    else if(!strcmp(sel,"images"))result=nil;\n    else if(!strcmp(sel,"currentFrameIndex"))result=(id)(uintptr_t)o->index;\n    else if(!strcmp(sel,"frameCount"))result=(id)(uintptr_t)o->length;\n    else if(!strcmp(sel,"shouldAnimate"))result=(id)(uintptr_t)YES;\n    else if(!strcmp(sel,"needsDisplayUpdate"))result=nil;\n    else if(!strcmp(sel,"displayLink"))')
        harness=harness.replace('timer==g_animation_timer', '(timer==g_animation_timer || timer==g_probe_timer)')
        harness=harness.replace('assert(!o || (o->invalid && !strcmp(o->cls,"NSTimer")))', 'assert(!o || o==&weak_set || (o->invalid && !strcmp(o->cls,"NSTimer")))')
        # The shared fake weak table models already live rows; no objects are retained by it.
        harness=harness.replace('#include "TASEmoteUI.c"',source)
        test_composer.ComposerTests().compile_run(harness,[zig,"cc","-fblocks","-DTAS_EMOTE_DIAGNOSTIC=1","-fsanitize=address,undefined"],runtime=True)


if __name__=="__main__":unittest.main()
