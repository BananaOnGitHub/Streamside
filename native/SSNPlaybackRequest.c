/* Donor-specific synchronous Swift ABI lives here, not in the frontend.
 * All storage is metadata/value-witness managed. No account OAuth credential is
 * read: TKGraphQL's existing HTTP authorization and integrity chain owns it. */
#include "SSNPlaybackRequest.h"
#include "SSNIntegration.h"
#include <dlfcn.h>
#include <stdlib.h>

static bool initialized,available;
static const void *data_type,*token_type,*optional_token,*string_type,*promise_type,*objc_type,*query_type,*query_witness;
static ApolloClientGetter client_getter;
static PlaybackParamsInit params_init;
static PlaybackQueryInit query_init;
static PlaybackFetch fetch;
static PlaybackField token_getter;
static PlaybackString value_getter,signature_getter;
static PromiseObjC promise_objc;
static Bridge bridge;
static SW Words2 (*from_string)(id);
static void (*release_object)(uintptr_t);
static const uintptr_t *vw(const void *t) { return t?((const uintptr_t*const*)t)[-1]:NULL; }
static bool sized(const void *t,size_t size) { const uintptr_t *w=vw(t); return w&&w[8]==size&&w[9]>=size&&(w[10]&255)<=15; }
static const void *meta(const char *name) {
    Meta fn=(Meta)ssn_resolve(name); if(!fn) return NULL;
    Response r=fn(0); return r.state?NULL:r.value;
}
static void destroy(void *p,const void *t) { ((Destroy)vw(t)[1])(p,t); }
static id SW map_error(const void *value,void *context CTX) {
    (void)value;(void)context;
    /* Native errors can include complete credential-bearing request URLs. */
    return m0(c("NSNull"),"new");
}
static id SW map_data(const void *value,void *context CTX) {
    (void)context;
    /* Generated Data and its optional token lower directly to X0. Their value
     * witnesses and the inspected getter call sites both establish one word. */
    uintptr_t token=token_getter(*(const uintptr_t*)value);
    if(((GetTag)vw(token_type)[6])(&token,1,token_type)!=0) {
        destroy(&token,optional_token); return m0(c("NSNull"),"new");
    }
    Words2 raw=value_getter(token),sig=signature_getter(token);
    id text=bridge(&raw,string_type),signature=bridge(&sig,string_type);
    destroy(&raw,string_type);destroy(&sig,string_type);destroy(&token,optional_token);
    id result=m0(c("NSNull"),"new");
    if(kind(text,"NSString")&&num(text,"length")>0&&num(text,"length")<=65536&&
       kind(signature,"NSString")&&num(signature,"length")>0&&num(signature,"length")<=1024) {
        objc_release(result);result=m0(c("NSMutableDictionary"),"new");
        put(result,"value",text);put(result,"signature",signature);
    }
    objc_release(text);objc_release(signature);return result;
}
static bool initialize(void) {
    if(initialized) return available;initialized=true;
    data_type=meta("$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataVMa");
    token_type=meta("$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataV0d8PlaybackeF0VMa");
    query_type=meta("$s16TwitchGraphQLAPI22StreamAccessTokenQueryCMa");
    const void *params=meta("$s16TwitchGraphQLAPI25PlaybackAccessTokenParamsVMa");
    string_type=dlsym(RTLD_DEFAULT,"$sSSN");
    const void *error=dlsym(RTLD_DEFAULT,"$s12TwitchApollo0A12GraphQLErrorVN");
    GenericMeta optional=dlsym(RTLD_DEFAULT,"$sSqMa");
    PairMeta promise=(PairMeta)ssn_resolve("$s12Tomorrowland7PromiseVMa");
    const void *(*conforms)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    const void *protocol=dlsym(RTLD_DEFAULT,"$s9ApolloAPI12GraphQLQueryMp");
    const void *(*objc_meta)(Class)=dlsym(RTLD_DEFAULT,"swift_getObjCClassMetadata");
    bridge=dlsym(RTLD_DEFAULT,"$ss27_bridgeAnythingToObjectiveCyyXlxlF");
    from_string=dlsym(RTLD_DEFAULT,"$sSS10FoundationE36_unconditionallyBridgeFromObjectiveCySSSo8NSStringCSgFZ");
    release_object=dlsym(RTLD_DEFAULT,"swift_release");
    client_getter=(ApolloClientGetter)ssn_resolve("$s9TwitchKit9TKGraphQLC12apolloClientAA08TWApolloF0Vvg");
    params_init=(PlaybackParamsInit)ssn_resolve("$s16TwitchGraphQLAPI25PlaybackAccessTokenParamsV6device12disableHTTPS10hasAdblock4maid14notificationID8platform13playerBackend0Q4Type20preferredVideoHeightAC9ApolloAPI0B10QLNullableOyAA0D18DeviceCapabilitiesVG_AOySbGAsOySSGATSSATSSAOySiGtcfC");
    query_init=(PlaybackQueryInit)ssn_resolve("$s16TwitchGraphQLAPI22StreamAccessTokenQueryC11channelName6paramsACSS_AA08PlaybackeF6ParamsVtcfC");
    fetch=(PlaybackFetch)ssn_resolve("$s9TwitchKit14TWApolloClientV14fetchAsPromise5query11cachePolicy12Tomorrowland0G0Vy4DataQz0A6Apollo0A12GraphQLErrorVGx_0M005CacheJ0Ot0M3API0N7QLQueryRzlF");
    token_getter=(PlaybackField)ssn_resolve("$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataV014streamPlaybackeF0AE0djeF0VSgvg");
    value_getter=(PlaybackString)ssn_resolve("$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataV0d8PlaybackeF0V5valueSSvg");
    signature_getter=(PlaybackString)ssn_resolve("$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataV0d8PlaybackeF0V9signatureSSvg");
    promise_objc=(PromiseObjC)ssn_resolve("$s12Tomorrowland7PromiseV4objc8mapValue0D5ErrorSo10TWLPromiseCyqd__qd_0_Gqd__xc_qd_0_q_ctRld__CRld_0_Cr0_lF");
    if(!sized(data_type,8)||!sized(token_type,8)||!sized(query_type,8)||!sized(params,8)||!sized(string_type,16)||
       !error||!optional||!promise||!conforms||!protocol||!objc_meta||!bridge||!from_string||!release_object||
       !client_getter||!params_init||!query_init||!fetch||!token_getter||!value_getter||!signature_getter||!promise_objc) return false;
    Response op=optional(0,token_type),pr=promise(0,data_type,error);
    if(op.state||pr.state||!sized(op.value,8)||!sized(pr.value,8)) return false;
    optional_token=op.value;promise_type=pr.value;
    query_witness=conforms(query_type,protocol);objc_type=objc_meta(objc_getClass("NSObject"));
    available=query_witness&&objc_type;return available;
}
id ssn_playback_request(id channel) {
    if(!ssn_playback_authorized()||!initialize()||!kind(channel,"NSString")||!num(channel,"length")||num(channel,"length")>128) return nil;
    id graph=m0(c("_TtC9TwitchKit9TKGraphQL"),"sharedInstance"); if(!graph) return nil;
    Words2 platform=from_string(ns("ios")),player=from_string(ns("site")),name=from_string(channel);
    /* Same native null representations/lowering as live requester 1025e0810–48.
     * This frontend explicitly uses interactive/site playback, not feed autoplay.
     * Constructors consume the supplied native Swift strings and InputDict. */
    uintptr_t params=params_init(0,2,2,0,0,0,0,platform.a,platform.b,0,0,player.a,player.b,0,1);
    uintptr_t query=query_init(name.a,name.b,params,query_type);
    Words2 client=client_getter(graph);uintptr_t result=0;
    /* Native requester uses CachePolicy tag 1: ignore local cache. */
    fetch(&result,query,1,client.a,client.b,query_type,query_witness);
    release_object(query);release_object(client.a);release_object(client.b);
    id mapped=promise_objc(map_data,NULL,map_error,NULL,promise_type,objc_type,objc_type,&result);
    destroy(&result,promise_type);
    if(!kind(mapped,"TWLPromise")) { objc_release(mapped);return nil; }
    return mapped;
}
