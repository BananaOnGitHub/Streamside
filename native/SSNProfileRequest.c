/* Exact donor adapter: native Apollo, runtime metadata/value witnesses and
 * concrete inspected register lowering. No Swift field or witness-slot guesses. */
#include "SSNProfileRequest.h"
#include "SSNSwiftABI.h"
#include "SSNPlaybackRequest.h"
#include "SSNIntegration.h"
#include <dlfcn.h>
#include <stdlib.h>
#include <dispatch/dispatch.h>
struct Operation { const char *query,*data,*factory;const char *root;const void *q,*d,*promise,*witness,*mutation_result; };
static struct Operation ops[5]={
    {.root="$s16TwitchGraphQLAPI29ProfileInfoFromChannelIDQueryC4DataV6__data9ApolloAPI0I4DictVvg",.query="$s16TwitchGraphQLAPI29ProfileInfoFromChannelIDQueryCMa",.data="$s16TwitchGraphQLAPI29ProfileInfoFromChannelIDQueryC4DataVMa",.factory=NULL},
    {.root="$s16TwitchGraphQLAPI23UserFollowingStateQueryC4DataV6__data9ApolloAPI0H4DictVvg",.query="$s16TwitchGraphQLAPI23UserFollowingStateQueryCMa",.data="$s16TwitchGraphQLAPI23UserFollowingStateQueryC4DataVMa",.factory=NULL},
    {.root="$s16TwitchGraphQLAPI20UnfollowUserMutationC4DataV6__data9ApolloAPI0G4DictVvg",.query="$s16TwitchGraphQLAPI20UnfollowUserMutationCMa",.data="$s16TwitchGraphQLAPI20UnfollowUserMutationC4DataVMa",.factory="$s16TwitchGraphQLAPI20UnfollowUserMutationC5inputAcA0dE5InputV_tcfC"},
    {.root="$s16TwitchGraphQLAPI18FollowUserMutationC4DataV6__data9ApolloAPI0G4DictVvg",.query="$s16TwitchGraphQLAPI18FollowUserMutationCMa",.data="$s16TwitchGraphQLAPI18FollowUserMutationC4DataVMa",.factory="$s16TwitchGraphQLAPI18FollowUserMutationC5inputAcA0dE5InputV_tcfC"},
    {.root="$s16TwitchGraphQLAPI38SetLiveNotificationsEnrollmentMutationC4DataV6__data9ApolloAPI0I4DictVvg",.query="$s16TwitchGraphQLAPI38SetLiveNotificationsEnrollmentMutationCMa",.data="$s16TwitchGraphQLAPI38SetLiveNotificationsEnrollmentMutationC4DataVMa",.factory="$s16TwitchGraphQLAPI38SetLiveNotificationsEnrollmentMutationC5inputAcA0defG5InputV_tcfC"},
};
static const void *dict_type,*data_type,*objc_type,*string_type,*error_type,*error_witness,*notify_enum,*notify_witness,*notify_value;
typedef SW Words2 (*EnumRawValue)(const void *type, const void *value CTX);
static EnumRawValue notification_raw_value;
static const void *panel_type,*panel_array_types[3];
static PlaybackField panel_data;
static Bridge bridge;static PlaybackField dict_getter;static ApolloClientGetter client_getter;
static SW Words2 (*from_string)(id);static bool (*cast)(void*,void*,const void*,const void*,uintptr_t);
static void (*release_object)(uintptr_t);static PromiseObjC promise_objc;static PairMeta promise_meta;
static PlaybackFetch fetch;static Perform perform;static PackedMeta result_meta;static Unwrap unwrap;
static bool initialized,available;
static const void *enum_value_type(const char *name,const void **payload,const void **witness);
static const uintptr_t *vw(const void *t) { return t?((const uintptr_t*const*)t)[-1]:NULL; }
static bool sized(const void *t,size_t n) { const uintptr_t *w=vw(t);return w&&w[8]==n&&w[9]>=n&&(w[10]&255)<=15; }
static void destroy(void *v,const void *t) { ((Destroy)vw(t)[1])(v,t); }
static const void *meta(const char *name) { Meta fn=(Meta)ssn_resolve(name);if(!fn)return NULL;Response x=fn(0);return x.state?NULL:x.value; }
static id failed(void) { return m0(c("NSNull"),"new"); }
id ssn_profile_unbox(id object) {
    uintptr_t raw=0;
    if(!object||!available||!cast(&raw,&object,objc_type,data_type,0)) return nil;
    uintptr_t dict=dict_getter(raw);destroy(&raw,data_type);
    id result=bridge(&dict,dict_type);destroy(&dict,dict_type);return result;
}
/* Use Apollo's existing value witnesses to turn a generated Panel or an
 * opaque array of nullable panel values into Foundation containers. */
