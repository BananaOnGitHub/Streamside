/* Exact Twitch 32 native feed adapter. No request credentials or Swift field
 * offsets cross this boundary. Concrete register lowering was inspected in the
 * donor; metadata, conformances and value witnesses come from Swift's runtime. */
#include "SSNFeed.h"
#include "SSNIntegration.h"
#include "SSNCore.h"
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

static bool initialized,available;
static const void *response_type,*stream_type,*game_type,*thumb_type,*date_type,*url_optional;
static const void *user_type,*string_type,*optional_game,*objc_type,*promise_type;
static const void *track_live,*track_user,*array_live,*array_user,*set_type;
static uintptr_t empty_set;
static Bridge bridge;
static bool (*cast)(void*,void*,const void*,const void*,uintptr_t);
static PersonalRequest personal;
static SectionsGetter live_getter,offline_getter;
static ItemGetter item_getter;
static Getter broadcaster_getter,game_getter,date_getter;
static ThumbnailsGetter stream_thumbnails,profile_thumbnails;
static ThumbnailGetter thumbnail_url;
static StringGetter title_getter,game_name;
static IntegerGetter viewers_getter;
static SW uint8_t (*watchable)(const void * CTX),(*blur_reason)(const void * CTX);

static const uintptr_t *witness(const void *type) { return type?((const uintptr_t*const*)type)[-1]:NULL; }
static size_t size_of(const void *type) {
    const uintptr_t *w=witness(type);
    if(!w||!w[8]||w[8]>65536||w[9]<w[8]||(w[10]&255)>15||(w[10]&(0x00100000|0x00400000|0x00800000))) return 0;
    return w[8];
}
static void *storage(const void *type) { size_t n=size_of(type); return n?calloc(1,n):NULL; }
static void release_value(void *value,const void *type) { ((Destroy)witness(type)[1])(value,type); }
static void dispose(void *value,const void *type) { if(value) { release_value(value,type); free(value); } }
static const void *meta(const char *name,bool system) {
    Meta accessor=(Meta)(system?dlsym(RTLD_DEFAULT,name):ssn_resolve(name));
    if(!accessor) return NULL;
    Response result=accessor(0);
    return !result.state&&size_of(result.value)?result.value:NULL;
}
static id failure(void) { ssn_failure(3); return m0(c("NSNull"),"new"); }
static id string_value(StringGetter getter,const void *value,size_t limit) {
    Words2 result=getter(value); id text=bridge(&result,string_type);
    release_value(&result,string_type);
    if(!kind(text,"NSString")||num(text,"length")>limit) { objc_release(text); return nil; }
    return text;
}
static id image_url(const void *value,ThumbnailsGetter getter,uint8_t size) {
    Words3 thumbnails=getter(value);
    void *url=storage(url_optional);
    if(!url) { release_value(&thumbnails,thumb_type); return nil; }
    thumbnail_url(url,size,thumbnails.a,thumbnails.b,thumbnails.c);
    id result=bridge(url,url_optional); dispose(url,url_optional);
    release_value(&thumbnails,thumb_type);
    id text=kind(result,"NSURL")?m0(result,"absoluteString"):nil;
    text=kind(text,"NSString")&&num(text,"length")<=2048?objc_retain(text):nil;
    objc_release(result); return text;
}

