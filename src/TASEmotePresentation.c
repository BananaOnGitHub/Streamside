/* Enrich native presentation definitions, never replace a message or its tokens.
 * Synthetic IDs deliberately join incoming emotes' image and geometry path. */
#include "TASEmotePresentation.h"
#include "TASEmotes.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef unsigned long U;
typedef long I;
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_storeWeak(id *,id);
extern id objc_loadWeakRetained(id *);
#define DATA_SOURCE "_TtC6Twitch14ChatDataSource"
#define TRANSCRIPT "_TtC6Twitch18ChatTranscriptView"
#define MANAGER "_TtC6Twitch12EmoteManager"
#define PRESENTATION "_TtC6Twitch17ChatMessageString"
#define MESSAGE "_TtC9TwitchKit13TWChatMessage"
#define TEXT_TOKEN "_TtC9TwitchKit18TWMessageTextToken"
#define DEFINITION "_TtC9TwitchKit11TKChatEmote"
#define SUBSCRIBER "currentChannelUnlockedSubscriberEmotesForMessageString:"
#define FOLLOWER "currentChannelUnlockedFollowerEmotesForMessageString:"
#define CONSTRUCTOR "initWithIdentifier:code:modifiedEmotes:assetType:"
static IMP originals[2],followers[2],manager_originals[3];
static id weak_manager; /* Live authority, never a cached account ID or room. */
static BOOL ambiguous_manager;
static pthread_mutex_t authority_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t calls[2],own_messages,definitions,scope_misses,unsafe_messages,identity_failures;
#define INC(v) ((void)__atomic_add_fetch(&(v),1,__ATOMIC_RELAXED))
#define GET(v) __atomic_load_n(&(v),__ATOMIC_RELAXED)
static id m0(id o,const char *s) { return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static id m1(id o,const char *s,id a) { return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a); }
static void v1(id o,const char *s,id a) { ((void (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a); }
static BOOL kind(id o,const char *s) { Class c=objc_getClass(s);return o && c && ((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),c); }
static BOOL responds(id o,const char *s) { return o && ((BOOL (*)(id,SEL,SEL))objc_msgSend)(o,sel_registerName("respondsToSelector:"),sel_registerName(s)); }
static BOOL flag(id o,const char *s) { return ((BOOL (*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static U count(id o) { return ((U (*)(id,SEL))objc_msgSend)(o,sel_registerName("count")); }
static id at(id o,U n) { return ((id (*)(id,SEL,U))objc_msgSend)(o,sel_registerName("objectAtIndex:"),n); }
static id str(const char *s) { return m1((id)objc_getClass("NSString"),"stringWithUTF8String:",(id)s); }
static BOOL equal(id a,id b) { return a && b && ((BOOL (*)(id,SEL,id))objc_msgSend)(a,sel_registerName("isEqual:"),b); }
static BOOL encoded(Class c,const char *name,const char *type) {
    Method m=c ? class_getInstanceMethod(c,sel_registerName(name)) : NULL;
    const char *actual=m ? method_getTypeEncoding(m) : NULL;
    return actual && !strcmp(actual,type);
}
/* Named field, next-field span, instance bounds and alignment all agree.
 * These inspected primitive/reference representations contain no Swift strings. */
static void *field(id o,const char *name,const char *next,size_t low,size_t high,size_t alignment) {
    if (!o) return NULL;
    Class c=object_getClass(o);Ivar iv=class_getInstanceVariable(c,name),end=class_getInstanceVariable(c,next);
    if (!iv || !end) return NULL;
    ptrdiff_t start=ivar_getOffset(iv),stop=ivar_getOffset(end);size_t size=class_getInstanceSize(c);
    if (start<(ptrdiff_t)sizeof(void *) || stop<start || (size_t)start%alignment ||
        (size_t)(stop-start)<low || (size_t)(stop-start)>high || (size_t)stop>size) return NULL;
    return (char *)o+start;
}
static uint32_t uint_field(id o,const char *name,const char *next,BOOL optional) {
    unsigned char *p=field(o,name,next,optional ? 5 : 4,8,4);
    if (!p || (optional && p[4]!=0)) return 0;
    uint32_t value=0;memcpy(&value,p,4);return value;
}
static id data_source_manager(id receiver) {
    if (!kind(receiver,DATA_SOURCE)) return nil;
    void *p=field(receiver,"emoteManager","currentTheme",sizeof(id),sizeof(id),sizeof(id));
    id manager=nil;if (p) memcpy(&manager,p,sizeof(manager));
    return kind(manager,MANAGER) ? manager : nil;
}
static void observe_manager(id manager) {
    if (!kind(manager,MANAGER)) return;
    pthread_mutex_lock(&authority_lock);
    id previous=objc_loadWeakRetained(&weak_manager);
    if (previous && previous!=manager) ambiguous_manager=YES;
    if (!previous) objc_storeWeak(&weak_manager,manager);
    objc_release(previous);pthread_mutex_unlock(&authority_lock);
}
static id manager_copy(id receiver) {
    id manager=data_source_manager(receiver);
    if (manager) { observe_manager(manager);return objc_retain(manager); }
    if (!kind(receiver,TRANSCRIPT)) return nil;
    pthread_mutex_lock(&authority_lock);
    manager=ambiguous_manager ? nil : objc_loadWeakRetained(&weak_manager);
    pthread_mutex_unlock(&authority_lock);return manager;
}
static uint32_t sender(id message) {
    id value=m0(message,"senderId");
    if (!kind(value,"NSNumber")) return 0;
    int64_t n=((int64_t (*)(id,SEL))objc_msgSend)(value,sel_registerName("longLongValue"));
    return n>0 && n<=UINT32_MAX ? (uint32_t)n : 0;
}
static BOOL definition_ready(void) {
    Class c=objc_getClass(DEFINITION);
    return encoded(c,CONSTRUCTOR,"@48@0:8@16@24@32q40") &&
        encoded(c,"identifier","@16@0:8") && encoded(c,"code","@16@0:8") &&
        encoded(c,"assetType","q16@0:8") && encoded(c,"isRegex","B16@0:8");
}
static BOOL native_codes(id list,id codes) {
    if (!kind(list,"NSArray") || count(list)>10000) return NO;
    for (U i=0,n=count(list);i<n;i++) {
        id emote=at(list,i);if (!kind(emote,DEFINITION)) return NO;
        id code=m0(emote,"code");if (!kind(code,"NSString")) return NO;
        v1(codes,"addObject:",code);
    }
    return YES;
}
static BOOL safe_tokens(id tokens,id codes) {
    if (!kind(tokens,"NSArray") || count(tokens)>128) return NO;
    Class text=objc_getClass(TEXT_TOKEN);if (!text) return NO;
    for (U i=0,n=count(tokens);i<n;i++) {
        id token=at(tokens,i);
        /* The native fallback matches before its moderation subclass branch. */
        if (kind(token,"_TtC9TwitchKit25TWMessageAutoModTextToken") ||
            kind(token,"_TtC9TwitchKit26TWMessageCensoredTextToken") ||
            (kind(token,TEXT_TOKEN) && object_getClass(token)!=text)) return NO;
        if (responds(token,"emoteText")) {
            id name=m0(token,"emoteText");if (kind(name,"NSString")) v1(codes,"addObject:",name);
        }
    }
    return YES;
}
static id definition_copy(id number,id name) {
    if (!kind(number,"NSString") || !kind(name,"NSString")) return nil;
    /* Twitch 31.5's ordinary token -> TKChatEmote conversion passes 1,
     * including five verified native call sites. This is not an animation flag. */
    id value=((id (*)(id,SEL,id,id,id,I))objc_msgSend)(m0((id)objc_getClass(DEFINITION),"alloc"),
        sel_registerName(CONSTRUCTOR),number,name,m0((id)objc_getClass("NSArray"),"array"),(I)1);
    /* Fail closed if a future constructor normalizes/replaces our identity. */
    if (!kind(value,DEFINITION) || !equal(m0(value,"identifier"),number) ||
        !equal(m0(value,"code"),name) || flag(value,"isRegex") ||
        ((I (*)(id,SEL))objc_msgSend)(value,sel_registerName("assetType"))!=1) {
        objc_release(value);INC(identity_failures);return nil;
    }
    return value;
}
static id enrich(id receiver,id presentation,id native,unsigned slot) {
    if (!tas_emotes_enabled_this_launch() || !kind(presentation,PRESENTATION) ||
        !responds(presentation,"chatMessage") || !definition_ready()) return native;
    id message=m0(presentation,"chatMessage");
    if (!kind(message,MESSAGE) || !responds(message,"senderId") || !responds(message,"messageTokens") ||
        !responds(message,"isHistoricalMessage") || !responds(message,"isFromOtherChannelInSharedChat") ||
        flag(message,"isHistoricalMessage") || flag(message,"isFromOtherChannelInSharedChat")) return native;
    uint32_t channel=uint_field(receiver,"channelID",slot ? "allowOpenURLHandling" : "emoteManager",slot!=0);
    id manager=manager_copy(receiver);
    uint32_t user=kind(manager,MANAGER) ? uint_field(manager,"currentUserID","recommendedEmotes",YES) : 0;
    objc_release(manager);
    if (!channel || !user) { INC(scope_misses);return native; }
    if (sender(message)!=user) return native;
    INC(own_messages);
    id tokens=m0(message,"messageTokens"),codes=m0((id)objc_getClass("NSMutableSet"),"set");
    if (!safe_tokens(tokens,codes)) { INC(unsafe_messages);return native; }
    /* Ask the saved native follower IMP for conflict codes. No provider work
     * is added to follower responses and no per-message snapshot is retained. */
    id follower=((id (*)(id,SEL,id))followers[slot])(receiver,sel_registerName(FOLLOWER),presentation);
    if (!native_codes(native,codes) || !native_codes(follower,codes)) return native;
    char room_text[16];snprintf(room_text,sizeof(room_text),"%u",channel);id room=str(room_text);
    id output=nil;U added=0;
    for (U i=0,n=count(tokens);i<n && added<64;i++) {
        id token=at(tokens,i);if (object_getClass(token)!=objc_getClass(TEXT_TOKEN) || !responds(token,"text")) continue;
        id text=m0(token,"text");
        if (!kind(text,"NSString") || ((U (*)(id,SEL))objc_msgSend)(text,sel_registerName("length"))>4096) continue;
        /* The inspected native matcher splits on literal U+0020, not general
         * whitespace. Use that exact boundary so tab/punctuation stay literal. */
        id words=m1(text,"componentsSeparatedByString:",str(" "));
        if (!kind(words,"NSArray") || count(words)>512) continue;
        for (U j=0,k=count(words);j<k && added<64;j++) {
            id name=at(words,j);if (!kind(name,"NSString") || ((U (*)(id,SEL))objc_msgSend)(name,sel_registerName("length"))>96 ||
                ((BOOL (*)(id,SEL,id))objc_msgSend)(codes,sel_registerName("containsObject:"),name)) continue;
            id metadata=tas_emotes_named_copy(room,name);
            id raw_number=kind(metadata,"NSDictionary") ? m1(metadata,"objectForKey:",str("id")) : nil;
            id number=kind(raw_number,"NSNumber") &&
                ((uint64_t (*)(id,SEL))objc_msgSend)(raw_number,sel_registerName("unsignedLongLongValue"))>=9000000000ULL ?
                m0(raw_number,"description") : nil;
            id emote=definition_copy(number,name);objc_release(metadata);
            if (!emote) continue;
            if (!output) output=m0(native,"mutableCopy");
            v1(output,"addObject:",emote);objc_release(emote);v1(codes,"addObject:",name);added++;INC(definitions);
        }
    }
    return output ? m0(output,"autorelease") : native;
}
static id data_subscriber(id self,SEL sel,id presentation) {
    INC(calls[0]);id native=((id (*)(id,SEL,id))originals[0])(self,sel,presentation);
    return enrich(self,presentation,native,0);
}
static id transcript_subscriber(id self,SEL sel,id presentation) {
    INC(calls[1]);id native=((id (*)(id,SEL,id))originals[1])(self,sel,presentation);
    return enrich(self,presentation,native,1);
}
static void manager_update(id self,SEL sel) { ((void (*)(id,SEL))manager_originals[0])(self,sel);observe_manager(self); }
static void manager_logout(id self,SEL sel) { ((void (*)(id,SEL))manager_originals[1])(self,sel);observe_manager(self); }
static void manager_request(id self,SEL sel) { ((void (*)(id,SEL))manager_originals[2])(self,sel);observe_manager(self); }
static BOOL install(Class c,const char *s,const char *encoding,IMP replacement,IMP *original) {
    if (*original) return YES;
    if (!encoded(c,s,encoding)) return NO;
    Method m=class_getInstanceMethod(c,sel_registerName(s));*original=method_getImplementation(m);
    if (!class_addMethod(c,sel_registerName(s),replacement,encoding)) method_setImplementation(m,replacement);
    return YES;
}
void tas_emote_presentation_retry_hooks(void) {
    if (!tas_emotes_enabled_this_launch() || !definition_ready()) return;
    const char *classes[]={DATA_SOURCE,TRANSCRIPT};IMP replacements[]={(IMP)data_subscriber,(IMP)transcript_subscriber};
    for (unsigned i=0;i<2;i++) {
        Class c=objc_getClass(classes[i]);
        if (!encoded(c,FOLLOWER,"@24@0:8@16") || !encoded(c,SUBSCRIBER,"@24@0:8@16")) continue;
        if (!followers[i]) followers[i]=method_getImplementation(class_getInstanceMethod(c,sel_registerName(FOLLOWER)));
        install(c,SUBSCRIBER,"@24@0:8@16",replacements[i],&originals[i]);
    }
    /* The shared manager registers these account-notification selectors in
     * its native initializer. Observe a weak live reference; reread currentUserID
     * on every render. Multiple observed live managers disable transcript scope. */
    Class manager=objc_getClass(MANAGER);
    install(manager,"userIsAvailableOrUpdated","v16@0:8",(IMP)manager_update,&manager_originals[0]);
    install(manager,"userDidLogOut","v16@0:8",(IMP)manager_logout,&manager_originals[1]);
    install(manager,"requestUserEmoteSetsUpdate","v16@0:8",(IMP)manager_request,&manager_originals[2]);
}
void tas_emote_presentation_status(char *buffer,size_t capacity) {
    if (!buffer || !capacity) return;
    snprintf(buffer,capacity,"Native presentation hooks (data source/transcript/account): %s/%s/%s\n"
        "Presentation callbacks (data source/transcript)/own messages/provider definitions: %llu/%llu/%llu/%llu\n"
        "Presentation skips (scope/unsafe text/identity): %llu/%llu/%llu\n",
        originals[0] ? "installed" : "missing",originals[1] ? "installed" : "missing",
        manager_originals[0] && manager_originals[1] && manager_originals[2] ? "installed" : "missing",
        (unsigned long long)GET(calls[0]),(unsigned long long)GET(calls[1]),(unsigned long long)GET(own_messages),
        (unsigned long long)GET(definitions),(unsigned long long)GET(scope_misses),(unsigned long long)GET(unsafe_messages),
        (unsigned long long)GET(identity_failures));
}
