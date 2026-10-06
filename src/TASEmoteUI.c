/* Optional UIKit integration. All hooks are scoped to Twitch's emote/chat
 * classes and synthetic IDs; installation is gated by the launch preference. */
#include "TASEmoteUI.h"
#include "TASEmotes.h"
#include "TASEmoteGeometry.h"
#include "TASEmoteProbe.h"
#include "TASEmoteImageProbe.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#if TAS_EMOTE_DIAGNOSTIC
#include <time.h>
static IMP g_probe_refresh, g_probe_static, g_probe_remove, g_probe_stop;
static id g_probe_timer, g_probe_layers;
static unsigned g_probe_layer_serial;
static uint64_t g_probe_polls, g_probe_dropped, g_probe_evicted;
static time_t g_probe_last_poll;
static struct timespec g_probe_started;
static struct {
    id layer, animation, frame; /* Identity only; never retained or dereferenced here. */
    uint64_t number, refreshes, advances, index;
    unsigned serial;
    char role[12];
    char signature[160];
    time_t last_tick, last_advance;
    uint64_t observed_ticks, observed_advances;
    BOOL quiet_reported, was_visible;
} g_probe_playheads[64];
#endif

typedef unsigned long NSUInteger;
typedef long NSInteger;
typedef double CGFloat;
typedef struct { CGFloat x, y; } Point;
typedef struct { CGFloat width, height; } Size;
typedef struct { Point origin; Size size; } Rect;
typedef struct { NSUInteger location, length; } Range;
typedef struct { CGFloat top, left, bottom, right; } Insets;
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_getAssociatedObject(id, const void *);
extern void objc_setAssociatedObject(id, const void *, id, uintptr_t);
static IMP g_receive, g_size, g_base_size, g_bounds, g_set_bounds, g_textkit_bounds, g_chat_textkit_bounds, g_layer_frame, g_layer_layout, g_tap;
static IMP g_animated_image;
static Class g_details_class;
static char g_metadata_key, g_snapshot_message_key, g_details_dismissing_key;
static char g_animation_key;
static id g_animation_layers, g_animation_timer; /* weak members; one idle-stopping timer */
static uint64_t g_receive_calls, g_sent_calls, g_sent_matches, g_sized, g_details, g_tap_calls, g_snapshots, g_tap_hits;
static uint64_t g_size_calls, g_bounds_calls, g_textkit_calls, g_resolved_ids;
static uint64_t g_layer_calls, g_layer_ids, g_layer_resizes, g_layer_layouts;
static uint64_t g_animation_loops, g_animation_resumes;
static uint64_t g_animation_checks;
#define INC(x) ((void)__atomic_add_fetch(&(x), 1, __ATOMIC_RELAXED))
#define GET(x) __atomic_load_n(&(x), __ATOMIC_RELAXED)
static id m0(id o, const char *s) { return ((id (*)(id,SEL))objc_msgSend)(o, sel_registerName(s)); }
static id m1(id o, const char *s, id a) { return ((id (*)(id,SEL,id))objc_msgSend)(o, sel_registerName(s), a); }
static void v1(id o, const char *s, id a) { ((void (*)(id,SEL,id))objc_msgSend)(o, sel_registerName(s), a); }
static id string(const char *s) { return m1((id)objc_getClass("NSString"),"stringWithUTF8String:",(id)s); }
static BOOL responds(id o, const char *s) { return o && ((BOOL (*)(id,SEL,SEL))objc_msgSend)(o,sel_registerName("respondsToSelector:"),sel_registerName(s)); }
static BOOL kind(id o, const char *c) { return o && ((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),objc_getClass(c)); }
static NSUInteger count(id o) { return ((NSUInteger (*)(id,SEL))objc_msgSend)(o,sel_registerName("count")); }
static id at(id o, NSUInteger i) { return ((id (*)(id,SEL,NSUInteger))objc_msgSend)(o,sel_registerName("objectAtIndex:"),i); }
static id key(id o, const char *k) { return kind(o,"NSDictionary") ? m1(o,"objectForKey:",string(k)) : nil; }
/* Resolve offsets by name at runtime, never rely on the inspected app's offsets. */
static id object_ivar(id o, const char *name) {
    Ivar ivar = o ? class_getInstanceVariable(object_getClass(o),name) : NULL;
    if (!ivar) return nil;
    id result = nil; memcpy(&result,(char *)o + ivar_getOffset(ivar),sizeof(result));
    return result;
}
static uint64_t synthetic_id(id value) {
    /* Twitch stores TWMessageEmoteToken objects in emoteLocationsMap. Read
     * their exported getter; their ivars contain Swift strings, not objects. */
    if (responds(value,"emoteId")) value = m0(value,"emoteId");
    if (!kind(value,"NSString") && !kind(value,"NSNumber")) return 0;
    const char *s = ((const char *(*)(id,SEL))objc_msgSend)(m0(value,"description"),sel_registerName("UTF8String"));
    if (!s || *s != '9') return 0;
    char *end; uint64_t number = strtoull(s,&end,10);
    return !*end && number >= 9000000000ULL ? number : 0;
}
static uint64_t url_id(id url) {
    if (!responds(url,"host") || !responds(url,"path")) return 0;
    id host = m0(url,"host");
    if (!((BOOL (*)(id,SEL,id))objc_msgSend)(host,sel_registerName("isEqualToString:"),string("static-cdn.jtvnw.net"))) return 0;
    const char *path = ((const char *(*)(id,SEL))objc_msgSend)(m0(url,"path"),sel_registerName("UTF8String"));
    const char *prefix = "/emoticons/v2/";
    if (!path || strncmp(path,prefix,strlen(prefix))) return 0;
    char *end; uint64_t number = strtoull(path+strlen(prefix),&end,10);
    return *end == '/' && number >= 9000000000ULL ? number : 0;
}
static uint64_t attachment_id(id attachment) {
    if (!responds(attachment,"imageData")) return 0;
    id data = m0(attachment,"imageData");
    return responds(data,"staticURL") ? url_id(m0(data,"staticURL")) : 0;
}
/* The inspected ImageAttachmentLayer.content stores (CGRect,
 * MessageStringImageData). Its native description and frame setter confirm
 * the strong object field after CGRect. Resolve both ivars at runtime and
 * require their complete tuple span before reading the object field. */
static uint64_t image_layer_id(id layer) {
    if (!kind(layer,"_TtC6Twitch20ImageAttachmentLayer")) return 0;
    Class cls = object_getClass(layer);
    Ivar content = class_getInstanceVariable(cls,"content");
    Ivar next = class_getInstanceVariable(cls,"networkImageRequester");
    if (!content || !next || ivar_getOffset(next) - ivar_getOffset(content) != (ptrdiff_t)(sizeof(Rect) + sizeof(id))) return 0;
    id data = nil;
    memcpy(&data,(char *)layer + ivar_getOffset(content) + sizeof(Rect),sizeof(data));
    if (!kind(data,"_TtC6Twitch22MessageStringImageData") || !responds(data,"staticURL")) return 0;
    uint64_t number = url_id(m0(data,"staticURL"));
    if (!number && responds(data,"animatedURL")) number = url_id(m0(data,"animatedURL"));
    return number;
}