static bool initialize(PairMeta promise,const void *error) {
    if(initialized) return available;
    initialized=true;
    if(!promise||!error) return false;
    bridge=(Bridge)dlsym(RTLD_DEFAULT,"$ss27_bridgeAnythingToObjectiveCyyXlxlF");
    cast=dlsym(RTLD_DEFAULT,"swift_dynamicCast");
    const void *(*objc_meta)(Class)=dlsym(RTLD_DEFAULT,"swift_getObjCClassMetadata");
    const void *(*conformance)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    GenericMeta array=dlsym(RTLD_DEFAULT,"$sSaMa"),optional=dlsym(RTLD_DEFAULT,"$sSqMa");
    PairMeta set=dlsym(RTLD_DEFAULT,"$sShMa");
    PairMeta track=(PairMeta)ssn_resolve("$s19TwitchAnalyticsCore13TrackableItemVMa");
    response_type=meta("$s9TwitchKit9TKGraphQLC24PersonalSectionsResponseVMa",false);
    stream_type=meta("$s10TwitchCore10LiveStreamVMa",false);
    user_type=meta("$s10TwitchCore4UserVMa",false);
    game_type=meta("$s10TwitchCore4GameVMa",false);
    thumb_type=meta("$s10TwitchCore10ThumbnailsVMa",false);
    date_type=meta("$s10Foundation4DateVMa",true);
    const void *url_type=meta("$s10Foundation3URLVMa",true);
    string_type=dlsym(RTLD_DEFAULT,"$sSSN");
    personal=(PersonalRequest)ssn_resolve("$s9TwitchKit9TKGraphQLC16personalSections25currentPlayingChannelName5order14blockedUserIDs12Tomorrowland7PromiseVyAC08PersonalF8ResponseV0A6Apollo0A12GraphQLErrorVGSSSg_AA28FollowedLiveStreamsSortOrderOShys6UInt32VGtF");
    live_getter=(SectionsGetter)ssn_resolve("$s9TwitchKit9TKGraphQLC24PersonalSectionsResponseV4liveSay0A13AnalyticsCore13TrackableItemVy0aJ010LiveStreamVGGvg");
    offline_getter=(SectionsGetter)ssn_resolve("$s9TwitchKit9TKGraphQLC24PersonalSectionsResponseV7offlineSay0A13AnalyticsCore13TrackableItemVy0aJ04UserVGGvg");
    item_getter=(ItemGetter)ssn_resolve("$s19TwitchAnalyticsCore13TrackableItemV4itemxvg");
    broadcaster_getter=(Getter)ssn_resolve("$s10TwitchCore10LiveStreamV11broadcasterAA4UserVvg");
    game_getter=(Getter)ssn_resolve("$s10TwitchCore10LiveStreamV4gameAA4GameVSgvg");
    date_getter=(Getter)ssn_resolve("$s10TwitchCore10LiveStreamV9createdAt10Foundation4DateVvg");
    stream_thumbnails=(ThumbnailsGetter)ssn_resolve("$s10TwitchCore10LiveStreamV10thumbnailsAA10ThumbnailsVvg");
    profile_thumbnails=(ThumbnailsGetter)ssn_resolve("$s10TwitchCore4UserV13profileImagesAA10ThumbnailsVvg");
    thumbnail_url=(ThumbnailGetter)ssn_resolve("$s10TwitchCore10ThumbnailsVy10Foundation3URLVSgAA9ThumbnailV4SizeOcig");
    title_getter=(StringGetter)ssn_resolve("$s10TwitchCore10LiveStreamV5titleSSvg");
    game_name=(StringGetter)ssn_resolve("$s10TwitchCore4GameV11displayNameSSvg");
    viewers_getter=(IntegerGetter)ssn_resolve("$s10TwitchCore10LiveStreamV12viewersCountSivg");
    watchable=(void*)ssn_resolve("$s10TwitchCore10LiveStreamV19currentUserCanWatchSbvg");
    blur_reason=(void*)ssn_resolve("$s10TwitchCore10LiveStreamV19thumbnailBlurReasonAA09ThumbnailfG0Ovg");
    if(!bridge||!cast||!objc_meta||!conformance||!array||!optional||!set||!track||
       !stream_type||!user_type||!game_type||!date_type||!url_type||size_of(string_type)!=16||
       size_of(response_type)!=16||size_of(thumb_type)!=24||!personal||!live_getter||!offline_getter||
       !item_getter||!broadcaster_getter||!game_getter||!date_getter||!stream_thumbnails||!profile_thumbnails||
       !thumbnail_url||!title_getter||!game_name||!viewers_getter||!watchable||!blur_reason) return false;
    const void *eq=dlsym(RTLD_DEFAULT,"$sSQMp"),*hash=dlsym(RTLD_DEFAULT,"$sSHMp"),*uint=dlsym(RTLD_DEFAULT,"$ss6UInt32VN");
    const void *live_eq=eq?conformance(stream_type,eq):NULL,*user_eq=eq?conformance(user_type,eq):NULL;
    const void *uint_hash=uint&&hash?conformance(uint,hash):NULL;
    if(!live_eq||!user_eq||!uint_hash) return false;
    Response tl=track(0,stream_type,live_eq),tu=track(0,user_type,user_eq);
    if(tl.state||tu.state||!size_of(tl.value)||!size_of(tu.value)) return false;
    track_live=tl.value; track_user=tu.value;
    Response al=array(0,track_live),au=array(0,track_user),og=optional(0,game_type),ou=optional(0,url_type);
    Response se=set(0,uint,uint_hash),pr=promise(0,response_type,error);
    if(al.state||au.state||og.state||ou.state||se.state||pr.state||size_of(al.value)!=8||size_of(au.value)!=8||
       !size_of(og.value)||!size_of(ou.value)||size_of(se.value)!=8||size_of(pr.value)!=8) return false;
    array_live=al.value;array_user=au.value;optional_game=og.value;url_optional=ou.value;set_type=se.value;promise_type=pr.value;
    objc_type=objc_meta(objc_getClass("NSObject"));
    id empty=m0(c("NSSet"),"set");
    if(!objc_type||!cast(&empty_set,&empty,objc_meta(objc_getClass("NSSet")),set_type,0)) return false;
    available=true;return true;
}
const void *ssn_feed_promise_type(PairMeta promise,const void *error) { return initialize(promise,error)?promise_type:NULL; }
void ssn_feed_request(void *out,id graph) {
    /* nil Optional<String>, inspected enum tag 0 = recommended, native empty Set.
     * Presentation sorts returned live channels by viewers, with stable ties. */
    personal(out,0,0,0,empty_set,graph);
}
static id channel_dictionary(const void *value,bool live) {
    void *user=live?storage(user_type):NULL;
    if(live && !user) return failure();
    if(live) broadcaster_getter(user,value);
    const void *user_value=live?user:value;
    id result=ssn_user_dictionary(user_value);
    if(!kind(result,"NSDictionary")) { dispose(user,user_type); return result; }
    id avatar=image_url(user_value,profile_thumbnails,1);
    if(avatar) { put(result,"avatarURL",avatar); objc_release(avatar); }
    put(result,"isLive",ns(live?"1":"0"));
    if(live) {
        id title=string_value(title_getter,value,4096);
        intptr_t viewers=viewers_getter(value);
        void *date=storage(date_type),*game=storage(optional_game);
        if(!title||viewers<0||!date||!game) {
            objc_release(title);free(date);free(game);objc_release(result);dispose(user,user_type);return failure();
        }
        put(result,"title",title);objc_release(title);
        char number[80];snprintf(number,sizeof(number),"%lld",(long long)viewers);put(result,"viewerCount",ns(number));
        date_getter(date,value);id date_object=bridge(date,date_type);dispose(date,date_type);
        if(!kind(date_object,"NSDate")) { objc_release(date_object);free(game);objc_release(result);dispose(user,user_type);return failure(); }
        double started=((double(*)(id,SEL))objc_msgSend)(date_object,ss("timeIntervalSince1970"));objc_release(date_object);
        if(isfinite(started)&&started>0) { snprintf(number,sizeof(number),"%.3f",started);put(result,"startedAt",ns(number)); }
        game_getter(game,value);id game_box=bridge(game,optional_game);dispose(game,optional_game);
        if(game_box && !kind(game_box,"NSNull")) {
            void *unwrapped=storage(game_type);
            if(!unwrapped||!cast(unwrapped,&game_box,objc_type,game_type,0)) {
                free(unwrapped);objc_release(game_box);objc_release(result);dispose(user,user_type);return failure();
            }
            id category=string_value(game_name,unwrapped,512);dispose(unwrapped,game_type);
            if(!category) { objc_release(game_box);objc_release(result);dispose(user,user_type);return failure(); }
            put(result,"category",category);objc_release(category);
        }
        objc_release(game_box);
        /* Preserve the donor's watch and thumbnail-blur decisions. Enum case 2
         * is blurNotRequired, admitted from this exact image's field descriptor. */
        if(watchable(value) && blur_reason(value)==2) {
            id preview=image_url(value,stream_thumbnails,2);
            if(preview) { put(result,"thumbnailURL",preview);objc_release(preview); }
        } else put(result,"thumbnailRestricted",ns("1"));
    }
    dispose(user,user_type);return result;
}
static bool append_items(id result,uintptr_t raw,const void *array_type,const void *track_type,const void *value_type,bool live) {
    id source=bridge(&raw,array_type);release_value(&raw,array_type);
    if(!kind(source,"NSArray")||num(source,"count")>10000) { objc_release(source);return false; }
    for(uintptr_t i=0;i<num(source,"count");i++) {
        id boxed=at(source,i);void *track=storage(track_type),*value=storage(value_type);
        if(!track||!value||!cast(track,&boxed,objc_type,track_type,0)) {
            free(track);free(value);objc_release(source);return false;
        }
        item_getter(value,track_type,track);dispose(track,track_type);
        id item=channel_dictionary(value,live);dispose(value,value_type);
        if(!kind(item,"NSDictionary")) { objc_release(item);objc_release(source);return false; }
        v1(result,"addObject:",item);objc_release(item);
    }
    objc_release(source);return true;
}
id SW ssn_feed_map(const void *value,void *context CTX) {
    (void)context;if(!available) return failure();
    /* The inspected concrete response is lowered as two direct integer words.
     * These are the complete ABI value, not guessed Swift field offsets. */
    Words2 words;memcpy(&words,value,sizeof(words));
    uintptr_t live=live_getter(words.a,words.b),offline=offline_getter(words.a,words.b);
    id result=m0(c("NSMutableArray"),"new");
    bool success=append_items(result,live,array_live,track_live,stream_type,true);
    bool other=append_items(result,offline,array_user,track_user,user_type,false);
    if(!success||!other) { objc_release(result);return failure(); }
    return result;
}