id ssn_profile_unbox_panel(id object) {
    uintptr_t panel=0;
    if(!available||!panel_data||!sized(panel_type,8)||!cast(&panel,&object,objc_type,panel_type,0))return nil;
    uintptr_t raw=panel_data(panel);
    destroy(&panel,panel_type);
    uintptr_t dictionary=dict_getter(raw);
    destroy(&raw,data_type);
    id result=bridge(&dictionary,dict_type);
    destroy(&dictionary,dict_type);
    return result;
}
id ssn_profile_unbox_panel_list(id object) {
    if(!available)return nil;
    for(unsigned i=0;i<sizeof(panel_array_types)/sizeof(panel_array_types[0]);i++) {
        const void *type=panel_array_types[i];
        uintptr_t array=0;
        if(!sized(type,8)||!cast(&array,&object,objc_type,type,0))continue;
        id result=bridge(&array,type);
        destroy(&array,type);
        if(kind(result,"NSArray"))return result;
        objc_release(result);
    }
    return nil;
}
/* DataDict bridges GraphQLEnum as an opaque Swift value. Cast only the donor's
 * concrete notification enum and get its String through Apollo's accessor. */
id ssn_profile_notification_string(id object) {
    _Alignas(16) unsigned char storage[24];
    if(!available||!notification_raw_value||!sized(notify_value,17)||
       !cast(storage,&object,objc_type,notify_value,0))return nil;
    Words2 raw=notification_raw_value(notify_value,storage);
    destroy(storage,notify_value);
    id string=bridge(&raw,string_type);
    destroy(&raw,string_type);
    return string;
}
static id map_data(const void *value,unsigned operation) {
    ssn_profile_event(operation,SSN_PROFILE_MAPPED);
    PlaybackField root_getter=(void*)ssn_resolve(ops[operation].root);
    uintptr_t raw=root_getter(*(const uintptr_t*)value);
    uintptr_t dict=dict_getter(raw);destroy(&raw,data_type);
    id boxed=bridge(&dict,dict_type);destroy(&dict,dict_type);
    id result=ssn_profile_normalize(boxed);objc_release(boxed);
    if(!result)ssn_profile_event(operation,SSN_PROFILE_NORMALIZATION_FAILED);
    else if(operation==0)ssn_profile_event(operation,ssn_profile_panel_stage(result));
    return result?:failed();
}
/* A Swift thick closure context is Swift-managed storage. Never give it a
 * pointer to a C operation record; capture-free entry points use NULL instead. */
