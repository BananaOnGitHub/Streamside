/* Exact Twitch 32 CCL query. Ordinary freeform stream tags are not warnings.
 * All generated selection values use inspected direct-word lowering; optional
 * tags, destruction and array conversion use runtime metadata/witnesses. */
#include "SSNContentLabelsRequest.h"
#include "SSNPlaybackRequest.h"
#include "SSNIntegration.h"
#include <dlfcn.h>

static bool initialized,available;
static const void *query_type,*data_type,*user_type,*stream_type,*label_type;
static const void *optional_user,*optional_stream,*optional_array,*string_type,*promise_type,*objc_type,*query_witness;
static ApolloClientGetter client_getter;
static LabelsQueryInit query_init;
static PlaybackFetch fetch;
static PlaybackField user_getter,stream_getter,labels_getter;
static PlaybackString name_getter;
static SW uint8_t (*enabled_getter)(uintptr_t);
static PromiseObjC promise_objc;
static Bridge bridge;
static SW Words2 (*from_string)(id);
static bool (*cast)(void*,void*,const void*,const void*,uintptr_t);
static void (*release_object)(uintptr_t);
static const uintptr_t *vw(const void *t) { return t?((const uintptr_t*const*)t)[-1]:NULL; }
static bool sized(const void *t,size_t n) { const uintptr_t *w=vw(t);return w&&w[8]==n&&w[9]>=n&&(w[10]&255)<=15; }
static void destroy(void *v,const void *t) { ((Destroy)vw(t)[1])(v,t); }
static const void *meta(const char *name) {
    Meta fn=(Meta)ssn_resolve(name);if(!fn) return NULL;
    Response r=fn(0);return r.state?NULL:r.value;
}
static id failed(void) { return m0(c("NSNull"),"new"); }
static id SW map_error(const void *value,void *context CTX) { (void)value;(void)context;return failed(); }
static id SW map_data(const void *value,void *context CTX) {
    (void)context;
    uintptr_t user=user_getter(*(const uintptr_t*)value);
    if(((GetTag)vw(user_type)[6])(&user,1,user_type)!=0) { destroy(&user,optional_user);return failed(); }
    uintptr_t stream=stream_getter(user);destroy(&user,optional_user);
    if(((GetTag)vw(stream_type)[6])(&stream,1,stream_type)!=0) { destroy(&stream,optional_stream);return failed(); }
    uintptr_t raw=labels_getter(stream);destroy(&stream,optional_stream);
    id source=bridge(&raw,optional_array);destroy(&raw,optional_array);
    if(!kind(source,"NSArray")||num(source,"count")>64) { objc_release(source);return failed(); }
    id result=m0(c("NSMutableArray"),"new");bool valid=true;
    for(uintptr_t i=0;i<num(source,"count");i++) {
        id boxed=at(source,i);uintptr_t label=0;
        if(!cast(&label,&boxed,objc_type,label_type,0)) { valid=false;break; }
        uint8_t enabled=enabled_getter(label);
        if(enabled>1) { destroy(&label,label_type);valid=false;break; }
        if(enabled) {
            Words2 raw_name=name_getter(label);id name=bridge(&raw_name,string_type);destroy(&raw_name,string_type);
            if(!kind(name,"NSString")||!num(name,"length")||num(name,"length")>512) valid=false;
            else v1(result,"addObject:",name);
            objc_release(name);
        }
        destroy(&label,label_type);if(!valid) break;
    }
    objc_release(source);
    if(!valid) { objc_release(result);return failed(); }
    return result;
}
static bool initialize(void) {
    if(initialized) return available;initialized=true;
    query_type=meta("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryCMa");
    data_type=meta("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataVMa");
    user_type=meta("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserVMa");
    stream_type=meta("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserV0G0VMa");
    label_type=meta("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserV0G0V0deF0VMa");
    query_init=(LabelsQueryInit)ssn_resolve("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC9channelIdACSS_tcfC");
    user_getter=(PlaybackField)ssn_resolve("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4userAE4UserVSgvg");
    stream_getter=(PlaybackField)ssn_resolve("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserV6streamAG0G0VSgvg");
    labels_getter=(PlaybackField)ssn_resolve("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserV0G0V07contentE6LabelsSayAI0deF0VGSgvg");
    name_getter=(PlaybackString)ssn_resolve("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserV0G0V0deF0V13localizedNameSSvg");
    enabled_getter=(void*)ssn_resolve("$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC4DataV4UserV0G0V0deF0V9isEnabledSbvg");
    client_getter=(ApolloClientGetter)ssn_resolve("$s9TwitchKit9TKGraphQLC12apolloClientAA08TWApolloF0Vvg");
    fetch=(PlaybackFetch)ssn_resolve("$s9TwitchKit14TWApolloClientV14fetchAsPromise5query11cachePolicy12Tomorrowland0G0Vy4DataQz0A6Apollo0A12GraphQLErrorVGx_0M005CacheJ0Ot0M3API0N7QLQueryRzlF");
    promise_objc=(PromiseObjC)ssn_resolve("$s12Tomorrowland7PromiseV4objc8mapValue0D5ErrorSo10TWLPromiseCyqd__qd_0_Gqd__xc_qd_0_q_ctRld__CRld_0_Cr0_lF");
    string_type=dlsym(RTLD_DEFAULT,"$sSSN");
    const void *error=dlsym(RTLD_DEFAULT,"$s12TwitchApollo0A12GraphQLErrorVN");
    GenericMeta optional=dlsym(RTLD_DEFAULT,"$sSqMa"),array=dlsym(RTLD_DEFAULT,"$sSaMa");
    PairMeta promise=(PairMeta)ssn_resolve("$s12Tomorrowland7PromiseVMa");
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    const void *protocol=dlsym(RTLD_DEFAULT,"$s9ApolloAPI12GraphQLQueryMp");
    const void *(*objc_meta)(Class)=dlsym(RTLD_DEFAULT,"swift_getObjCClassMetadata");
    bridge=dlsym(RTLD_DEFAULT,"$ss27_bridgeAnythingToObjectiveCyyXlxlF");
    from_string=dlsym(RTLD_DEFAULT,"$sSS10FoundationE36_unconditionallyBridgeFromObjectiveCySSSo8NSStringCSgFZ");
    cast=dlsym(RTLD_DEFAULT,"swift_dynamicCast");release_object=dlsym(RTLD_DEFAULT,"swift_release");
    if(!sized(query_type,8)||!sized(data_type,8)||!sized(user_type,8)||!sized(stream_type,8)||!sized(label_type,8)||!sized(string_type,16)||
       !query_init||!user_getter||!stream_getter||!labels_getter||!name_getter||!enabled_getter||!client_getter||!fetch||!promise_objc||
       !error||!optional||!array||!promise||!conforms||!protocol||!objc_meta||!bridge||!from_string||!cast||!release_object) return false;
    Response a=array(0,label_type),u=optional(0,user_type),s=optional(0,stream_type),p=promise(0,data_type,error);
    if(a.state||u.state||s.state||p.state||!sized(a.value,8)||!sized(u.value,8)||!sized(s.value,8)||!sized(p.value,8)) return false;
    Response oa=optional(0,a.value);if(oa.state||!sized(oa.value,8)) return false;
    optional_user=u.value;optional_stream=s.value;optional_array=oa.value;promise_type=p.value;
    query_witness=conforms(query_type,protocol);objc_type=objc_meta(objc_getClass("NSObject"));
    available=query_witness&&objc_type;return available;
}
id ssn_content_labels_request(id channel) {
    if(!ssn_playback_authorized()||!initialize()||!kind(channel,"NSString")||!num(channel,"length")||num(channel,"length")>128) return nil;
    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance");if(!graph) return nil;
    Words2 name=from_string(channel);uintptr_t query=query_init(name.a,name.b,query_type);
    Words2 client=client_getter(graph);uintptr_t result=0;
    fetch(&result,query,1,client.a,client.b,query_type,query_witness);
    release_object(query);release_object(client.a);release_object(client.b);
    id mapped=promise_objc(map_data,NULL,map_error,NULL,promise_type,objc_type,objc_type,&result);destroy(&result,promise_type);
    if(!kind(mapped,"TWLPromise")) { objc_release(mapped);return nil; }
    return mapped;
}
