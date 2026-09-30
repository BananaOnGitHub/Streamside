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
static IMP g_send, g_size, g_base_size, g_bounds, g_set_bounds, g_tap;
static Class g_details_class;
static char g_metadata_key;
static uint64_t g_sent_calls, g_sent_matches, g_sized, g_details, g_tap_calls, g_snapshots, g_tap_hits;
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
    return synthetic_id(m1(m0(message,"emoteLocationsMap"),"objectForKey:",number));
}
static Size message_size(id self, SEL sel, NSInteger index) {
    Size size = ((Size (*)(id,SEL,NSInteger))g_size)(self,sel,index);
    return proportional(size,message_id_at(self,index));
}
static Size base_message_size(id self, SEL sel, NSInteger index) {
    Size size = ((Size (*)(id,SEL,NSInteger))g_base_size)(self,sel,index);
    return proportional(size,message_id_at(self,index));
}
static Rect attachment_bounds(id self, SEL sel) {
    Rect rect = ((Rect (*)(id,SEL))g_bounds)(self,sel);
    rect.size = proportional(rect.size,attachment_id(self)); return rect;
}
static void attachment_set_bounds(id self, SEL sel, Rect rect) {
    rect.size = proportional(rect.size,attachment_id(self));
    ((void (*)(id,SEL,Rect))g_set_bounds)(self,sel,rect);
}
/* Only append names actually used in this outgoing message, and never replace
 * Twitch's existing emote definitions. The message content is passed unchanged. */
static BOOL native_name(id sets, id name) {
    for (NSUInteger s = 0; s < count(sets); s++) {
        id set = at(sets,s); if (!responds(set,"emotes")) continue;
        id emotes = m0(set,"emotes"); if (!kind(emotes,"NSArray")) continue;
        for (NSUInteger i = 0; i < count(emotes); i++) {
            id emote = at(emotes,i); if (!responds(emote,"token")) continue;
            id token = m0(emote,"token");
            if (responds(token,"exact") && ((BOOL (*)(id,SEL,id))objc_msgSend)(m0(token,"exact"),sel_registerName("isEqualToString:"),name)) return YES;
            if (responds(token,"regex")) {
                id pattern = m0(token,"regex");
                if (kind(pattern,"NSString")) {
                    id regex = ((id (*)(id,SEL,id,NSUInteger,id))objc_msgSend)((id)objc_getClass("NSRegularExpression"),sel_registerName("regularExpressionWithPattern:options:error:"),pattern,(NSUInteger)0,nil);
                    NSUInteger length = ((NSUInteger (*)(id,SEL))objc_msgSend)(name,sel_registerName("length"));
                    Range range = ((Range (*)(id,SEL,id,NSUInteger,Range))objc_msgSend)(regex,sel_registerName("rangeOfFirstMatchInString:options:range:"),name,(NSUInteger)0,(Range){0,length});
                    if (range.location == 0 && range.length == length) return YES;
                }
            }
        }
    }
    return NO;
}
static id send_message(id self, SEL sel, id user, id username, id channel, id content,
                        id sets, id badges, id reply, id info, id message, id nonce) {
    INC(g_sent_calls);
    id matches = tas_emotes_local_matches_copy(channel,content), augmented = nil;
    if (matches && kind(sets,"NSArray") && count(matches)) {
        id emotes = m0((id)objc_getClass("NSMutableArray"),"array");
        id names = m0(matches,"allKeys"), empty = m0((id)objc_getClass("NSArray"),"array");
        for (NSUInteger i = 0; i < count(names); i++) {
            id name = at(names,i); if (native_name(sets,name)) continue;
            id token = m1(m0((id)objc_getClass("KMPMCEmoteTokenExact"),"alloc"),"initWithExact:",name);
            id emote = ((id (*)(id,SEL,id,id,id))objc_msgSend)(m0((id)objc_getClass("KMPMCEmote"),"alloc"),sel_registerName("initWithId:token:modifiers:"),m1(matches,"objectForKey:",name),token,empty);
            if (emote) { v1(emotes,"addObject:",emote); INC(g_sent_matches); objc_release(emote); }
            if (token) objc_release(token);
        }
        if (count(emotes)) {
            id set = ((id (*)(id,SEL,id,id,id))objc_msgSend)(m0((id)objc_getClass("KMPMCEmoteSet"),"alloc"),sel_registerName("initWithId:emotes:ownerDisplayName:"),string("tas-third-party"),emotes,nil);
            if (set) { augmented = m0(sets,"mutableCopy"); v1(augmented,"addObject:",set); objc_release(set); }
        }
    }
    id result = ((id (*)(id,SEL,id,id,id,id,id,id,id,id,id,id))g_send)(self,sel,user,username,channel,content,augmented ?: sets,badges,reply,info,message,nonce);
    if (augmented) objc_release(augmented);
    if (matches) objc_release(matches);
    return result;
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
    /* KMP classes export these selectors dynamically at framework startup. */
    Class emote = objc_getClass("KMPMCEmote"), token = objc_getClass("KMPMCEmoteTokenExact"), set = objc_getClass("KMPMCEmoteSet");
    if (class_getInstanceMethod(emote,sel_registerName("initWithId:token:modifiers:")) &&
        class_getInstanceMethod(token,sel_registerName("initWithExact:")) &&
        class_getInstanceMethod(set,sel_registerName("initWithId:emotes:ownerDisplayName:")))
        hook(objc_getClass("KMPMCIrcSendMessageChannel"),"initWithUserId:username:channel:content:userEmoteSets:badgesTag:reply:chatUserInfo:messageId:clientNonce:",12,(IMP)send_message,&g_send);
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
        "Hooks (sent/chat size/base size/bounds/tap): %s/%s/%s/%s/%s\n"
        "Local message calls/matched emotes: %llu/%llu\n"
        "Proportional sizes/taps/provider sheets: %llu/%llu/%llu\n"
        "Tap snapshots/provider hits: %llu/%llu\n",
        g_send ? "installed" : "missing",g_size ? "installed" : "missing",g_base_size ? "installed" : "missing",g_bounds && g_set_bounds ? "installed" : "missing",g_tap ? "installed" : "missing",
        (unsigned long long)GET(g_sent_calls),(unsigned long long)GET(g_sent_matches),(unsigned long long)GET(g_sized),(unsigned long long)GET(g_tap_calls),(unsigned long long)GET(g_details),(unsigned long long)GET(g_snapshots),(unsigned long long)GET(g_tap_hits));
}
