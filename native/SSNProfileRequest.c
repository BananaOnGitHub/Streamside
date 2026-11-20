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
static Bridge bridge;static PlaybackField dict_getter;static ApolloClientGetter client_getter;
static SW Words2 (*from_string)(id);static bool (*cast)(void*,void*,const void*,const void*,uintptr_t);
static void (*release_object)(uintptr_t);static PromiseObjC promise_objc;static PairMeta promise_meta;
static PlaybackFetch fetch;static Perform perform;static PackedMeta result_meta;static Unwrap unwrap;
static bool initialized,available;
static const uintptr_t *vw(const void *t) { return t?((const uintptr_t*const*)t)[-1]:NULL; }
static bool sized(const void *t,size_t n) { const uintptr_t *w=vw(t);return w&&w[8]==n&&w[9]>=n&&(w[10]&255)<=15; }
static void destroy(void *v,const void *t) { ((Destroy)vw(t)[1])(v,t); }
static const void *meta(const char *name) { Meta fn=(Meta)ssn_resolve(name);if(!fn)return NULL;Response x=fn(0);return x.state?NULL:x.value; }
static id failed(void) { return m0(c("NSNull"),"new"); }
static id SW map_error(const void *value,void *context CTX) { (void)value;(void)context;return failed(); }
id ssn_profile_unbox(id object) {
    uintptr_t raw=0;
    if(!available||!cast(&raw,&object,objc_type,data_type,0)) return nil;
    uintptr_t dict=dict_getter(raw);destroy(&raw,data_type);
    id result=bridge(&dict,dict_type);destroy(&dict,dict_type);return result;
}
static id SW map_data(const void *value,void *context CTX) {
    PlaybackField root_getter=(void*)ssn_resolve(((const struct Operation*)context)->root);
    uintptr_t raw=root_getter(*(const uintptr_t*)value);
    uintptr_t dict=dict_getter(raw);destroy(&raw,data_type);
    id boxed=bridge(&dict,dict_type);destroy(&dict,dict_type);
    id result=ssn_profile_normalize(boxed);objc_release(boxed);return result?:failed();
}
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
    error_type=ssn_resolve("$s12TwitchApollo0A12GraphQLErrorVN");
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
static const void *enum_value_type(const char *name,const void **payload,const void **witness) {
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    PairMeta generic=(void*)ssn_resolve("$s9ApolloAPI11GraphQLEnumOMa");
    *payload=meta(name);const void *protocol=ssn_resolve("$s9ApolloAPI8EnumTypeMp");
    if(!*payload||!protocol||!conforms||!generic)return NULL;*witness=conforms(*payload,protocol);if(!*witness)return NULL;
    Response value=generic(0,*payload,*witness);return value.state?NULL:value.value;
}
id ssn_profile_request(id channel,unsigned operation,id setting) {
    if(operation>4||!ssn_playback_authorized()||!initialize()||!kind(channel,"NSString")||!num(channel,"length")||num(channel,"length")>128)return nil;
    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance");if(!graph)return nil;
    struct Operation *op=&ops[operation];Words2 name=from_string(channel);uintptr_t query=0;
    if(operation==0) {
        uint8_t flag=0;uintptr_t stories=0,codecs=0;const void *p=NULL,*w=NULL;
        GenericMeta array=dlsym(RTLD_DEFAULT,"$sSaMa");
        const void *s=enum_value_type("$s16TwitchGraphQLAPI22StoryFeatureCapabilityOMa",&p,&w),*v=enum_value_type("$s16TwitchGraphQLAPI10VideoCodecOMa",&p,&w);
        Response sa=s&&array?array(0,s):(Response){0},va=v&&array?array(0,v):(Response){0};
        if(sa.state||va.state||!none_value(dlsym(RTLD_DEFAULT,"$sSbN"),1,&flag)||!none_value(sa.value,8,&stories)||!none_value(va.value,8,&codecs)) { destroy(&name,string_type);return nil; }
        ProfileInit make=(void*)ssn_resolve("$s16TwitchGraphQLAPI29ProfileInfoFromChannelIDQueryC9channelID24includeIsParticipatingDJ17storyCapabilities0K18CollaborationCount15supportedCodecs0kG12SafetyStatusACSS_9ApolloAPI0B10QLNullableOySbGALySayAJ0B6QLEnumOyAA22StoryFeatureCapabilityOGGGAmLySayAOyAA10VideoCodecOGGGAMtcfC");if(make)query=make(name.a,name.b,flag,stories,flag,codecs,flag,op->q);
    } else if(operation==1) {
        LabelsQueryInit make=(void*)ssn_resolve("$s16TwitchGraphQLAPI23UserFollowingStateQueryC6userIDACSS_tcfC");if(make)query=make(name.a,name.b,op->q);
    } else {
        uintptr_t input=0;
        if(operation==2) { SW uintptr_t (*make)(uintptr_t,uintptr_t)=(void*)ssn_resolve("$s16TwitchGraphQLAPI17UnfollowUserInputV8targetIDACSS_tcfC");if(make)input=make(name.a,name.b); }
        if(operation==3) { FollowInput make=(void*)ssn_resolve("$s16TwitchGraphQLAPI15FollowUserInputV20disableNotifications8targetIDACSb_SStcfC");if(make)input=make(0,name.a,name.b); }
        if(operation==4) {
            EnumInit make_enum=(void*)ssn_resolve("$s9ApolloAPI11GraphQLEnumO8rawValueACyxGSS_tcfC");NotifyInput make=(void*)ssn_resolve("$s16TwitchGraphQLAPI35SetLiveNotificationsEnrollmentInputV9channelID12settingStateACSS_9ApolloAPI0B6QLEnumOyAA033FollowsChannelNotificationSettingL0OGtcfC");
            notify_value=enum_value_type("$s16TwitchGraphQLAPI38FollowsChannelNotificationSettingStateOMa",&notify_enum,&notify_witness);
            if(!sized(notify_value,17)||!make_enum||!make||!kind(setting,"NSString")) { destroy(&name,string_type);return nil; }
            _Alignas(16) unsigned char storage[24]={0};Words2 choice=from_string(setting);
            make_enum(storage,choice.a,choice.b,notify_enum,notify_witness);
            Words2 words;memcpy(&words,storage,16);uint8_t tag=storage[16];
            input=make(name.a,name.b,words.a,words.b,tag); // consumes the enum/String values
        }
        SW uintptr_t (*make)(uintptr_t,const void* CTX)=(void*)ssn_resolve(op->factory);
        if(input&&make)query=make(input,op->q);
    }
    if(!query)return nil;
    Words2 client=client_getter(graph);uintptr_t result=0;
    if(operation<2) fetch(&result,query,1,client.a,client.b,op->q,op->witness);
    else {
        MutationMap maps[]={NULL,NULL,unwrap2,unwrap3,unwrap4};
        perform(&result,query,(id)dispatch_get_main_queue(),maps[operation],NULL,client.a,client.b,op->q,op->d,error_type,op->witness,error_witness);
    }
    release_object(query);release_object(client.a);release_object(client.b);
    id mapped=promise_objc(map_data,op,map_error,NULL,op->promise,objc_type,objc_type,&result);destroy(&result,op->promise);
    if(!kind(mapped,"TWLPromise")){objc_release(mapped);return nil;}return mapped;
}