#define PROFILE_MAP(N) \
static id SW map##N(const void *value,void *context CTX) { (void)context;return map_data(value,N); } \
static id SW error##N(const void *value,void *context CTX) { (void)value;(void)context;ssn_profile_event(N,SSN_PROFILE_NATIVE_ERROR);return failed(); }
PROFILE_MAP(0)
PROFILE_MAP(1)
PROFILE_MAP(2)
PROFILE_MAP(3)
PROFILE_MAP(4)
#undef PROFILE_MAP
static const Map value_maps[]={map0,map1,map2,map3,map4},error_maps[]={error0,error1,error2,error3,error4};
static void SW unwrap2(void* OUT out,const void *value,void *context CTX) { (void)context;unwrap(out,ops[2].mutation_result,value); }
static void SW unwrap3(void* OUT out,const void *value,void *context CTX) { (void)context;unwrap(out,ops[3].mutation_result,value); }
static void SW unwrap4(void* OUT out,const void *value,void *context CTX) { (void)context;unwrap(out,ops[4].mutation_result,value); }
static bool initialize(void) {
    if(initialized)return available;initialized=true;
    bridge=dlsym(RTLD_DEFAULT,"$ss27_bridgeAnythingToObjectiveCyyXlxlF");
    from_string=dlsym(RTLD_DEFAULT,"$sSS10FoundationE36_unconditionallyBridgeFromObjectiveCySSSo8NSStringCSgFZ");
    cast=dlsym(RTLD_DEFAULT,"swift_dynamicCast");release_object=dlsym(RTLD_DEFAULT,"swift_release");
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    const void *(*objc_meta)(Class)=dlsym(RTLD_DEFAULT,"swift_getObjCClassMetadata");
    data_type=meta("$s9ApolloAPI8DataDictVMa");string_type=dlsym(RTLD_DEFAULT,"$sSSN");
    error_type=meta("$s12TwitchApollo0A12GraphQLErrorVMa");
    const void *hashable=dlsym(RTLD_DEFAULT,"$ss11AnyHashableVN"),*hash_protocol=dlsym(RTLD_DEFAULT,"$sSHMp");
    Meta3 dictionary=dlsym(RTLD_DEFAULT,"$sSDMa");
    dict_getter=(void*)ssn_resolve("$s9ApolloAPI8DataDictV5_dataSDySSs11AnyHashableVGvg");client_getter=(void*)ssn_resolve("$s9TwitchKit9TKGraphQLC12apolloClientAA08TWApolloF0Vvg");
    promise_objc=(void*)ssn_resolve("$s12Tomorrowland7PromiseV4objc8mapValue0D5ErrorSo10TWLPromiseCyqd__qd_0_Gqd__xc_qd_0_q_ctRld__CRld_0_Cr0_lF");promise_meta=(void*)ssn_resolve("$s12Tomorrowland7PromiseVMa");fetch=(void*)ssn_resolve("$s9TwitchKit14TWApolloClientV14fetchAsPromise5query11cachePolicy12Tomorrowland0G0Vy4DataQz0A6Apollo0A12GraphQLErrorVGx_0M005CacheJ0Ot0M3API0N7QLQueryRzlF");
    perform=(void*)ssn_resolve("$s9TwitchKit14TWApolloClientV16performAsPromise8mutation5queue7mapping12Tomorrowland0G0Vyq_q0_Gx_So012OS_dispatch_I0C0A6Apollo0A13GraphQLResultOyq_q0_GAN0O16QLMutationResultVy4DataQzAN0aO7QLErrorVGct0N3API0oQ0RzAN0oT8ProtocolR0_r1_lF");result_meta=(void*)ssn_resolve("$s12TwitchApollo21GraphQLMutationResultVMa");unwrap=(void*)ssn_resolve("$s12TwitchApollo21GraphQLMutationResultV9unwrappedAA0aC8QLResultOyxq_Gvg");
    const void *error_protocol=ssn_resolve("$s12TwitchApollo20GraphQLErrorProtocolMp"),*root_protocol=ssn_resolve("$s9ApolloAPI16RootSelectionSetMp");
    if(!bridge||!from_string||!cast||!release_object||!conforms||!objc_meta||!dictionary||!hashable||!hash_protocol||!error_type||!error_protocol||!root_protocol||
       !sized(data_type,8)||!sized(string_type,16)||!dict_getter||!client_getter||!promise_objc||!promise_meta||!fetch||!perform||!result_meta||!unwrap) return false;
    const void *hash_witness=conforms(string_type,hash_protocol);if(!hash_witness)return false;
    Response dict=dictionary(0,string_type,hashable,hash_witness);if(dict.state||!sized(dict.value,8))return false;dict_type=dict.value;
    objc_type=objc_meta(objc_getClass("NSObject"));error_witness=conforms(error_type,error_protocol);if(!objc_type||!error_witness)return false;
    for(unsigned i=0;i<5;i++) {
        struct Operation *op=&ops[i];op->q=meta(op->query);op->d=meta(op->data);
        const void *protocol=ssn_resolve(i<2?"$s9ApolloAPI12GraphQLQueryMp":"$s9ApolloAPI15GraphQLMutationMp");
        if(!ssn_resolve(op->root)||!sized(op->q,8)||!sized(op->d,8)||!protocol)return false;
        op->witness=conforms(op->q,protocol);Response promise=promise_meta(0,op->d,error_type);
        if(!op->witness||promise.state||!sized(promise.value,8))return false;op->promise=promise.value;
        if(i>=2) {
            const void *data_witness=conforms(op->d,root_protocol);if(!data_witness)return false;
            const void *arguments[]={op->d,error_type,data_witness,error_witness};
            Response result=result_meta(0,arguments);
            if(result.state||!vw(result.value)||vw(result.value)[8]>65536)return false;op->mutation_result=result.value;
        }
    }
    panel_type=meta("$s16TwitchGraphQLAPI19ProfileInfoFragmentV5PanelVMa");
    panel_data=(PlaybackField)ssn_resolve("$s16TwitchGraphQLAPI19ProfileInfoFragmentV5PanelV6__data9ApolloAPI8DataDictVvg");
    GenericMeta array_meta=(GenericMeta)dlsym(RTLD_DEFAULT,"$sSaMa");
    GenericMeta optional_meta=(GenericMeta)dlsym(RTLD_DEFAULT,"$sSqMa");
    if(array_meta&&optional_meta&&panel_type) {
        Response hashable_optional=optional_meta(0,hashable),panel_optional=optional_meta(0,panel_type);
        const void *elements[]={hashable,hashable_optional.state?NULL:hashable_optional.value,
                               panel_optional.state?NULL:panel_optional.value};
        for(unsigned i=0;i<sizeof(elements)/sizeof(elements[0]);i++) {
            if(!elements[i])continue;
            Response array=array_meta(0,elements[i]);
            if(!array.state)panel_array_types[i]=array.value;
        }
    }
    notify_value=enum_value_type("$s16TwitchGraphQLAPI38FollowsChannelNotificationSettingStateOMa",&notify_enum,&notify_witness);
    notification_raw_value=(EnumRawValue)ssn_resolve("$s9ApolloAPI11GraphQLEnumO8rawValueSSvg");
    available=true;return true;
}
/* Native nil-literal initializer constructs .none, not a synthesized enum tag.
 * Its concrete Bool and Array carrier widths were inspected in query init. */