static void animation_check(id timer);
static BOOL animation_intersects(id layer,id target) {
    Rect bounds=((Rect (*)(id,SEL))objc_msgSend)(layer,sel_registerName("bounds"));
    Rect projected=((Rect (*)(id,SEL,Rect,id))objc_msgSend)(layer,sel_registerName("convertRect:toLayer:"),bounds,target);
    Rect viewport=((Rect (*)(id,SEL))objc_msgSend)(target,sel_registerName("bounds"));
    return projected.size.width>0 && projected.size.height>0 &&
        projected.origin.x<viewport.origin.x+viewport.size.width && projected.origin.y<viewport.origin.y+viewport.size.height &&
        projected.origin.x+projected.size.width>viewport.origin.x && projected.origin.y+projected.size.height>viewport.origin.y;
}
static BOOL animation_visible(id layer) {
    id application=m0((id)objc_getClass("UIApplication"),"sharedApplication");
    if (((NSInteger (*)(id,SEL))objc_msgSend)(application,sel_registerName("applicationState"))!=0) return NO;
    id window=nil,ancestor=layer;
    for (unsigned depth=0;ancestor && depth<64;depth++,ancestor=m0(ancestor,"superlayer")) {
        if (((BOOL (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("isHidden")) ||
            !(((float (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("opacity"))>0)) return NO;
        if (((BOOL (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("masksToBounds")) && !animation_intersects(layer,ancestor)) return NO;
        id delegate=m0(ancestor,"delegate");
        if (kind(delegate,"UIView")) window=m0(delegate,"window") ?: window;
    }
    if (ancestor || !window || ((BOOL (*)(id,SEL))objc_msgSend)(window,sel_registerName("isHidden"))) return NO;
    return animation_intersects(layer,m0(window,"layer"));
}
#if TAS_EMOTE_DIAGNOSTIC
/* Read-only reasons mirror the existing recovery visibility gate. These
 * observations never decide whether to start/resume an animation. */
static const char *probe_visibility(id layer) {
    id app=m0((id)objc_getClass("UIApplication"),"sharedApplication");
    if (((NSInteger (*)(id,SEL))objc_msgSend)(app,sel_registerName("applicationState"))) return "background";
    if (!layer || !m0(layer,"superlayer")) return "detached";
    id window=nil,ancestor=layer;
    for (unsigned depth=0;ancestor && depth<64;depth++,ancestor=m0(ancestor,"superlayer")) {
        if (((BOOL (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("isHidden"))) return "hidden";
        if (!(((float (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("opacity"))>0)) return "transparent";
        if (((BOOL (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("masksToBounds")) && !animation_intersects(layer,ancestor)) return "clipped";
        id delegate=m0(ancestor,"delegate");
        if (kind(delegate,"UIView")) window=m0(delegate,"window") ?: window;
    }
    if (ancestor) return "depth-limit";
    if (!window) return "no-window";
    if (((BOOL (*)(id,SEL))objc_msgSend)(window,sel_registerName("isHidden"))) return "window-hidden";
    return animation_intersects(layer,m0(window,"layer")) ? "visible" : "offscreen";
}
static uint64_t probe_integer(id object,const char *selector) {
    return responds(object,selector) ? ((NSUInteger (*)(id,SEL))objc_msgSend)(object,sel_registerName(selector)) : 0;
}
static int probe_flag(id object,const char *selector) {
    return responds(object,selector) ? ((BOOL (*)(id,SEL))objc_msgSend)(object,sel_registerName(selector)) : -1;
}
static id probe_image_data(id attachment) {
    if (!kind(attachment,"_TtC6Twitch20ImageAttachmentLayer")) return nil;
    Class cls=object_getClass(attachment);
    Ivar content=class_getInstanceVariable(cls,"content"),next=class_getInstanceVariable(cls,"networkImageRequester");
    if (!content || !next || ivar_getOffset(next)-ivar_getOffset(content)!=(ptrdiff_t)(sizeof(Rect)+sizeof(id))) return nil;
    id data=nil; memcpy(&data,(char *)attachment+ivar_getOffset(content)+sizeof(Rect),sizeof(data));
    return kind(data,"_TtC6Twitch22MessageStringImageData") ? data : nil;
}
static int probe_mode(id attachment) {
    if (!kind(attachment,"_TtC6Twitch20ImageAttachmentLayer")) return -1;
    Class cls=object_getClass(attachment); Ivar mode=class_getInstanceVariable(cls,"currentDisplayMode"),next=class_getInstanceVariable(cls,"animatedImageLayer");
    if (!mode || !next || ivar_getOffset(next)-ivar_getOffset(mode)!=8) return -1;
    unsigned char value; memcpy(&value,(char *)attachment+ivar_getOffset(mode),1); return value<=2 ? value : -1;
}
static void probe_intent(id attachment,id input,char *buffer,size_t capacity) {
    id data=probe_image_data(attachment); char provenance[256]; tas_image_probe_origin(input,provenance,sizeof(provenance));
    snprintf(buffer,capacity,"mode=%d wants-animation=%d animated-url=%d %s",probe_mode(attachment),probe_flag(data,"isAnimated"),responds(data,"animatedURL") ? m0(data,"animatedURL")!=nil : -1,provenance);
}
static const char *probe_role(id layer) {
    id parent=m0(layer,"superlayer");
    if (!kind(parent,"_TtC6Twitch20ImageAttachmentLayer")) return "unknown";
    if (layer==object_ivar(parent,"animatedImageLayer")) return "animated";
    if (layer==object_ivar(parent,"staticImageLayer")) return "static";
    return "unknown";
}
static BOOL probe_contains(id layers,id layer) {
    for (NSUInteger i=0,n=count(layers);i<n;i++) if (at(layers,i)==layer) return YES;
    return NO;
}
static void probe_reap(id layers) {
    for (unsigned s=0;s<64;s++) {
        if (!g_probe_playheads[s].layer || probe_contains(layers,g_probe_playheads[s].layer)) continue;
        char state[80]; snprintf(state,sizeof(state),"layer=%u role=%s weak-layer=gone",g_probe_playheads[s].serial,g_probe_playheads[s].role);
        tas_emote_probe_record(g_probe_playheads[s].number,g_probe_playheads[s].serial,"layer-released",state,false);
        memset(&g_probe_playheads[s],0,sizeof(g_probe_playheads[s]));
    }
}
static BOOL probe_track(id layer) {
    if (!g_probe_layers) {
        g_probe_layers=objc_retain(m0((id)objc_getClass("NSHashTable"),"weakObjectsHashTable"));
        clock_gettime(CLOCK_MONOTONIC,&g_probe_started);
    }
    uint64_t number=layer ? image_layer_id(m0(layer,"superlayer")) : 0;
    if (!g_probe_layers || !number) return NO;
    id layers=m0(g_probe_layers,"allObjects");
    if (probe_contains(layers,layer)) return YES;
    probe_reap(layers); /* Never allocate an identity for an unadmitted layer. */
    if (count(layers)>=64) {
        /* Newly visible layers can replace live hidden/offscreen observations.
         * This is recorder eviction, never evidence of object deallocation. */
        id victim=nil;
        if (!strcmp(probe_visibility(layer),"visible")) for (NSUInteger i=0,n=count(layers);i<n;i++) {
            id candidate=at(layers,i);
            if (strcmp(probe_visibility(candidate),"visible")) { victim=candidate; break; }
        }
        if (!victim) {
            g_probe_dropped++;
            char state[96]; snprintf(state,sizeof(state),"layer=untracked role=%s reason=capacity limit=64",probe_role(layer));
            tas_emote_probe_record(number,0,"tracking-limited",state,false);
            return NO;
        }
        for (unsigned s=0;s<64;s++) if (g_probe_playheads[s].layer==victim) {
            char state[96]; snprintf(state,sizeof(state),"layer=%u role=%s reason=visible-priority weak-layer=live",g_probe_playheads[s].serial,g_probe_playheads[s].role);
            tas_emote_probe_record(g_probe_playheads[s].number,g_probe_playheads[s].serial,"tracking-evicted",state,false);
            memset(&g_probe_playheads[s],0,sizeof(g_probe_playheads[s])); break;
        }
        v1(g_probe_layers,"removeObject:",victim); g_probe_evicted++;
    }
    v1(g_probe_layers,"addObject:",layer);
    return YES;
}
static void probe_snapshot(id layer,const char *event) {
    uint64_t number=image_layer_id(m0(layer,"superlayer"));
    unsigned slot=64;
    for (unsigned i=0;i<64;i++) if (g_probe_playheads[i].layer==layer) { slot=i; break; }
    /* Detached layers retain only their numeric identity; the weak table
     * supplies the live object. Reuse in another attachment invalidates it. */
    if (!number && !m0(layer,"superlayer") && slot<64) {
        number=g_probe_playheads[slot].number;
    }
    if (!number) {
        if (slot<64) memset(&g_probe_playheads[slot],0,sizeof(g_probe_playheads[slot]));
        return;
    }
    if (slot==64 && !probe_track(layer)) return;
    if (slot==64) for (unsigned i=0;i<64;i++) if (!g_probe_playheads[i].layer) { slot=i; break; }
    if (slot==64) return; /* Fixed observation budget, never an unbounded map. */
    id image=m0(layer,"animatedImage"),frame=m0(layer,"currentFrame");
    uint64_t index=probe_integer(layer,"currentFrameIndex");
    if (g_probe_playheads[slot].number!=number) {
        memset(&g_probe_playheads[slot],0,sizeof(g_probe_playheads[slot]));
        g_probe_playheads[slot].layer=layer; g_probe_playheads[slot].number=number;
        g_probe_playheads[slot].serial=++g_probe_layer_serial;
    }
    if (m0(layer,"superlayer")) snprintf(g_probe_playheads[slot].role,sizeof(g_probe_playheads[slot].role),"%s",probe_role(layer));
    /* Keep lifetime counters across image clearing/replacement. Refresh
     * baselines change, but prior ticks must not disappear with the image. */
    BOOL image_changed=g_probe_playheads[slot].animation!=image;
    g_probe_playheads[slot].animation=image;
    g_probe_playheads[slot].frame=frame; g_probe_playheads[slot].index=index;
    id link=m0(layer,"displayLink");
    const char *visibility=probe_visibility(layer);
    int paused=probe_flag(link,"isPaused");
    const char *gate=!image ? "no-animation" : strcmp(visibility,"visible") ? "invisible" :
        !link ? "no-link" : paused==1 ? "resume-eligible" : paused==0 ? "running-link" : "unknown-link";
    struct timespec now; clock_gettime(CLOCK_MONOTONIC,&now);
    unsigned elapsed=(unsigned)(now.tv_sec-g_probe_started.tv_sec);
    id parent=m0(layer,"superlayer");
    id sibling=kind(parent,"_TtC6Twitch20ImageAttachmentLayer") ? object_ivar(parent,"staticImageLayer") : nil;
    const char *static_visibility=kind(sibling,"CALayer") ? probe_visibility(sibling) : "unavailable";
    id animated=kind(parent,"_TtC6Twitch20ImageAttachmentLayer") ? object_ivar(parent,"animatedImageLayer") : nil;
    const char *animated_visibility=kind(animated,"CALayer") ? probe_visibility(animated) : "unavailable";
    char state[768],intent[320]; probe_intent(parent,image ?: frame,intent,sizeof(intent));
    snprintf(state,sizeof(state),"t=%u layer=%u role=%s refresh=%s ticks=%llu advances=%llu index=%llu frames=%llu animation=%d frame=%d contents=%d link=%s should=%d dirty=%d loops=%llu visibility=%s gate=%s animated-child=%s static-child=%s %s",
        elapsed,g_probe_playheads[slot].serial,g_probe_playheads[slot].role,g_probe_refresh ? "hooked" : "missing",
        (unsigned long long)g_probe_playheads[slot].refreshes,(unsigned long long)g_probe_playheads[slot].advances,
        (unsigned long long)index,(unsigned long long)probe_integer(image,"frameCount"),image!=nil,frame!=nil,m0(layer,"contents")!=nil,
        !link ? "missing" : paused==1 ? "paused" : paused==0 ? "running" : "unknown",
        probe_flag(layer,"shouldAnimate"),probe_flag(layer,"needsDisplayUpdate"),
        (unsigned long long)probe_integer(layer,"loopCountdown"),visibility,gate,animated_visibility,static_visibility,intent);
    char signature[160];
    snprintf(signature,sizeof(signature),"%d/%d/%d/%d/%s/%s/%s/%s/%s",image!=nil,frame!=nil,paused,
        probe_flag(layer,"shouldAnimate"),visibility,gate,g_probe_playheads[slot].role,animated_visibility,static_visibility);
    BOOL visible=!strcmp(visibility,"visible");
    /* Preserve the previous progressing state when clocks go quiet. This is
     * evidence, not a freeze verdict: long frame holds can also trigger it. */
    if (image_changed || !visible || !g_probe_playheads[slot].was_visible) {
        g_probe_playheads[slot].last_tick=g_probe_playheads[slot].last_advance=now.tv_sec;
        g_probe_playheads[slot].quiet_reported=NO;
    }
    if (g_probe_playheads[slot].refreshes!=g_probe_playheads[slot].observed_ticks) g_probe_playheads[slot].last_tick=now.tv_sec;
    if (g_probe_playheads[slot].advances!=g_probe_playheads[slot].observed_advances) {
        g_probe_playheads[slot].last_advance=now.tv_sec; g_probe_playheads[slot].quiet_reported=NO;
        if (visible && image) {
            tas_emote_probe_record(number,g_probe_playheads[slot].serial,"last-frame-progress",state,false);
        }
    }
    g_probe_playheads[slot].observed_ticks=g_probe_playheads[slot].refreshes;
    g_probe_playheads[slot].observed_advances=g_probe_playheads[slot].advances;
    g_probe_playheads[slot].was_visible=visible;
    if (!strcmp(event,"sample")) {
        if (visible && image && link && paused==0 && probe_integer(image,"frameCount")>1 &&
            now.tv_sec-g_probe_playheads[slot].last_advance>=3 && !g_probe_playheads[slot].quiet_reported) {
            tas_emote_probe_record(number,g_probe_playheads[slot].serial,
                now.tv_sec-g_probe_playheads[slot].last_tick>=3 ? "no-refresh-3s" : "no-frame-change-3s",state,false);
            g_probe_playheads[slot].quiet_reported=YES;
        }
        if (image_changed || strcmp(signature,g_probe_playheads[slot].signature))
            tas_emote_probe_record(number,g_probe_playheads[slot].serial,"state-change",state,visible);
        /* Hidden-row polling cannot evict a useful visible checkpoint. */
        if (visible) tas_emote_probe_record(number,g_probe_playheads[slot].serial,event,state,true);
    } else tas_emote_probe_record(number,g_probe_playheads[slot].serial,event,state,visible);
    snprintf(g_probe_playheads[slot].signature,sizeof(g_probe_playheads[slot].signature),"%s",signature);
}
static void probe_sample_all(id timer) {
    if (timer && timer!=g_probe_timer) return;
    id layers=m0(g_probe_layers,"allObjects");
    struct timespec now; clock_gettime(CLOCK_MONOTONIC,&now);
    g_probe_polls++; g_probe_last_poll=now.tv_sec;
    probe_reap(layers);
    for (NSUInteger i=0,n=count(layers);i<n;i++) probe_snapshot(at(layers,i),"sample");
    if (timer && !count(layers)) {
        id finished=g_probe_timer; g_probe_timer=nil;
        m0(finished,"invalidate"); objc_release(finished);
    }
}
void tas_emote_ui_probe_start(void) {
    /* Selection is only a filter. Never clear history or native counters. */
    if (g_probe_timer) return;
    probe_track(nil);
    /* Include cached animations that were assigned before Start Trace. */
    id layers=m0(g_animation_layers,"allObjects");
    for (NSUInteger i=0,n=count(layers);i<n;i++) {
        id layer=at(layers,i);
        if (image_layer_id(m0(layer,"superlayer"))) probe_track(layer);
    }
    probe_sample_all(nil);
    if (g_probe_timer || !count(m0(g_probe_layers,"allObjects"))) return;
    id timer=((id (*)(id,SEL,double,BOOL,id))objc_msgSend)((id)objc_getClass("NSTimer"),sel_registerName("timerWithTimeInterval:repeats:block:"),1.0,YES,(id)^(id fired) { probe_sample_all(fired); });
    if (!timer) return;
    g_probe_timer=objc_retain(timer);
    ((void (*)(id,SEL,double))objc_msgSend)(timer,sel_registerName("setTolerance:"),0.25);
    ((void (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSRunLoop"),"mainRunLoop"),sel_registerName("addTimer:forMode:"),timer,string("kCFRunLoopCommonModes"));
}
static void probe_display_refresh(id self,SEL selector,id link) {
    ((void (*)(id,SEL,id))g_probe_refresh)(self,selector,link);
    /* Count native callbacks, including when the sampled index wraps back to
     * the same value. Never request a decoder frame or alter its playhead. */
    for (unsigned i=0;i<64;i++) if (g_probe_playheads[i].layer==self) {
        if (m0(self,"animatedImage")!=g_probe_playheads[i].animation) break;
        id attachment=m0(self,"superlayer");
        if (attachment && image_layer_id(attachment)!=g_probe_playheads[i].number) break;
        g_probe_playheads[i].refreshes++;
        uint64_t index=probe_integer(self,"currentFrameIndex"); id frame=m0(self,"currentFrame");
        if (index!=g_probe_playheads[i].index || frame!=g_probe_playheads[i].frame) g_probe_playheads[i].advances++;
        g_probe_playheads[i].index=index; g_probe_playheads[i].frame=frame;
        break;
    }
}
static void probe_assignment(id layer,const char *event,id input,const char *branch) {
    uint64_t number=image_layer_id(m0(layer,"superlayer")); unsigned ordinal=0;
    if (!number) return;
    for (unsigned i=0;i<64;i++) if (g_probe_playheads[i].layer==layer && g_probe_playheads[i].number==number) {
        ordinal=g_probe_playheads[i].serial; break;
    }
    id parent=m0(layer,"superlayer"); char intent[320],decision[128]; probe_intent(parent,input,intent,sizeof(intent));
    if (strstr(event,"before")) {
        snprintf(decision,sizeof(decision),"%s/role-%s/mode-%d/wants-animation-%d",branch,probe_role(layer),probe_mode(parent),probe_flag(probe_image_data(parent),"isAnimated"));
        tas_image_probe_assignment(number,ordinal,input,decision);
        probe_intent(parent,input,intent,sizeof(intent));
    }
    char state[768];
    snprintf(state,sizeof(state),"layer=%u tracking=%s role=%s visibility=%s input=%d input-frames-readable=%d input-frames=%llu uiimage=%d uiimage-frames=%llu resident-animation=%d resident-frames=%llu current-frame=%d contents=%d branch=%s %s",
        ordinal,ordinal ? "admitted" : "untracked",probe_role(layer),probe_visibility(layer),input!=nil,
        responds(input,"frameCount"),(unsigned long long)probe_integer(input,"frameCount"),kind(input,"UIImage"),
        (unsigned long long)(responds(input,"images") ? count(m0(input,"images")) : 0),m0(layer,"animatedImage")!=nil,
        (unsigned long long)probe_integer(m0(layer,"animatedImage"),"frameCount"),m0(layer,"currentFrame")!=nil,m0(layer,"contents")!=nil,branch,intent);
    tas_emote_probe_image(number,ordinal,event,state);
}
static void probe_static_image(id self,SEL selector,id image) {
    const char *branch=tas_image_probe_caller(__builtin_return_address(0));
    if (image_layer_id(m0(self,"superlayer"))) probe_track(self);
    probe_snapshot(self,"static-set-before");
    probe_assignment(self,"assign-static-before",image,branch);
    ((void (*)(id,SEL,id))g_probe_static)(self,selector,image);
    probe_assignment(self,"assign-static-after",image,branch);
    probe_snapshot(self,"static-set-after"); tas_emote_ui_probe_start();
}
static void probe_remove_layer(id self,SEL selector) {
    probe_snapshot(self,"remove-before");
    ((void (*)(id,SEL))g_probe_remove)(self,selector);
    probe_snapshot(self,"remove-after");
}
static void probe_stop_animation(id self,SEL selector) {
    probe_snapshot(self,"stop-before");
    ((void (*)(id,SEL))g_probe_stop)(self,selector);
    probe_snapshot(self,"stop-after");
}
#endif
static void animation_stop_check(void) {
    id timer=g_animation_timer; g_animation_timer=nil;
    m0(timer,"invalidate"); objc_release(timer);
}
static void animation_track(id layer) {
    if (!g_animation_layers) g_animation_layers=objc_retain(m0((id)objc_getClass("NSHashTable"),"weakObjectsHashTable"));
    v1(g_animation_layers,"addObject:",layer);
    if (g_animation_timer || !animation_visible(layer)) return;
    /* Recovery only, once a second. Twitch's display link/decoder/playhead
     * remain untouched. The weak table cannot keep chat rows alive. */
    id timer=((id (*)(id,SEL,double,BOOL,id))objc_msgSend)((id)objc_getClass("NSTimer"),sel_registerName("timerWithTimeInterval:repeats:block:"),1.0,YES,(id)^(id fired) { animation_check(fired); });
    if (!timer) return;
    g_animation_timer=objc_retain(timer);
    ((void (*)(id,SEL,double))objc_msgSend)(timer,sel_registerName("setTolerance:"),0.25);
    ((void (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("NSRunLoop"),"mainRunLoop"),sel_registerName("addTimer:forMode:"),timer,string("kCFRunLoopCommonModes"));
}
/* Twitch's TWAnimatedImageLayer copies a GIF's finite loop count and pauses
 * on removal. Reattachment alone does not call updateAnimationState. Scope
 * recovery to a provider attachment and let Twitch check hidden/opacity and
 * parent presence; never force an offscreen or native emote to animate. */
static void provider_animation(id attachment) {
    if (!image_layer_id(attachment)) return;
    id layer=object_ivar(attachment,"animatedImageLayer");
    if (!kind(layer,"TWAnimatedImageLayer") || m0(layer,"superlayer")!=attachment ||
        !responds(layer,"animatedImage") || !responds(layer,"updateAnimationState") ||
        !responds(layer,"setLoopCountdown:") || !responds(layer,"displayLink")) return;
    id animation=m0(layer,"animatedImage");
    if (!animation) return;
    if (animation!=objc_getAssociatedObject(layer,&g_animation_key) ||
        (responds(layer,"loopCountdown") && !((NSUInteger (*)(id,SEL))objc_msgSend)(layer,sel_registerName("loopCountdown")))) {
        ((void (*)(id,SEL,NSUInteger))objc_msgSend)(layer,sel_registerName("setLoopCountdown:"),UINT64_MAX);
        objc_setAssociatedObject(layer,&g_animation_key,animation,1);
        INC(g_animation_loops);
    }
    animation_track(layer);
    id link=m0(layer,"displayLink");
    if (responds(link,"isPaused") && ((BOOL (*)(id,SEL))objc_msgSend)(link,sel_registerName("isPaused")) && animation_visible(layer)) {
        m0(layer,"updateAnimationState");
        if (!((BOOL (*)(id,SEL))objc_msgSend)(link,sel_registerName("isPaused"))) INC(g_animation_resumes);
    }
}
static void animation_check(id timer) {
    if (timer && timer!=g_animation_timer) return;
    id layers=m0(g_animation_layers,"allObjects"); BOOL visible=NO;
    for (NSUInteger i=0,n=count(layers);i<n;i++) {
        id layer=at(layers,i),attachment=m0(layer,"superlayer");
        if (!m0(layer,"animatedImage") || (attachment && !image_layer_id(attachment))) { v1(g_animation_layers,"removeObject:",layer); continue; }
        if (!attachment) continue; /* Keep only a weak reference for reattachment/foreground. */
        if (!animation_visible(layer)) continue;
        visible=YES; INC(g_animation_checks); provider_animation(attachment);
    }
    if (!visible) animation_stop_check();
}
static void animated_set_image(id self, SEL sel, id image) {
#if TAS_EMOTE_DIAGNOSTIC
    const char *branch=tas_image_probe_caller(__builtin_return_address(0));
    if (image_layer_id(m0(self,"superlayer"))) probe_track(self);
    probe_snapshot(self,image ? "animation-set-before" : "animation-clear-before");
    if (image) probe_assignment(self,"assign-animation-before",image,branch);
#endif
    ((void (*)(id,SEL,id))g_animated_image)(self,sel,image);
#if TAS_EMOTE_DIAGNOSTIC
    if (image) probe_assignment(self,"assign-animation-after",image,branch);
    if (image) tas_emote_probe_stage(image_layer_id(m0(self,"superlayer")),"chat-animation-decoded");
    probe_snapshot(self,image ? "animation-set-after" : "animation-clear-after");
    tas_emote_ui_probe_start();
#endif
    /* The setter resets its countdown even if a reused layer keeps its URL. */
    if (image!=objc_getAssociatedObject(self,&g_animation_key))
        objc_setAssociatedObject(self,&g_animation_key,nil,1);
    if (!image) v1(g_animation_layers,"removeObject:",self);
    provider_animation(m0(self,"superlayer"));
}

static Size proportional(Size size, uint64_t number) {
    double aspect = tas_emotes_aspect(number);
    if (aspect <= 0 || size.height <= 0) return size;
    tas_emote_proportions(&size.width, &size.height, aspect);
    INC(g_sized); return size;
}
static Rect proportional_layer_frame(Rect rect, uint64_t number) {
    if (!number) return rect;
    INC(g_layer_ids);
    Size before = rect.size;
    rect.size = proportional(rect.size,number);
    if (before.width != rect.size.width || before.height != rect.size.height) INC(g_layer_resizes);
    return rect;
}
/* Swift also sends setFrame: to CALayer's implementation using super calls.
 * Hook that boundary, filtering all work to identified provider image layers. */
static void layer_set_frame(id self, SEL sel, Rect rect) {
    if (kind(self,"_TtC6Twitch20ImageAttachmentLayer")) {
        INC(g_layer_calls);
        uint64_t number=image_layer_id(self);
        tas_emote_probe_stage(number,"chat-image-layer-frame");
        rect = proportional_layer_frame(rect,number);
    }
    ((void (*)(id,SEL,Rect))g_layer_frame)(self,sel,rect);
}
static void image_layer_layout(id self, SEL sel) {
    ((void (*)(id,SEL))g_layer_layout)(self,sel);
    INC(g_layer_layouts);
    uint64_t number = image_layer_id(self);
    if (!number) return;
    tas_emote_probe_stage(number,"chat-image-layer-layout");
#if TAS_EMOTE_DIAGNOSTIC
    if (m0(self,"contents")) tas_emote_probe_stage(number,"chat-layer-has-image");
    {
        id animated=object_ivar(self,"animatedImageLayer");
        if (kind(animated,"TWAnimatedImageLayer")) probe_track(animated);
        id still=object_ivar(self,"staticImageLayer");
        if (kind(still,"TWAnimatedImageLayer")) probe_track(still);
        tas_emote_ui_probe_start();
    }
#endif
    Rect frame = ((Rect (*)(id,SEL))objc_msgSend)(self,sel_registerName("frame"));
    Rect adjusted = proportional_layer_frame(frame,number);
    if (frame.size.width != adjusted.size.width || frame.size.height != adjusted.size.height)
        ((void (*)(id,SEL,Rect))objc_msgSend)(self,sel_registerName("setFrame:"),adjusted);
    provider_animation(self);
}

static uint64_t message_id_at(id message, NSInteger index) {
    if (!responds(message,"emoteLocationsMap")) return 0;
    id number = ((id (*)(id,SEL,NSInteger))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithInteger:"),index);
    uint64_t result = synthetic_id(m1(m0(message,"emoteLocationsMap"),"objectForKey:",number));
    tas_emote_probe_stage(result,"chat-token-sizing");
    if (result) INC(g_resolved_ids);
    return result;
}
static Size message_size(id self, SEL sel, NSInteger index) {
    INC(g_size_calls);
    Size size = ((Size (*)(id,SEL,NSInteger))g_size)(self,sel,index);
    return proportional(size,message_id_at(self,index));
}
static Size base_message_size(id self, SEL sel, NSInteger index) {
    INC(g_size_calls);
    Size size = ((Size (*)(id,SEL,NSInteger))g_base_size)(self,sel,index);
    return proportional(size,message_id_at(self,index));
}
static Rect attachment_bounds(id self, SEL sel) {
    INC(g_bounds_calls);
    Rect rect = ((Rect (*)(id,SEL))g_bounds)(self,sel);
    rect.size = proportional(rect.size,attachment_id(self)); return rect;
}
static void attachment_set_bounds(id self, SEL sel, Rect rect) {
    INC(g_bounds_calls);
    rect.size = proportional(rect.size,attachment_id(self));
    ((void (*)(id,SEL,Rect))g_set_bounds)(self,sel,rect);
}
/* Swift calls its sizing routines directly, bypassing their ObjC bridges.
 * TextKit dispatches this attachment callback through Objective-C. Scope the
 * fallback to Twitch's layout manager (and our independent tap snapshot). */
static Rect textkit_bounds_with(IMP original, id self, SEL sel, id container, Rect fragment, Point position, NSUInteger index) {
    Rect rect = ((Rect (*)(id,SEL,id,Rect,Point,NSUInteger))original)(self,sel,container,fragment,position,index);
    id manager = responds(container,"layoutManager") ? m0(container,"layoutManager") : nil;
    id message = objc_getAssociatedObject(manager,&g_snapshot_message_key);
    if (!message && kind(manager,"_TtC6Twitch26MessageStringLayoutManager"))
        message = object_ivar(manager,"messageString");
    if (!message) return rect;
    INC(g_textkit_calls);
    uint64_t number = message_id_at(message,(NSInteger)index);
    if (number) rect.size = proportional(rect.size,number);
    return rect;
}

static Rect textkit_bounds(id self, SEL sel, id container, Rect fragment, Point position, NSUInteger index) {
    return textkit_bounds_with(g_textkit_bounds,self,sel,container,fragment,position,index);
}
static Rect chat_textkit_bounds(id self, SEL sel, id container, Rect fragment, Point position, NSUInteger index) {
    return textkit_bounds_with(g_chat_textkit_bounds,self,sel,container,fragment,position,index);
}

/* The chat manager delivers its locally generated messages through this
 * native delegate callback. Kotlin's constructor bridge is never used by
 * Kotlin itself. Build new tokens without changing the content sent to IRC. */
typedef struct { uint32_t a, b, c, d; } AutoModFlags;
static id substring(id value, Range range) {
    return ((id (*)(id,SEL,Range))objc_msgSend)(value,sel_registerName("substringWithRange:"),range);
}
static void append_text(id output, id original, id text, Range range) {
    if (!range.length) return;
    AutoModFlags flags = ((AutoModFlags (*)(id,SEL))objc_msgSend)(original,sel_registerName("autoModFlags"));
    id token = ((id (*)(id,SEL,id,AutoModFlags))objc_msgSend)(m0((id)object_getClass(original),"alloc"),sel_registerName("initWithText:autoModFlags:"),substring(text,range),flags);
    if (token) { v1(output,"addObject:",token); objc_release(token); }
}
static uint32_t sender_id(id value) {
    /* The UInt32? getter bridges to NSNumber, not NSString. Accept the
     * textual representation as a compatibility fallback, never a Swift ivar. */
    if (!kind(value,"NSNumber") && !kind(value,"NSString")) return 0;
    int64_t number = ((int64_t (*)(id,SEL))objc_msgSend)(value,sel_registerName("longLongValue"));
    return number > 0 && number <= UINT32_MAX ? (uint32_t)number : 0;
}

static id rewrite_local_message(id message, id room, uint32_t user) {
    if (!kind(message,"_TtC9TwitchKit13TWChatMessage") || !responds(message,"senderId")) return nil;
    id sender = m0(message,"senderId");
    if (!user || sender_id(sender) != user) return nil;
    INC(g_sent_calls);
    id tokens = m0(message,"messageTokens"); if (!kind(tokens,"NSArray")) return nil;
    id output = m0((id)objc_getClass("NSMutableArray"),"array");
    Class text_class = objc_getClass("_TtC9TwitchKit18TWMessageTextToken");
    id whitespace = m0((id)objc_getClass("NSCharacterSet"),"whitespaceAndNewlineCharacterSet");
    NSUInteger hits = 0;
    for (NSUInteger i = 0; i < count(tokens); i++) {
        id token = at(tokens,i);
        /* Preserve native emote/mention/URL/censored token objects unchanged. */
        if (object_getClass(token) != text_class) { v1(output,"addObject:",token); continue; }
        id text = m0(token,"text"), matches = tas_emotes_local_matches_copy(room,text);
        if (!matches || !count(matches)) { v1(output,"addObject:",token); if (matches) objc_release(matches); continue; }
        NSUInteger length = ((NSUInteger (*)(id,SEL))objc_msgSend)(text,sel_registerName("length"));
        NSUInteger start = 0, pending = 0;
        while (start < length) {
            Range separator = ((Range (*)(id,SEL,id,NSUInteger,Range))objc_msgSend)(text,sel_registerName("rangeOfCharacterFromSet:options:range:"),whitespace,(NSUInteger)0,(Range){start,length-start});
            NSUInteger end = separator.location < length ? separator.location : length;
            if (end > start) {
                id name = substring(text,(Range){start,end-start}), number = m1(matches,"objectForKey:",name);
                if (synthetic_id(number)) {
                    id emote = ((id (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("_TtC9TwitchKit19TWMessageEmoteToken"),"alloc"),sel_registerName("initWithEmoteId:emoteText:"),number,name);
                    if (emote) {
                        append_text(output,token,text,(Range){pending,start-pending});
                        v1(output,"addObject:",emote); objc_release(emote); hits++; pending = end;
                    }
                }
            }
            start = end < length ? end + 1 : length;
        }
        append_text(output,token,text,(Range){pending,length-pending}); objc_release(matches);
    }
    if (!hits) return nil;
    /* TKIdentity is the ObjC name of Swift_Deprecated_Identity. Construct it
     * through its bridge instead of interpreting the message's Swift struct. */
    id identity = ((id (*)(id,SEL,uint32_t,id,id))objc_msgSend)(m0((id)objc_getClass("TKIdentity"),"alloc"),sel_registerName("initWithId:name:synthesizedDisplayName:"),user,m0(message,"senderName"),m0(message,"senderDisplayName"));
    if (!identity) return nil;
    uint64_t flags = ((uint64_t (*)(id,SEL))objc_msgSend)(message,sel_registerName("flags"));
    NSInteger kind_value = ((NSInteger (*)(id,SEL))objc_msgSend)(message,sel_registerName("kind"));
    uint64_t modes = ((uint64_t (*)(id,SEL))objc_msgSend)(message,sel_registerName("userModes"));
    id result = ((id (*)(id,SEL,id,id,id,id,id,id,id,uint64_t,NSInteger,uint64_t,id,id))objc_msgSend)(m0((id)object_getClass(message),"alloc"),sel_registerName("initWithTokens:senderIdentity:badges:date:messageID:liveMessageID:color:flags:kind:userModes:messageType:messageTags:"),output,identity,m0(message,"badges"),m0(message,"date"),m0(message,"messageID"),m0(message,"liveMessageID"),m0(message,"color"),flags,kind_value,modes,m0(message,"messageType"),m0(message,"messageTags"));
    objc_release(identity);
    if (result) {
        BOOL historical = ((BOOL (*)(id,SEL))objc_msgSend)(message,sel_registerName("isHistoricalMessage"));
        ((void (*)(id,SEL,BOOL))objc_msgSend)(result,sel_registerName("setIsHistoricalMessage:"),historical);
        __atomic_add_fetch(&g_sent_matches,hits,__ATOMIC_RELAXED);
    }
    return result;
}
static void receive_messages(id self, SEL sel, id manager, id messages, uint32_t user, uint32_t channel) {
    INC(g_receive_calls);
    id rewritten = nil;
    if (user && kind(messages,"NSArray")) {
        char room_number[16]; snprintf(room_number,sizeof(room_number),"%u",channel);
        id room = string(room_number);
        for (NSUInteger i = 0; i < count(messages); i++) {
            id replacement = rewrite_local_message(at(messages,i),room,user);
            if (!replacement) continue;
            if (!rewritten) rewritten = m0(messages,"mutableCopy");
            ((void (*)(id,SEL,NSUInteger,id))objc_msgSend)(rewritten,sel_registerName("replaceObjectAtIndex:withObject:"),i,replacement);
            objc_release(replacement);
        }
    }
#if TAS_EMOTE_DIAGNOSTIC
    id delivered=rewritten ?: messages;
    char channel_number[16]; snprintf(channel_number,sizeof(channel_number),"%u",channel);
    if (kind(delivered,"NSArray")) for (NSUInteger i=0;i<count(delivered) && i<256;i++) {
        id message=at(delivered,i);
        id tokens=responds(message,"messageTokens") ? m0(message,"messageTokens") : nil;
        if (!kind(tokens,"NSArray")) continue;
        for (NSUInteger j=0;j<count(tokens) && j<128;j++) {
            id token=at(tokens,j);
            BOOL emote=responds(token,"emoteText");
            id value=emote ? m0(token,"emoteText") : responds(token,"text") ? m0(token,"text") : nil;
            if (!kind(value,"NSString")) continue;
            const char *body=((const char *(*)(id,SEL))objc_msgSend)(value,sel_registerName("UTF8String"));
            tas_emote_probe_text("native-delivery",body,channel_number,emote ? "emote-token" : "literal-text-token");
        }
    }
#endif
    ((void (*)(id,SEL,id,id,uint32_t,uint32_t))g_receive)(self,sel,manager,rewritten ?: messages,user,channel);
    if (rewritten) objc_release(rewritten);
}

static IMP g_details_load;
static void bool_value(id o, const char *s, BOOL value) {
    ((void (*)(id,SEL,BOOL))objc_msgSend)(o,sel_registerName(s),value);
}
static void integer_value(id o, const char *s, NSInteger value) {
    ((void (*)(id,SEL,NSInteger))objc_msgSend)(o,sel_registerName(s),value);
}
static id frame_view(const char *class_name, Rect frame) {
    return ((id (*)(id,SEL,Rect))objc_msgSend)(m0((id)objc_getClass(class_name),"alloc"),sel_registerName("initWithFrame:"),frame);
}
static BOOL details_dismiss(id self, id completion) {
    id nav = m0(self,"navigationController");
    /* Dismiss only our presented wrapper, never a stream controller or an
     * ancestor after the details controller has already been detached. */
    if (!kind(nav,"UINavigationController") || m0(m0(nav,"viewControllers"),"firstObject") != self ||
        m0(m0(nav,"presentingViewController"),"presentedViewController") != nav ||
        ((BOOL (*)(id,SEL))objc_msgSend)(nav,sel_registerName("isBeingPresented")) ||
        ((BOOL (*)(id,SEL))objc_msgSend)(nav,sel_registerName("isBeingDismissed")) ||
        objc_getAssociatedObject(self,&g_details_dismissing_key)) return NO;
    objc_setAssociatedObject(self,&g_details_dismissing_key,string("yes"),1);
    ((void (*)(id,SEL,BOOL,id))objc_msgSend)(nav,sel_registerName("dismissViewControllerAnimated:completion:"),YES,completion);
    return YES;
}
static void details_close(id self, SEL sel, id sender) {
    (void)sel; (void)sender; details_dismiss(self,nil);
}
static id html_escape(id value) {
    const char *from[] = {"&", "\"", "'", "<", ">"};
    const char *to[] = {"&amp;", "&quot;", "&#39;", "&lt;", "&gt;"};
    for (size_t i = 0; i < 5; i++) value = ((id (*)(id,SEL,id,id))objc_msgSend)(value,sel_registerName("stringByReplacingOccurrencesOfString:withString:"),string(from[i]),string(to[i]));
    return value;
}
static void details_load(id self, SEL sel) {
    ((void (*)(id,SEL))g_details_load)(self,sel);
    id metadata = objc_getAssociatedObject(self,&g_metadata_key), table = m0(self,"tableView");
    v1(self,"setTitle:",key(metadata,"name"));
    id done = ((id (*)(id,SEL,NSInteger,id,SEL))objc_msgSend)(m0((id)objc_getClass("UIBarButtonItem"),"alloc"),sel_registerName("initWithBarButtonSystemItem:target:action:"),(NSInteger)0,self,sel_registerName("tas_close:"));
    v1(m0(self,"navigationItem"),"setRightBarButtonItem:",done); objc_release(done);
    Rect bounds = ((Rect (*)(id,SEL))objc_msgSend)(table,sel_registerName("bounds"));
    double width = bounds.size.width > 0 ? bounds.size.width : 320;
    id header = frame_view("UIView",(Rect){{0,0},{width,152}});
    id title = frame_view("UILabel",(Rect){{128,20},{width-144,32}});
    v1(title,"setText:",key(metadata,"name"));
    v1(title,"setTextColor:",m0((id)objc_getClass("UIColor"),"labelColor"));
    v1(title,"setFont:",((id (*)(id,SEL,CGFloat))objc_msgSend)((id)objc_getClass("UIFont"),sel_registerName("boldSystemFontOfSize:"),(CGFloat)20));
    integer_value(title,"setAutoresizingMask:",2); v1(header,"addSubview:",title); objc_release(title);
    id subtitle = frame_view("UILabel",(Rect){{128,54},{width-144,84}});
    v1(subtitle,"setText:",key(metadata,"subtitle")); integer_value(subtitle,"setNumberOfLines:",3);
    v1(subtitle,"setTextColor:",m0((id)objc_getClass("UIColor"),"secondaryLabelColor"));
    v1(subtitle,"setFont:",((id (*)(id,SEL,CGFloat))objc_msgSend)((id)objc_getClass("UIFont"),sel_registerName("systemFontOfSize:"),(CGFloat)16));
    integer_value(subtitle,"setAutoresizingMask:",2); v1(header,"addSubview:",subtitle); objc_release(subtitle);
    /* WebKit decodes GIF/WebP animation directly. This document is image-only,
     * with no script, remote HTML, or persistent browsing data. */
    Class web_class = objc_getClass("WKWebView");
    if (!web_class) {
        dlopen("/System/Library/Frameworks/WebKit.framework/WebKit", RTLD_LAZY);
        web_class = objc_getClass("WKWebView");
    }
    if (web_class) {
        id config = m0((id)objc_getClass("WKWebViewConfiguration"),"new");
        v1(config,"setWebsiteDataStore:",m0((id)objc_getClass("WKWebsiteDataStore"),"nonPersistentDataStore"));
        bool_value(m0(config,"preferences"),"setJavaScriptEnabled:",NO);
        id web = ((id (*)(id,SEL,Rect,id))objc_msgSend)(m0((id)web_class,"alloc"),sel_registerName("initWithFrame:configuration:"),(Rect){{16,28},{96,96}},config);
        objc_release(config);
        bool_value(web,"setOpaque:",NO); bool_value(web,"setUserInteractionEnabled:",NO);
        v1(web,"setBackgroundColor:",m0((id)objc_getClass("UIColor"),"clearColor"));
        v1(m0(web,"scrollView"),"setBackgroundColor:",m0((id)objc_getClass("UIColor"),"clearColor"));
        bool_value(m0(web,"scrollView"),"setScrollEnabled:",NO);
        id html = m0((id)objc_getClass("NSMutableString"),"string");
        v1(html,"appendString:",string("<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; img-src https://cdn.7tv.app https://cdn.betterttv.net https://cdn.frankerfacez.com; style-src 'unsafe-inline'\"><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent}img{width:100%;height:100%;object-fit:contain}</style><img alt='' src=\""));
        v1(html,"appendString:",html_escape(key(metadata,"url"))); v1(html,"appendString:",string("\">"));
        ((id (*)(id,SEL,id,id))objc_msgSend)(web,sel_registerName("loadHTMLString:baseURL:"),html,nil);
        v1(header,"addSubview:",web); objc_release(web);
    }
    v1(table,"setTableHeaderView:",header); objc_release(header);
    ((void (*)(id,SEL,CGFloat))objc_msgSend)(table,sel_registerName("setRowHeight:"),(CGFloat)60);
}
static NSInteger details_rows(id self, SEL sel, id table, NSInteger section) {
    (void)self; (void)sel; (void)table; return section == 0 ? 3 : 0;
}
static id details_cell(id self, SEL sel, id table, id path) {
    (void)self; (void)sel;
    NSInteger row = ((NSInteger (*)(id,SEL))objc_msgSend)(path,sel_registerName("row"));
    if (row < 0 || row > 2) return nil;
    const char *names[] = {"Copy name","Copy image URL","Open in browser"};
    const char *icons[] = {"doc.on.doc","link","arrow.up.right.square"};
    id cell = m1(table,"dequeueReusableCellWithIdentifier:",string("TASEmoteAction"));
    if (!cell) {
        cell = ((id (*)(id,SEL,NSInteger,id))objc_msgSend)(m0((id)objc_getClass("UITableViewCell"),"alloc"),sel_registerName("initWithStyle:reuseIdentifier:"),(NSInteger)0,string("TASEmoteAction"));
        m0(cell,"autorelease");
    }
    v1(m0(cell,"textLabel"),"setText:",string(names[row]));
    v1(m0(cell,"imageView"),"setImage:",m1((id)objc_getClass("UIImage"),"systemImageNamed:",string(icons[row])));
    return cell;
}
static void details_select(id self, SEL sel, id table, id path) {
    (void)sel;
    if (objc_getAssociatedObject(self,&g_details_dismissing_key)) return;
    ((void (*)(id,SEL,id,BOOL))objc_msgSend)(table,sel_registerName("deselectRowAtIndexPath:animated:"),path,YES);
    NSInteger row = ((NSInteger (*)(id,SEL))objc_msgSend)(path,sel_registerName("row"));
    id metadata = objc_getAssociatedObject(self,&g_metadata_key);
    if (row == 0 || row == 1) v1(m0((id)objc_getClass("UIPasteboard"),"generalPasteboard"),"setString:",key(metadata,row == 0 ? "name" : "url"));
    else if (row == 2) {
        id url = m1((id)objc_getClass("NSURL"),"URLWithString:",key(metadata,"url"));
        if (!url) return;
        /* UIKit owns the copied completion. C block captures are not owning
         * Objective-C references: keep the URL alive without retaining the
         * sheet, presenter, composer or stream across the browser handoff. */
        id held = objc_retain(url);
        BOOL closing = details_dismiss(self,(id)^{
            id application = m0((id)objc_getClass("UIApplication"),"sharedApplication");
            if (((NSInteger (*)(id,SEL))objc_msgSend)(application,sel_registerName("applicationState")) == 0)
                ((void (*)(id,SEL,id,id,id))objc_msgSend)(application,sel_registerName("openURL:options:completionHandler:"),held,m0((id)objc_getClass("NSDictionary"),"dictionary"),nil);
            objc_release(held);
        });
        if (!closing) objc_release(held);
        return; /* No UIKit transition is initiated after opening the browser. */
    } else return;
    details_close(self,sel,nil);
}
static BOOL register_details(void) {
    if (g_details_class) return YES;
    Class base = objc_getClass("UITableViewController"); if (!base) return NO;
    g_details_class = objc_allocateClassPair(base,"TASProviderEmoteController",0);
    if (!g_details_class) return NO;
    g_details_load = class_getMethodImplementation(base,sel_registerName("viewDidLoad"));
    class_addMethod(g_details_class,sel_registerName("viewDidLoad"),(IMP)details_load,"v@:");
    class_addMethod(g_details_class,sel_registerName("tas_close:"),(IMP)details_close,"v@:@");
    class_addMethod(g_details_class,sel_registerName("tableView:numberOfRowsInSection:"),(IMP)details_rows,"q@:@q");
    class_addMethod(g_details_class,sel_registerName("tableView:cellForRowAtIndexPath:"),(IMP)details_cell,"@@:@@");
    class_addMethod(g_details_class,sel_registerName("tableView:didSelectRowAtIndexPath:"),(IMP)details_select,"v@:@@");
    objc_registerClassPair(g_details_class); return YES;
}
static id presenter_for_view(id view) {
    for (id responder = view; responder; responder = m0(responder,"nextResponder"))
        if (kind(responder,"UIViewController")) return responder;
    return nil;
}
BOOL tas_emote_ui_modal_visible(id view) {
    id controller=presenter_for_view(view);
    for (unsigned i=0;controller && i<24;i++,controller=m0(controller,"parentViewController"))
        if (m0(controller,"presentedViewController")) return YES;
    return NO;
}
BOOL tas_emote_ui_present_details(id view, id metadata) {
    if (!metadata) return NO;
    id presenter = presenter_for_view(view);
    if (!presenter || m0(presenter,"presentedViewController") || !register_details()) return NO;
    id details = ((id (*)(id,SEL,NSInteger))objc_msgSend)(m0((id)g_details_class,"alloc"),sel_registerName("initWithStyle:"),(NSInteger)0);
    objc_setAssociatedObject(details,&g_metadata_key,metadata,1);
    id nav = m1(m0((id)objc_getClass("UINavigationController"),"alloc"),"initWithRootViewController:",details);
    objc_release(details); integer_value(nav,"setModalPresentationStyle:",1);
    id sheet = responds(nav,"sheetPresentationController") ? m0(nav,"sheetPresentationController") : nil;
    if (sheet) {
        id detents = m0((id)objc_getClass("NSMutableArray"),"array");
        v1(detents,"addObject:",m0((id)objc_getClass("UISheetPresentationControllerDetent"),"mediumDetent"));
        v1(detents,"addObject:",m0((id)objc_getClass("UISheetPresentationControllerDetent"),"largeDetent"));
        v1(sheet,"setDetents:",detents); bool_value(sheet,"setPrefersGrabberVisible:",YES);
    }
    ((void (*)(id,SEL,id,BOOL,id))objc_msgSend)(presenter,sel_registerName("presentViewController:animated:completion:"),nav,YES,nil);
    objc_release(nav); INC(g_details); return YES;
}
static BOOL show_details(id view, uint64_t number) {
    id metadata=tas_emotes_metadata_copy(number);
    BOOL shown=tas_emote_ui_present_details(view,metadata);
    objc_release(metadata); return shown;
}

/* Hit-test an independent TextKit snapshot so the tap does not mutate Twitch's
 * actor-owned layout engine. Use its text layer frame and container padding. */
static uint64_t tapped_emote(id self, id gesture) {
    id layer = object_ivar(self,"messageStringLayer"), message = object_ivar(layer,"messageString");
    id text_layer = object_ivar(layer,"textLayer");
    if (!kind(text_layer,"CALayer") || !responds(message,"attributedString")) return 0;
    id attributed = m0(message,"attributedString");
    INC(g_snapshots);
    if (!kind(attributed,"NSAttributedString")) return 0;
    Point point = ((Point (*)(id,SEL,id))objc_msgSend)(gesture,sel_registerName("locationInView:"),self);
    point = ((Point (*)(id,SEL,Point,id))objc_msgSend)(text_layer,sel_registerName("convertPoint:fromLayer:"),point,m0(self,"layer"));
    Rect bounds = ((Rect (*)(id,SEL))objc_msgSend)(text_layer,sel_registerName("bounds"));
    point.x -= bounds.origin.x; point.y -= bounds.origin.y;
    if (point.x < 0 || point.y < 0 || point.x >= bounds.size.width || point.y >= bounds.size.height) return 0;
    id storage = m1(m0((id)objc_getClass("NSTextStorage"),"alloc"),"initWithAttributedString:",attributed);
    id manager = m0((id)objc_getClass("NSLayoutManager"),"new");
    objc_setAssociatedObject(manager,&g_snapshot_message_key,message,1);
    id container = ((id (*)(id,SEL,Size))objc_msgSend)(m0((id)objc_getClass("NSTextContainer"),"alloc"),sel_registerName("initWithSize:"),bounds.size);
    ((void (*)(id,SEL,CGFloat))objc_msgSend)(container,sel_registerName("setLineFragmentPadding:"),(CGFloat)0);
    v1(manager,"addTextContainer:",container); v1(storage,"addLayoutManager:",manager);
    NSUInteger glyph = ((NSUInteger (*)(id,SEL,Point,id,CGFloat *))objc_msgSend)(manager,sel_registerName("glyphIndexForPoint:inTextContainer:fractionOfDistanceThroughGlyph:"),point,container,NULL);
    uint64_t number = 0;
    NSUInteger total = ((NSUInteger (*)(id,SEL))objc_msgSend)(manager,sel_registerName("numberOfGlyphs"));
    if (glyph < total) {
        Rect rect = ((Rect (*)(id,SEL,Range,id))objc_msgSend)(manager,sel_registerName("boundingRectForGlyphRange:inTextContainer:"),(Range){glyph,1},container);
        if (point.x >= rect.origin.x && point.y >= rect.origin.y && point.x < rect.origin.x+rect.size.width && point.y < rect.origin.y+rect.size.height) {
            NSUInteger index = ((NSUInteger (*)(id,SEL,NSUInteger))objc_msgSend)(manager,sel_registerName("characterIndexForGlyphAtIndex:"),glyph);
            number = message_id_at(message,(NSInteger)index);
        }
    }
    objc_release(container); objc_release(manager); objc_release(storage); return number;
}
static void tap_gesture(id self, SEL sel, id gesture) {
    INC(g_tap_calls);
    uint64_t number = tapped_emote(self,gesture);
    if (number) INC(g_tap_hits);
    if (number && show_details(self,number)) return;
    ((void (*)(id,SEL,id))g_tap)(self,sel,gesture);
}
static BOOL hook(Class cls, const char *name, unsigned int arguments, IMP replacement, IMP *original) {
    if (*original || !cls) return *original != NULL;
    SEL sel = sel_registerName(name); Method method = class_getInstanceMethod(cls,sel);
    if (!method || method_getNumberOfArguments(method) != arguments) return NO;
    *original = method_getImplementation(method);
    if (!class_addMethod(cls,sel,replacement,method_getTypeEncoding(method))) method_setImplementation(method,replacement);
    return YES;
}
void tas_emote_ui_retry_hooks(void) {
    if (!tas_emotes_enabled_this_launch()) return;
    Class identity = objc_getClass("TKIdentity"), text_token = objc_getClass("_TtC9TwitchKit18TWMessageTextToken");
    if (class_getInstanceMethod(identity,sel_registerName("initWithId:name:synthesizedDisplayName:")) &&
        class_getInstanceMethod(text_token,sel_registerName("initWithText:autoModFlags:")))
        hook(objc_getClass("_TtC6Twitch20TwitchChatController"),"chatManager:receivedMessages:for:on:",6,(IMP)receive_messages,&g_receive);
    hook(objc_getClass("_TtC6Twitch19ChatEmoteAttachment"),"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:",6,(IMP)chat_textkit_bounds,&g_chat_textkit_bounds);
    hook(objc_getClass("NSTextAttachment"),"attachmentBoundsForTextContainer:proposedLineFragment:glyphPosition:characterIndex:",6,(IMP)textkit_bounds,&g_textkit_bounds);
    hook(objc_getClass("_TtC6Twitch17ChatMessageString"),"sizeOfImageAttachmentAtCharacterIndex:",3,(IMP)message_size,&g_size);
    hook(objc_getClass("_TtC6Twitch13MessageString"),"sizeOfImageAttachmentAtCharacterIndex:",3,(IMP)base_message_size,&g_base_size);
    hook(objc_getClass("_TtC6Twitch32MessageStringImageDataAttachment"),"bounds",2,(IMP)attachment_bounds,&g_bounds);
    hook(objc_getClass("_TtC6Twitch32MessageStringImageDataAttachment"),"setBounds:",3,(IMP)attachment_set_bounds,&g_set_bounds);
    hook(objc_getClass("CALayer"),"setFrame:",3,(IMP)layer_set_frame,&g_layer_frame);
    hook(objc_getClass("_TtC6Twitch20ImageAttachmentLayer"),"layoutSublayers",2,(IMP)image_layer_layout,&g_layer_layout);
    hook(objc_getClass("TWAnimatedImageLayer"),"setAnimatedImage:",3,(IMP)animated_set_image,&g_animated_image);
#if TAS_EMOTE_DIAGNOSTIC
    /* Native signature: void displayDidRefresh:(CADisplayLink *). */
    tas_image_probe_install();
    hook(objc_getClass("TWAnimatedImageLayer"),"displayDidRefresh:",3,(IMP)probe_display_refresh,&g_probe_refresh);
    /* Native signatures: void setStaticImage:(UIImage *), void removeFromSuperlayer. */
    hook(objc_getClass("TWAnimatedImageLayer"),"setStaticImage:",3,(IMP)probe_static_image,&g_probe_static);
    hook(objc_getClass("TWAnimatedImageLayer"),"removeFromSuperlayer",2,(IMP)probe_remove_layer,&g_probe_remove);
    hook(objc_getClass("TWAnimatedImageLayer"),"stopAnimating",2,(IMP)probe_stop_animation,&g_probe_stop);
#endif
    hook(objc_getClass("_TtC6Twitch17MessageStringView"),"handleTapGesture:",3,(IMP)tap_gesture,&g_tap);
    /* The existing launch/foreground observer retries these hooks. It also
     * restarts recovery after a background or no-visible-emote idle stop. */
    animation_check(nil);
}
void tas_emote_ui_status(char *buffer, size_t capacity) {
    if (!buffer || !capacity) return;
    snprintf(buffer,capacity,
        "\nEmote UI (this launch)\n"
        "Hooks (local delivery/chat size/base size/bounds/TextKit/tap): %s/%s/%s/%s/%s/%s\n"
        "Native delivery callbacks/local messages/matched emotes: %llu/%llu/%llu\n"
        "Sizing calls (message/attachment/TextKit)/resolved IDs: %llu/%llu/%llu/%llu\n"
        "Proportional sizes/taps/provider sheets: %llu/%llu/%llu\n"
        "Tap snapshots/provider hits: %llu/%llu\n"
        "Image layer hooks (frame/layout): %s/%s\n"
        "Image layer frame calls/layouts/provider IDs/resizes: %llu/%llu/%llu/%llu\n"
        "Provider animation hook/loop bindings/resumes/checks: %s/%llu/%llu/%llu\n",
        g_receive ? "installed" : "missing",g_size ? "installed" : "missing",g_base_size ? "installed" : "missing",g_bounds && g_set_bounds ? "installed" : "missing",g_textkit_bounds && g_chat_textkit_bounds ? "installed" : "missing",g_tap ? "installed" : "missing",
        (unsigned long long)GET(g_receive_calls),(unsigned long long)GET(g_sent_calls),(unsigned long long)GET(g_sent_matches),
        (unsigned long long)GET(g_size_calls),(unsigned long long)GET(g_bounds_calls),(unsigned long long)GET(g_textkit_calls),(unsigned long long)GET(g_resolved_ids),
        (unsigned long long)GET(g_sized),(unsigned long long)GET(g_tap_calls),(unsigned long long)GET(g_details),(unsigned long long)GET(g_snapshots),(unsigned long long)GET(g_tap_hits),
        g_layer_frame ? "installed" : "missing",g_layer_layout ? "installed" : "missing",
        (unsigned long long)GET(g_layer_calls),(unsigned long long)GET(g_layer_layouts),(unsigned long long)GET(g_layer_ids),(unsigned long long)GET(g_layer_resizes),
        g_animated_image ? "installed" : "missing",(unsigned long long)GET(g_animation_loops),(unsigned long long)GET(g_animation_resumes),(unsigned long long)GET(g_animation_checks));
#if TAS_EMOTE_DIAGNOSTIC
    size_t used=strnlen(buffer,capacity);
    if (used<capacity) snprintf(buffer+used,capacity-used,
        "Rolling recorder hooks (refresh/static/remove/stop): %s/%s/%s/%s; live layer limit: 64\n",
        g_probe_refresh ? "installed" : "missing",g_probe_static ? "installed" : "missing",
        g_probe_remove ? "installed" : "missing",g_probe_stop ? "installed" : "missing");
    struct timespec now; clock_gettime(CLOCK_MONOTONIC,&now);
    used=strnlen(buffer,capacity);
    if (used<capacity) snprintf(buffer+used,capacity-used,
        "Recorder timer/live layers/polls/last poll age: %s/%lu/%llu/%llds\n"
        "Recorder admission denials/visible-priority evictions: %llu/%llu (event counts, not unique layers)\n",
        g_probe_timer ? "active" : "idle",(unsigned long)count(m0(g_probe_layers,"allObjects")),(unsigned long long)g_probe_polls,
        g_probe_last_poll ? (long long)(now.tv_sec-g_probe_last_poll) : -1LL,
        (unsigned long long)g_probe_dropped,(unsigned long long)g_probe_evicted);
    used=strnlen(buffer,capacity); if (used<capacity) tas_image_probe_status(buffer+used,capacity-used);
#endif
}
