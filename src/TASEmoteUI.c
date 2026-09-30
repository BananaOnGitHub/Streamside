/* Optional UIKit integration. All hooks are scoped to Twitch's emote/chat
 * classes and synthetic IDs; installation is gated by the launch preference. */
#include "TASEmoteUI.h"
#include "TASEmotes.h"
#include "TASEmoteGeometry.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

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
static IMP g_receive, g_size, g_base_size, g_bounds, g_set_bounds, g_textkit_bounds, g_chat_textkit_bounds, g_tap;
static Class g_details_class;
static char g_metadata_key, g_snapshot_message_key;
static uint64_t g_receive_calls, g_sent_calls, g_sent_matches, g_sized, g_details, g_tap_calls, g_snapshots, g_tap_hits;
static uint64_t g_size_calls, g_bounds_calls, g_textkit_calls, g_resolved_ids;
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
static Size proportional(Size size, uint64_t number) {
    double aspect = tas_emotes_aspect(number);
    if (aspect <= 0 || size.height <= 0) return size;
    tas_emote_proportions(&size.width, &size.height, aspect);
    INC(g_sized); return size;
}
static uint64_t message_id_at(id message, NSInteger index) {
    if (!responds(message,"emoteLocationsMap")) return 0;
    id number = ((id (*)(id,SEL,NSInteger))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithInteger:"),index);
    uint64_t result = synthetic_id(m1(m0(message,"emoteLocationsMap"),"objectForKey:",number));
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
static id rewrite_local_message(id message, id room, uint32_t user) {
    if (!kind(message,"_TtC9TwitchKit13TWChatMessage") || !responds(message,"senderId")) return nil;
    id sender = m0(message,"senderId");
    if (!kind(sender,"NSString") || ((uint64_t (*)(id,SEL))objc_msgSend)(sender,sel_registerName("longLongValue")) != user) return nil;
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
                    append_text(output,token,text,(Range){pending,start-pending});
                    id emote = ((id (*)(id,SEL,id,id))objc_msgSend)(m0((id)objc_getClass("_TtC9TwitchKit19TWMessageEmoteToken"),"alloc"),sel_registerName("initWithEmoteId:emoteText:"),number,name);
                    if (emote) { v1(output,"addObject:",emote); objc_release(emote); hits++; pending = end; }
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
static void details_close(id self, SEL sel, id sender) {
    (void)sel; (void)sender;
    ((void (*)(id,SEL,BOOL,id))objc_msgSend)(self,sel_registerName("dismissViewControllerAnimated:completion:"),YES,nil);
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
    ((void (*)(id,SEL,id,BOOL))objc_msgSend)(table,sel_registerName("deselectRowAtIndexPath:animated:"),path,YES);
    NSInteger row = ((NSInteger (*)(id,SEL))objc_msgSend)(path,sel_registerName("row"));
    id metadata = objc_getAssociatedObject(self,&g_metadata_key);
    if (row == 0 || row == 1) v1(m0((id)objc_getClass("UIPasteboard"),"generalPasteboard"),"setString:",key(metadata,row == 0 ? "name" : "url"));
    else if (row == 2) {
        id url = m1((id)objc_getClass("NSURL"),"URLWithString:",key(metadata,"url"));
        ((void (*)(id,SEL,id,id,id))objc_msgSend)(m0((id)objc_getClass("UIApplication"),"sharedApplication"),sel_registerName("openURL:options:completionHandler:"),url,m0((id)objc_getClass("NSDictionary"),"dictionary"),nil);
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
static BOOL show_details(id view, uint64_t number) {
    id metadata = tas_emotes_metadata_copy(number); if (!metadata) return NO;
    id presenter = presenter_for_view(view);
    if (!presenter || m0(presenter,"presentedViewController") || !register_details()) { objc_release(metadata); return NO; }
    id details = ((id (*)(id,SEL,NSInteger))objc_msgSend)(m0((id)g_details_class,"alloc"),sel_registerName("initWithStyle:"),(NSInteger)0);
    objc_setAssociatedObject(details,&g_metadata_key,metadata,1); objc_release(metadata);
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
    hook(objc_getClass("_TtC6Twitch17MessageStringView"),"handleTapGesture:",3,(IMP)tap_gesture,&g_tap);
}
void tas_emote_ui_status(char *buffer, size_t capacity) {
    if (!buffer || !capacity) return;
    snprintf(buffer,capacity,
        "\nEmote UI (this launch)\n"
        "Hooks (local delivery/chat size/base size/bounds/TextKit/tap): %s/%s/%s/%s/%s/%s\n"
        "Native delivery callbacks/local messages/matched emotes: %llu/%llu/%llu\n"
        "Sizing calls (message/attachment/TextKit)/resolved IDs: %llu/%llu/%llu/%llu\n"
        "Proportional sizes/taps/provider sheets: %llu/%llu/%llu\n"
        "Tap snapshots/provider hits: %llu/%llu\n",
        g_receive ? "installed" : "missing",g_size ? "installed" : "missing",g_base_size ? "installed" : "missing",g_bounds && g_set_bounds ? "installed" : "missing",g_textkit_bounds && g_chat_textkit_bounds ? "installed" : "missing",g_tap ? "installed" : "missing",
        (unsigned long long)GET(g_receive_calls),(unsigned long long)GET(g_sent_calls),(unsigned long long)GET(g_sent_matches),
        (unsigned long long)GET(g_size_calls),(unsigned long long)GET(g_bounds_calls),(unsigned long long)GET(g_textkit_calls),(unsigned long long)GET(g_resolved_ids),
        (unsigned long long)GET(g_sized),(unsigned long long)GET(g_tap_calls),(unsigned long long)GET(g_details),(unsigned long long)GET(g_snapshots),(unsigned long long)GET(g_tap_hits));
}