static bool none_value(const void *payload,size_t width,void *out) {
    GenericMeta nullable=(void*)ssn_resolve("$s9ApolloAPI15GraphQLNullableOMa");NilValue nil_value=(void*)ssn_resolve("$s9ApolloAPI15GraphQLNullableO10nilLiteralACyxGyt_tcfC");
    if(!payload||!nullable||!nil_value)return false;
    Response value=nullable(0,payload);if(value.state||!sized(value.value,width))return false;
    nil_value(out,payload);return true;
}
/* Apollo's Boolean-literal initializer uses the payload's single-payload
 * enum store witness with tag 0 and two empty cases for .some(true).
 * Validate the actual Bool and nullable widths before constructing that value. */
static bool viewer_state_enabled(uint8_t *out) {
    const void *boolean=dlsym(RTLD_DEFAULT,"$sSbN");
    GenericMeta nullable=(void*)ssn_resolve("$s9ApolloAPI15GraphQLNullableOMa");
    if(!sized(boolean,1)||!nullable)return false;
    Response type=nullable(0,boolean);
    if(type.state||!sized(type.value,1))return false;
    const uintptr_t *w=vw(boolean);
    StoreTag store=(StoreTag)w[7];GetTag get_tag=(GetTag)w[6];
    if(!store||!get_tag)return false;
    *out=1;
    store(out,0,2,boolean);
    return *out==1&&get_tag(out,2,boolean)==0;
}
static const void *enum_value_type(const char *name,const void **payload,const void **witness) {
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    PairMeta generic=(void*)ssn_resolve("$s9ApolloAPI11GraphQLEnumOMa");
    *payload=meta(name);const void *protocol=ssn_resolve("$s9ApolloAPI8EnumTypeMp");
    if(!*payload||!protocol||!conforms||!generic)return NULL;*witness=conforms(*payload,protocol);if(!*witness)return NULL;
    Response value=generic(0,*payload,*witness);return value.state?NULL:value.value;
}
id ssn_profile_request(id channel,unsigned operation,id setting) {
    if(operation>4)return nil;
    if(!ssn_playback_authorized()) { ssn_profile_event(operation,SSN_PROFILE_SESSION_CHANGED);return nil; }
    if(!initialize()) { ssn_profile_event(operation,SSN_PROFILE_UNAVAILABLE);return nil; }
    ssn_profile_event(operation,SSN_PROFILE_ABI_READY);
    if(!kind(channel,"NSString")||!num(channel,"length")||num(channel,"length")>128)return nil;
    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance");if(!graph)return nil;
    struct Operation *op=&ops[operation];Words2 name=from_string(channel);uintptr_t query=0;
    if(operation==0) {
        uint8_t flag=0,viewer=0;uintptr_t stories=0,codecs=0;Words2 country={0};const void *p=NULL,*w=NULL;
        GenericMeta array=dlsym(RTLD_DEFAULT,"$sSaMa");
        const void *s=enum_value_type("$s16TwitchGraphQLAPI22StoryFeatureCapabilityOMa",&p,&w),*v=enum_value_type("$s16TwitchGraphQLAPI10VideoCodecOMa",&p,&w);
        Response sa=s&&array?array(0,s):(Response){0},va=v&&array?array(0,v):(Response){0};
        if(sa.state||va.state||!none_value(dlsym(RTLD_DEFAULT,"$sSbN"),1,&flag)||!none_value(sa.value,8,&stories)||!none_value(va.value,8,&codecs)||!none_value(string_type,16,&country)||!viewer_state_enabled(&viewer)) { destroy(&name,string_type);return nil; }
        ProfileInit make=(void*)ssn_resolve("$s16TwitchGraphQLAPI29ProfileInfoFromChannelIDQueryC9channelID24includeIsParticipatingDJ17storyCapabilities0K18CollaborationCount15supportedCodecs0kG12SafetyStatus11countryCode0K11ViewerStateACSS_9ApolloAPI0B10QLNullableOySbGANySayAL0B6QLEnumOyAA22StoryFeatureCapabilityOGGGAoNySayAQyAA10VideoCodecOGGGAoNySSGAOtcfC");if(make)query=make(name.a,name.b,flag,stories,flag,codecs,flag,country.a,country.b,viewer,op->q);
    } else if(operation==1) {
        LabelsQueryInit make=(void*)ssn_resolve("$s16TwitchGraphQLAPI23UserFollowingStateQueryC6userIDACSS_tcfC");if(make)query=make(name.a,name.b,op->q);
    } else {
        uintptr_t input=0;
        if(operation==2) { SW uintptr_t (*make)(uintptr_t,uintptr_t)=(void*)ssn_resolve("$s16TwitchGraphQLAPI17UnfollowUserInputV8targetIDACSS_tcfC");if(make)input=make(name.a,name.b); }
        if(operation==3) { FollowInput make=(void*)ssn_resolve("$s16TwitchGraphQLAPI15FollowUserInputV20disableNotifications8targetIDACSb_SStcfC");if(make)input=make(0,name.a,name.b); }
        if(operation==4) {
            EnumInit make_enum=(void*)ssn_resolve("$s9ApolloAPI11GraphQLEnumO8rawValueACyxGSS_tcfC");NotifyInput make=(void*)ssn_resolve("$s16TwitchGraphQLAPI35SetLiveNotificationsEnrollmentInputV9channelID12settingStateACSS_9ApolloAPI0B6QLEnumOyAA033FollowsChannelNotificationSettingL0OGtcfC");
            if(!sized(notify_value,17)||!make_enum||!make||!kind(setting,"NSString")) { destroy(&name,string_type);return nil; }
            _Alignas(16) unsigned char storage[24]={0};Words2 choice=from_string(setting);
            make_enum(storage,choice.a,choice.b,notify_enum,notify_witness);
            Words2 words;memcpy(&words,storage,16);uint8_t tag=storage[16];
            input=make(name.a,name.b,words.a,words.b,tag); // consumes the enum/String values
        }
        SW uintptr_t (*make)(uintptr_t,const void* CTX)=(void*)ssn_resolve(op->factory);
        if(input&&make)query=make(input,op->q);
    }
    if(!query) { ssn_profile_event(operation,SSN_PROFILE_UNAVAILABLE);return nil; }
    Words2 client=client_getter(graph);uintptr_t result=0;
    if(operation<2) fetch(&result,query,1,client.a,client.b,op->q,op->witness);
    else {
        MutationMap maps[]={NULL,NULL,unwrap2,unwrap3,unwrap4};
        perform(&result,query,(id)dispatch_get_main_queue(),maps[operation],NULL,client.a,client.b,op->q,op->d,error_type,op->witness,error_witness);
    }
    ssn_profile_event(operation,SSN_PROFILE_SUBMITTED);
    release_object(query);release_object(client.a);release_object(client.b);
    id mapped=promise_objc(value_maps[operation],NULL,error_maps[operation],NULL,op->promise,objc_type,objc_type,&result);destroy(&result,op->promise);
    if(!kind(mapped,"TWLPromise")){objc_release(mapped);return nil;}return mapped;
}

/* TwitchKit's bounded small-image lookup. The mapping receives a borrowed
 * Optional<URL> and bridges it with the system Swift metadata for that type. */
static const void *avatar_url_type;

static id SW map_avatar(const void *value,void *context CTX) {
    (void)context;
    id url=bridge(value,avatar_url_type);
    id text=kind(url,"NSURL")?m0(url,"absoluteString"):nil;
    id result=m0(c("NSMutableDictionary"),"new");
    if(kind(text,"NSString")&&num(text,"length")<=2048)put(result,"avatarURL",text);
    objc_release(url);
    return result;
}

static id SW error_avatar(const void *value,void *context CTX) {
    (void)value;(void)context;
    return failed();
}

id ssn_profile_avatar_request(uint32_t user_id) {
    if(!user_id||!ssn_playback_authorized()||!initialize())return nil;
    AvatarRequest request=(void*)ssn_resolve("$s9TwitchKit9TKGraphQLC25fetchSmallProfileImageURL13forUserWithID12Tomorrowland7PromiseVy10Foundation0I0VSg0A6Apollo0A12GraphQLErrorVGs6UInt32V_tF");
    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance");
    if(!request||!graph)return nil;

    if(!avatar_url_type) {
        Meta url_meta=dlsym(RTLD_DEFAULT,"$s10Foundation3URLVMa");
        GenericMeta optional=dlsym(RTLD_DEFAULT,"$sSqMa");
        Response url=url_meta?url_meta(0):(Response){0};
        if(!optional||url.state||!url.value)return nil;
        Response type=optional(0,url.value);
        if(type.state||!type.value)return nil;
        avatar_url_type=type.value;
    }
    Response promise=promise_meta(0,avatar_url_type,error_type);
    if(promise.state||!sized(promise.value,8))return nil;

    uintptr_t result=0;
    request(&result,user_id,graph);
    id mapped=promise_objc(map_avatar,NULL,error_avatar,NULL,promise.value,objc_type,objc_type,&result);
    destroy(&result,promise.value);
    if(!kind(mapped,"TWLPromise")) { objc_release(mapped);return nil; }
    return mapped;
}

/* Reuse the authenticated Apollo client and its native mutation adapter.
 * SwiftUI receives a delivery result only. */
static const void *chat_mutation_result;

static void SW unwrap_chat(void * OUT out,const void *value,void *context CTX) {
    (void)context;
    unwrap(out,chat_mutation_result,value);
}

static id SW map_chat(const void *value,void *context CTX) {
    (void)context;
    PlaybackField root=(void*)ssn_resolve("$s16TwitchGraphQLAPI23SendChatMessageMutationC4DataV6__data9ApolloAPI0H4DictVvg");
    if(!root)return failed();
    uintptr_t raw=root(*(const uintptr_t*)value);
    uintptr_t dict=dict_getter(raw);
    destroy(&raw,data_type);
    id boxed=bridge(&dict,dict_type);
    destroy(&dict,dict_type);
    id result=ssn_chat_send_result(boxed);
    objc_release(boxed);
    return result?:failed();
}

id ssn_chat_send_request(id channel,id message) {
    if(!ssn_playback_authorized()||!initialize()||
       !kind(channel,"NSString")||!num(channel,"length")||num(channel,"length")>32||
       !kind(message,"NSString")||!num(message,"length")||num(message,"length")>500)return nil;

    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance");
    const void *query_type=meta("$s16TwitchGraphQLAPI23SendChatMessageMutationCMa"),*data=meta("$s16TwitchGraphQLAPI23SendChatMessageMutationC4DataVMa");
    const void *mutation_protocol=ssn_resolve("$s9ApolloAPI15GraphQLMutationMp");
    const void *root_protocol=ssn_resolve("$s9ApolloAPI16RootSelectionSetMp");
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    ChatInput input=(void*)ssn_resolve("$s16TwitchGraphQLAPI20SendChatMessageInputV9channelID7message5nonce011replyParentfI0ACSS_SS9ApolloAPI0B10QLNullableOySSGAKtcfC");
    SW uintptr_t (*make)(uintptr_t,const void* CTX)=(void*)ssn_resolve("$s16TwitchGraphQLAPI23SendChatMessageMutationC5inputAcA0deF5InputV_tcfC");
    if(!graph||!sized(query_type,8)||!sized(data,8)||!conforms||!mutation_protocol||!root_protocol||
       !input||!make||!ssn_resolve("$s16TwitchGraphQLAPI23SendChatMessageMutationC4DataV6__data9ApolloAPI0H4DictVvg"))return nil;
    const void *witness=conforms(query_type,mutation_protocol),*data_witness=conforms(data,root_protocol);
    Response promise=promise_meta(0,data,error_type);
    if(!witness||!data_witness||promise.state||!sized(promise.value,8))return nil;
    if(!chat_mutation_result) {
        const void *arguments[]={data,error_type,data_witness,error_witness};
        Response result=result_meta(0,arguments);
        if(result.state||!vw(result.value)||vw(result.value)[8]>65536)return nil;
        chat_mutation_result=result.value;
    }

    _Alignas(16) Words2 nonce={0},reply={0};
    if(!none_value(string_type,16,&nonce)||!none_value(string_type,16,&reply))return nil;
    Words2 channel_id=from_string(channel),body=from_string(message);
    uintptr_t query=make(input(channel_id.a,channel_id.b,body.a,body.b,nonce.a,nonce.b,reply.a,reply.b),query_type);
    Words2 client=client_getter(graph);
    uintptr_t result=0;
    perform(&result,query,(id)dispatch_get_main_queue(),unwrap_chat,NULL,client.a,client.b,query_type,data,error_type,witness,error_witness);
    release_object(query);release_object(client.a);release_object(client.b);
    id mapped=promise_objc(map_chat,NULL,error_avatar,NULL,promise.value,objc_type,objc_type,&result);
    destroy(&result,promise.value);
    if(!kind(mapped,"TWLPromise")) { objc_release(mapped);return nil; }
    return mapped;
}

/* Native read-only cheer catalogue. Generated Swift getters return a DataDict
 * word, a String pair, or a typed Array word; each carrier is validated against
 * metadata. No SDK identity, auth or unrelated campaign fields are exported. */
struct CheerTypes {
    const void *query,*data,*promise,*witness,*group,*groups;
};
static struct CheerTypes cheer_channel,cheer_global;
static const void *cheer_user,*cheer_user_optional,*cheer_value,*cheer_optional;
static const void *cheer_node,*cheer_nodes,*cheer_tier,*cheer_tiers;
static const void *cheer_config,*cheer_display,*cheer_color,*cheer_colors;
static bool cheer_initialized,cheer_available;
static const void *cheer_array(const void *element) {
    GenericMeta array=dlsym(RTLD_DEFAULT,"$sSaMa");
    if(!sized(element,8)||!array)return NULL;
    Response result=array(0,element);
    return !result.state&&sized(result.value,8)?result.value:NULL;
}
static const void *cheer_option(const void *element) {
    GenericMeta optional=dlsym(RTLD_DEFAULT,"$sSqMa");
    if(!sized(element,8)||!optional)return NULL;
    Response result=optional(0,element);
    return !result.state&&sized(result.value,8)?result.value:NULL;
}
static bool cheer_query_types(struct CheerTypes *types,const char *query,const char *data,const char *group) {
    types->query=meta(query);types->data=meta(data);types->group=meta(group);
    types->groups=cheer_array(types->group);
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    const void *protocol=ssn_resolve("$s9ApolloAPI12GraphQLQueryMp");
    if(!sized(types->query,8)||!sized(types->data,8)||!types->groups||!conforms||!protocol)return false;
    types->witness=conforms(types->query,protocol);
    Response promise=promise_meta(0,types->data,error_type);
    if(!types->witness||promise.state||!sized(promise.value,8))return false;
    types->promise=promise.value;return true;
}
static bool cheer_initialize(void) {
    if(cheer_initialized)return cheer_available;
    cheer_initialized=true;
    if(!cheer_query_types(&cheer_channel,"$s16TwitchGraphQLAPI14CheerInfoQueryCMa","$s16TwitchGraphQLAPI14CheerInfoQueryC4DataVMa","$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserV0D0V0D5GroupVMa")||
       !cheer_query_types(&cheer_global,"$s16TwitchGraphQLAPI22GlobalCheerConfigQueryCMa","$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataVMa","$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V5GroupVMa"))return false;
    cheer_user=meta("$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserVMa");cheer_user_optional=cheer_option(cheer_user);
    cheer_value=meta("$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserV0D0VMa");cheer_optional=cheer_option(cheer_value);
    cheer_node=meta("$s16TwitchGraphQLAPI22CheermoteGroupFragmentV4NodeVMa");cheer_nodes=cheer_array(cheer_node);
    cheer_tier=meta("$s16TwitchGraphQLAPI22CheermoteGroupFragmentV4NodeV4TierVMa");cheer_tiers=cheer_array(cheer_tier);
    cheer_config=meta("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0VMa");
    cheer_display=meta("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V07DisplayF0VMa");
    cheer_color=meta("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V07DisplayF0V5ColorVMa");cheer_colors=cheer_array(cheer_color);
    cheer_available=cheer_user_optional&&cheer_optional&&cheer_nodes&&cheer_tiers&&sized(cheer_config,8)&&sized(cheer_display,8)&&cheer_colors;
    return cheer_available;
}
static bool cheer_present(uintptr_t *value,const void *payload) {
    return ((GetTag)vw(payload)[6])(value,1,payload)==0;
}
static id cheer_string(PlaybackString getter,uintptr_t object,unsigned maximum) {
    if(!getter)return nil;
    Words2 value=getter(object);
    id string=bridge(&value,string_type);destroy(&value,string_type);
    if(!kind(string,"NSString")||!num(string,"length")||num(string,"length")>maximum) { objc_release(string);return nil; }
    return string;
}
static id cheer_list(PlaybackField getter,uintptr_t object,const void *type,unsigned maximum) {
    if(!getter)return nil;
    uintptr_t array=getter(object);
    id boxed=bridge(&array,type);destroy(&array,type);
    if(!kind(boxed,"NSArray")||num(boxed,"count")>maximum){objc_release(boxed);return nil;}
    return boxed;
}
static id cheer_number(uintptr_t value) {
    if(!value||value>100000000)return nil;
    return ((id(*)(id,SEL,unsigned long long))objc_msgSend)(c("NSNumber"),ss("numberWithUnsignedLongLong:"),(unsigned long long)value);
}
static id cheer_groups(uintptr_t owner,bool global) {
    const struct CheerTypes *type=global?&cheer_global:&cheer_channel;
    PlaybackField group_get=(void*)ssn_resolve(global?
        "$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V6groupsSayAG5GroupVGvg":
        "$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserV0D0V11cheerGroupsSayAI0D5GroupVGvg");
    PlaybackField node_get=(void*)ssn_resolve(global?
        "$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V5GroupV5nodesSayAA09CheermoteI8FragmentV4NodeVGvg":
        "$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserV0D0V0D5GroupV5nodesSayAA09CheermoteI8FragmentV4NodeVGvg");
    PlaybackString template_get=(void*)ssn_resolve(global?
        "$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V5GroupV11templateURLSSvg":
        "$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserV0D0V0D5GroupV11templateURLSSvg");
    PlaybackString prefix_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22CheermoteGroupFragmentV4NodeV6prefixSSvg");
    PlaybackField tier_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22CheermoteGroupFragmentV4NodeV5tiersSayAE4TierVGvg");
    PlaybackField bits_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22CheermoteGroupFragmentV4NodeV4TierV4bitsSivg");
    if(!group_get||!node_get||!template_get||!prefix_get||!tier_get||!bits_get)return nil;
    id groups=cheer_list(group_get,owner,type->groups,128);
    if(!groups)return nil;
    id result=m0(c("NSMutableArray"),"new");
    for(uintptr_t i=0;i<num(groups,"count")&&num(result,"count")<256;i++) {
        id box=at(groups,i);uintptr_t group=0;
        if(!cast(&group,&box,objc_type,type->group,0))continue;
        id template=cheer_string(template_get,group,2048),nodes=cheer_list(node_get,group,cheer_nodes,256);
        destroy(&group,type->group);
        for(uintptr_t j=0;template&&nodes&&j<num(nodes,"count")&&num(result,"count")<256;j++) {
            id node_box=at(nodes,j);uintptr_t node=0;
            if(!cast(&node,&node_box,objc_type,cheer_node,0))continue;
            id prefix=cheer_string(prefix_get,node,64),tiers=cheer_list(tier_get,node,cheer_tiers,32);
            destroy(&node,cheer_node);
            id values=m0(c("NSMutableArray"),"new");
            for(uintptr_t k=0;tiers&&k<num(tiers,"count");k++) {
                id tier_box=at(tiers,k);uintptr_t tier=0;
                if(!cast(&tier,&tier_box,objc_type,cheer_tier,0))continue;
                id value=cheer_number(bits_get(tier));destroy(&tier,cheer_tier);
                if(value)v1(values,"addObject:",value);
            }
            if(prefix&&num(values,"count")) {
                id row=m0(c("NSMutableDictionary"),"new");put(row,"prefix",prefix);put(row,"template",template);put(row,"tiers",values);
                v1(result,"addObject:",row);objc_release(row);
            }
            objc_release(values);objc_release(tiers);objc_release(prefix);
        }
        objc_release(template);objc_release(nodes);
    }
    objc_release(groups);return result;
}
static id SW map_channel_cheers(const void *value,void *context CTX) {
    (void)context;
    PlaybackField get_user=(void*)ssn_resolve("$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4userAE4UserVSgvg");
    PlaybackField get_cheer=(void*)ssn_resolve("$s16TwitchGraphQLAPI14CheerInfoQueryC4DataV4UserV5cheerAG0D0VSgvg");
    if(!get_user||!get_cheer)return failed();
    uintptr_t user=get_user(*(const uintptr_t*)value);
    if(!cheer_present(&user,cheer_user)){destroy(&user,cheer_user_optional);return failed();}
    uintptr_t cheer=get_cheer(user);destroy(&user,cheer_user_optional);
    if(!cheer_present(&cheer,cheer_value)){destroy(&cheer,cheer_optional);return failed();}
    id groups=cheer_groups(cheer,false);destroy(&cheer,cheer_optional);
    if(!groups)return failed();
    id result=m0(c("NSMutableDictionary"),"new");put(result,"groups",groups);objc_release(groups);return result;
}
static id SW map_global_cheers(const void *value,void *context CTX) {
    (void)context;
    PlaybackField config_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV05cheerF0AE0eF0Vvg"),
        display_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V07displayF0AG07DisplayF0Vvg"),
        colors_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V07DisplayF0V6colorsSayAI5ColorVGvg"),
        bits_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V07DisplayF0V5ColorV4bitsSivg");
    PlaybackString color_get=(void*)ssn_resolve("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryC4DataV0eF0V07DisplayF0V5ColorV5colorSSvg");
    if(!config_get||!display_get||!colors_get||!bits_get||!color_get)return failed();
    uintptr_t config=config_get(*(const uintptr_t*)value);
    id groups=cheer_groups(config,true);
    uintptr_t display=display_get(config);destroy(&config,cheer_config);
    id colors=cheer_list(colors_get,display,cheer_colors,64);destroy(&display,cheer_display);
    id result=m0(c("NSMutableDictionary"),"new"),palette=m0(c("NSMutableArray"),"new");
    for(uintptr_t i=0;colors&&i<num(colors,"count");i++) {
        id box=at(colors,i);uintptr_t item=0;
        if(!cast(&item,&box,objc_type,cheer_color,0))continue;
        id bits=cheer_number(bits_get(item)),color=cheer_string(color_get,item,16);destroy(&item,cheer_color);
        if(bits&&color){id row=m0(c("NSMutableDictionary"),"new");put(row,"bits",bits);put(row,"color",color);v1(palette,"addObject:",row);objc_release(row);}
        objc_release(color);
    }
    if(groups)put(result,"groups",groups);
    put(result,"colors",palette);objc_release(groups);objc_release(colors);objc_release(palette);return result;
}
id ssn_chat_cheer_request(id channel,bool global) {
    if(!ssn_playback_authorized()||!initialize()||!cheer_initialize())return nil;
    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance");if(!graph)return nil;
    struct CheerTypes *types=global?&cheer_global:&cheer_channel;
    uintptr_t query=0;
    if(global) {
        SW uintptr_t (*make)(const void * CTX)=(void*)ssn_resolve("$s16TwitchGraphQLAPI22GlobalCheerConfigQueryCACycfC");
        if(make)query=make(types->query);
    } else {
        LabelsQueryInit make=(void*)ssn_resolve("$s16TwitchGraphQLAPI14CheerInfoQueryC9channelIDACSS_tcfC");
        if(!make||!kind(channel,"NSString")||!num(channel,"length")||num(channel,"length")>32)return nil;
        Words2 name=from_string(channel);query=make(name.a,name.b,types->query);
    }
    if(!query)return nil;
    Words2 client=client_getter(graph);uintptr_t result=0;
    fetch(&result,query,1,client.a,client.b,types->query,types->witness);
    release_object(query);release_object(client.a);release_object(client.b);
    id mapped=promise_objc(global?map_global_cheers:map_channel_cheers,NULL,error_avatar,NULL,types->promise,objc_type,objc_type,&result);
    destroy(&result,types->promise);
    if(!kind(mapped,"TWLPromise")){objc_release(mapped);return nil;}return mapped;
}
