/* Exact Twitch 32 bridge. Swift model storage stays opaque. Metadata and value
 * witnesses come from the runtime; no protocol witness slots or ivar layouts
 * are synthesized. See the Phase 2 ABI record and compiler register checks. */
#include "SSNIntegration.h"
#include "SSNCore.h"
#include "SSNSessionPolicy.h"
#include <dlfcn.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <dispatch/dispatch.h>
#include "SSNSwiftABI.h"
#if SSN_SWIFTUI
#include "SSNFeed.h"
#endif
static const void *user_type,*current_type,*identity_type,*string_type,*array_type,*page_type;
static const void *account_promise_type,*follows_promise_type,*tuple_type,*set_type,*objc_type;
static Bridge bridge;
static bool (*dynamic_cast)(void*,void*,const void*,const void*,uintptr_t);
static Getter current_user,user_identity;
static StringGetter identity_name,identity_display;
static PromiseObjC promise_objc;
static CurrentRequest current_request;
static FollowRequest follow_request;
static id account,channels,graph,active_promise,request_auth,verified_auth;
static uint64_t generation;
static unsigned waiting_ticks;
static bool initialized,available,checking_follows;
static _Atomic bool mapping_fault;
static Words3 nil_cursor;
static uintptr_t empty_set;
static const uintptr_t *vw(const void *type) { return type?((const uintptr_t*const*)type)[-1]:NULL; }
static size_t value_size(const void *type) {
    const uintptr_t *w=vw(type);
    if(!w || !w[8] || w[8]>65536 || w[9]<w[8] || (w[10]&255)>15 || (w[10]&(0x00100000|0x00400000|0x00800000))) return 0;
    return w[8];
}
static void *allocate(const void *type) { size_t size=value_size(type); return size?calloc(1,size):NULL; }
static void destroy(void *value,const void *type) {
    if(value) { ((Destroy)vw(type)[1])(value,type); free(value); }
}
static const void *metadata(const char *symbol) {
    Meta fn=(Meta)ssn_resolve(symbol); if(!fn) return NULL;
    Response r=fn(0); return !r.state&&value_size(r.value)?r.value:NULL;
}
static id failed_value(void) { return m0(c("NSNull"),"new"); }
static id mapping_failure(void) { atomic_store(&mapping_fault,true); ssn_failure(3); return failed_value(); }
id ssn_user_dictionary(const void *value) {
    void *identity=allocate(identity_type); if(!identity) return mapping_failure();
    user_identity(identity,value);
    Words2 raw=identity_name(identity),display=identity_display(identity);
    id name=bridge(&raw,string_type),label=bridge(&display,string_type);
    ((Destroy)vw(string_type)[1])(&raw,string_type);
    ((Destroy)vw(string_type)[1])(&display,string_type);
    destroy(identity,identity_type);
    id result=failed_value();
    if(kind(name,"NSString")&&num(name,"length")>0&&num(name,"length")<=128 &&
       kind(label,"NSString")&&num(label,"length")<=256) {
        objc_release(result); result=m0(c("NSMutableDictionary"),"new");
        put(result,"username",name); put(result,"displayName",label);
        put(result,"status",ns("Live status unavailable from this query"));
    }
    if(!kind(result,"NSDictionary")) { atomic_store(&mapping_fault,true); ssn_failure(3); }
    objc_release(name); objc_release(label); return result;
}
static id SW map_account(const void *value,void *context CTX) {
    (void)context; void *user=allocate(user_type); if(!user) return mapping_failure();
    current_user(user,value); id result=ssn_user_dictionary(user); destroy(user,user_type); return result;
}
static id SW map_follows(const void *value,void *context CTX) {
    (void)context;
    /* Tuple element offsets are supplied by the runtime's public ABI metadata. */
    const uintptr_t *tuple=tuple_type;
    id source=bridge((const char*)value+tuple[4],array_type);
    if(!kind(source,"NSArray")||num(source,"count")>50) { objc_release(source); return mapping_failure(); }
    id result=m0(c("NSMutableArray"),"new");
    for(uintptr_t i=0;i<num(source,"count");i++) {
        id boxed=at(source,i); void *user=allocate(user_type);
        if(!user || !dynamic_cast(user,&boxed,objc_type,user_type,0)) {
            free(user); objc_release(source); objc_release(result); return mapping_failure();
        }
        id item=ssn_user_dictionary(user); destroy(user,user_type);
        if(!kind(item,"NSDictionary")) { objc_release(item); objc_release(source); objc_release(result); return mapping_failure(); }
        v1(result,"addObject:",item); objc_release(item);
    }
    objc_release(source); return result;
}
static id SW map_error(const void *value,void *context CTX) {
    (void)value; (void)context;
    /* Never stringify a donor error: it can contain request/credential context. */
    return m0(c("NSNull"),"new");
}
static bool initialize(void) {
    if(initialized) return available&&!atomic_load(&mapping_fault);
    initialized=true;
    bridge=(Bridge)dlsym(RTLD_DEFAULT,"$ss27_bridgeAnythingToObjectiveCyyXlxlF");
    dynamic_cast=(void*)dlsym(RTLD_DEFAULT,"swift_dynamicCast");
    const void *(*objc_meta)(Class)=dlsym(RTLD_DEFAULT,"swift_getObjCClassMetadata");
    GenericMeta array=(void*)dlsym(RTLD_DEFAULT,"$sSaMa"),optional=(void*)dlsym(RTLD_DEFAULT,"$sSqMa");
    PairMeta set=(void*)dlsym(RTLD_DEFAULT,"$sShMa");
    const void *(*conformance)(const void*,const void*)=dlsym(RTLD_DEFAULT,"swift_conformsToProtocol");
    PairMeta promise=(PairMeta)ssn_resolve("$s12Tomorrowland7PromiseVMa");
    GenericMeta page=(GenericMeta)ssn_resolve("$s9TwitchKit10PageCursorVMa");
    SW Response (*tuple_meta)(uintptr_t,const void*,const void*,const char*,const void*)=dlsym(RTLD_DEFAULT,"swift_getTupleTypeMetadata2");
    current_user=(Getter)ssn_resolve("$s14TwitchIdentity11CurrentUserV4user0A4Core0D0Vvg");
    user_identity=(Getter)ssn_resolve("$s10TwitchCore4UserV8identityAA8IdentityVvg");
    identity_name=(StringGetter)ssn_resolve("$s10TwitchCore8IdentityV4nameSSvg");
    identity_display=(StringGetter)ssn_resolve("$s10TwitchCore8IdentityV11displayNameSSvg");
    promise_objc=(PromiseObjC)ssn_resolve("$s12Tomorrowland7PromiseV4objc8mapValue0D5ErrorSo10TWLPromiseCyqd__qd_0_Gqd__xc_qd_0_q_ctRld__CRld_0_Cr0_lF");
    current_request=(CurrentRequest)ssn_resolve("$s9TwitchKit9TKGraphQLC11currentUser12Tomorrowland7PromiseVy0A8Identity07CurrentF0V0A6Apollo0A12GraphQLErrorVGyF");
    follow_request=(FollowRequest)ssn_resolve("$s9TwitchKit9TKGraphQLC13followedUsers5limit6cursor14blockedUserIDs12Tomorrowland7PromiseVySay0A4Core0J0VG_AA10PageCursorVyAA09_FollowedF0OGt0A6Apollo0A12GraphQLErrorVGSi_ASSgShys6UInt32VGtF");
    if(!bridge||!dynamic_cast||!objc_meta||!array||!optional||!set||!conformance||!promise||!page||!tuple_meta||
       !current_user||!user_identity||!identity_name||!identity_display||!promise_objc||!current_request||!follow_request) return false;
    user_type=metadata("$s10TwitchCore4UserVMa"); current_type=metadata("$s14TwitchIdentity11CurrentUserVMa");
    identity_type=metadata("$s10TwitchCore8IdentityVMa");
    const void *marker=metadata("$s9TwitchKit14_FollowedUsersOMa");
    /* The marker is an empty enum: a zero value size is valid for this type. */
    if(!marker) { Meta fn=(Meta)ssn_resolve("$s9TwitchKit14_FollowedUsersOMa"); if(fn) { Response r=fn(0); if(!r.state) marker=r.value; } }
    string_type=dlsym(RTLD_DEFAULT,"$sSSN");
    const void *error=dlsym(RTLD_DEFAULT,"$s12TwitchApollo0A12GraphQLErrorVN");
    const void *uint32=dlsym(RTLD_DEFAULT,"$ss6UInt32VN"),*hashable=dlsym(RTLD_DEFAULT,"$sSHMp");
    if(!user_type||!current_type||!identity_type||!marker||!error||!uint32||!hashable||value_size(string_type)!=16) return false;
    Response ar=array(0,user_type),pa=page(0,marker);
    if(ar.state||pa.state||value_size(ar.value)!=8||value_size(pa.value)!=17||vw(pa.value)[9]!=24) return false;
    array_type=ar.value; page_type=pa.value;
    Response tu=tuple_meta(0,array_type,page_type,NULL,NULL);
    if(tu.state||value_size(tu.value)!=8+value_size(page_type)||vw(tu.value)[9]!=32) return false;
    tuple_type=tu.value; const uintptr_t *t=tuple_type;
    if(t[0]!=0x301||t[1]!=2||t[3]!=(uintptr_t)array_type||t[4]!=0||t[5]!=(uintptr_t)page_type||t[6]!=8) return false;
    Response ap=promise(0,current_type,error),fp=promise(0,tuple_type,error);
    if(ap.state||fp.state||value_size(ap.value)!=8||value_size(fp.value)!=8) return false;
    account_promise_type=ap.value; follows_promise_type=fp.value;
    Response op=optional(0,page_type); if(op.state||value_size(op.value)!=17||vw(op.value)[9]!=24) return false;
    ((StoreTag)vw(page_type)[7])(&nil_cursor,1,1,page_type);
    if(((GetTag)vw(page_type)[6])(&nil_cursor,1,page_type)!=1) return false;
    const void *witness=conformance(uint32,hashable); if(!witness) return false;
    Response se=set(0,uint32,witness); if(se.state||value_size(se.value)!=8) return false;
    set_type=se.value; objc_type=objc_meta(objc_getClass("NSObject"));
    id empty=m0(c("NSSet"),"set");
    if(!objc_type||!dynamic_cast(&empty_set,&empty,objc_meta(objc_getClass("NSSet")),set_type,0)) return false;
    Class g=objc_getClass("_TtC9TwitchKit9TKGraphQL"),p=objc_getClass("TWLPromise"),h=objc_getClass("_TtC6PMHTTP11HTTPManager");
    if(!method_is(g,"sharedInstance","@16@0:8",true)||!method_is(p,"getValue:error:","B32@0:8^@16^@24",false)||!method_is(p,"requestCancel","v16@0:8",false)||
       !method_is(h,"defaultManager","@16@0:8",true)||!method_is(h,"defaultAuth","@16@0:8",false)) return false;
    graph=objc_retain(m0((id)g,"sharedInstance"));
    available=graph!=nil; return available;
}
bool ssn_account_refreshing(void) { return active_promise!=nil; }
id ssn_account_info(void) { return account; }
id ssn_followed_channels(void) { return channels; }
static id authorization(void) { return m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth"); }
static bool authorized(void) { return authorization()!=nil; }
static void clear(void) {
    if(account || channels) ssn_account_data_cleared();
    objc_release(account); account=nil; objc_release(channels); channels=nil;
    objc_release(verified_auth); verified_auth=nil; objc_release(request_auth); request_auth=nil;
}
void ssn_account_changed(void) {
    generation++; waiting_ticks=0; clear();
    if(active_promise) { v0(active_promise,"requestCancel"); objc_release(active_promise); active_promise=nil; }
    ssn_service(SSN_SESSION_CHANGED,0); ssn_ui_changed();
}
void ssn_account_event(unsigned event) {
    /* Only compare opaque object identity with the authorization that supplied
     * the successful currentUser result. Presence alone cannot retain a session.
     * Login/logout/token changes always invalidate, including same-object cases. */
    bool preserve=SSN_NATIVE && account && verified_auth &&
        ssn_preserve_account_event(event,authorization()==verified_auth);
    ssn_account_observed(event,preserve);
    if(!preserve) ssn_account_changed();
    ssn_report();
}
static void poll(void *context);
static bool request(bool follows) {
    const void *type=follows?follows_promise_type:account_promise_type;
#if SSN_SWIFTUI
    if(follows) {
        const void *error=dlsym(RTLD_DEFAULT,"$s12TwitchApollo0A12GraphQLErrorVN");
        type=ssn_feed_promise_type((PairMeta)ssn_resolve("$s12Tomorrowland7PromiseVMa"),error);
    }
#endif
    void *value=allocate(type); if(!value) return false;
    if(follows) {
#if SSN_SWIFTUI
        ssn_feed_request(value,graph);
#else
        follow_request(value,50,nil_cursor.a,nil_cursor.b,nil_cursor.c,empty_set,graph);
#endif
    }
    else {
        objc_release(request_auth); request_auth=objc_retain(authorization());
        current_request(value,graph);
    }
    Map mapper=map_follows;
#if SSN_SWIFTUI
    mapper=ssn_feed_map;
#endif
    id promise=promise_objc(follows?mapper:map_account,NULL,map_error,NULL,type,objc_type,objc_type,value);
    destroy(value,type);
    if(!kind(promise,"TWLPromise")) { objc_release(promise); return false; }
    active_promise=promise; checking_follows=follows; waiting_ticks=0;
    dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,250000000),dispatch_get_main_queue(),(void*)(uintptr_t)generation,poll);
    return true;
}
static void poll(void *context) {
    if((uint64_t)(uintptr_t)context!=generation||!active_promise) return;
    id value=nil,error=nil;
    BOOL done=((BOOL(*)(id,SEL,id*,id*))objc_msgSend)(active_promise,ss("getValue:error:"),&value,&error);
    if(!done && ++waiting_ticks<120) {
        dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,250000000),dispatch_get_main_queue(),context,poll); return;
    }
    id promise=active_promise; active_promise=nil;
    if(!done) v0(promise,"requestCancel");
    if(!authorized()||authorization()!=request_auth||error||!done||!(checking_follows?kind(value,"NSArray"):kind(value,"NSDictionary"))) {
        bool broken=atomic_load(&mapping_fault)||ssn_failed();
#if SSN_SWIFTUI
        if(checking_follows && account && authorized() && authorization()==verified_auth && authorization()==request_auth && !broken) {
            /* A failed feed request does not erase the preceding verified
             * account. Native account-change signals still clear everything. */
            ssn_service(SSN_FEED_FAILED,(unsigned)num(channels,"count"));
        } else
#endif
        { clear();ssn_service(broken?SSN_ABI_FAILED:(authorized()?SSN_REQUEST_FAILED:SSN_SIGNED_OUT),0); }
    } else if(checking_follows) {
        objc_release(channels); channels=objc_retain(value); ssn_service(num(channels,"count")?SSN_READY:SSN_EMPTY,(unsigned)num(channels,"count"));
    } else {
        /* Current-user verification must not transfer another account's feed.
         * Authoritative account notifications already cancel and clear; this
         * comparison also covers an account change observed by refresh first. */
        id previous=m1(account,"objectForKey:",ns("username"));
        id next=m1(value,"objectForKey:",ns("username"));
        if(!previous || !((BOOL(*)(id,SEL,id))objc_msgSend)(previous,ss("isEqualToString:"),next)) {
            if(channels) ssn_account_data_cleared();
            objc_release(channels); channels=nil;
        }
        objc_release(verified_auth); verified_auth=objc_retain(request_auth);
        objc_release(account); account=objc_retain(value);
        if(!channels) ssn_service(SSN_LOADING_FOLLOWS,0);
        if(!request(true)) { clear(); ssn_service(SSN_ABI_FAILED,0); ssn_failure(3); }
    }
    objc_release(promise); ssn_report(); ssn_ui_changed();
}
void ssn_account_refresh(void) {
    if(!SSN_NATIVE) return;
    if(!ssn_armed()) { ssn_failure(0); ssn_service(SSN_MONITOR_FAILED,0); ssn_ui_changed(); ssn_report(); return; }
    /* Ordinary foreground/manual refresh keeps verified presentation data.
     * Real account events still use ssn_account_changed(), which clears it.
     * Incrementing the request generation rejects cancelled/stale completions. */
    generation++; waiting_ticks=0;
    if(active_promise) { v0(active_promise,"requestCancel"); objc_release(active_promise); active_promise=nil; }
    if(!initialize()) { ssn_service(SSN_ABI_FAILED,0); ssn_failure(3); }
    else if(!authorized()) { clear(); ssn_service(SSN_SIGNED_OUT,0); }
    else {
        if(account && authorization()!=verified_auth) clear();
        if(!account) ssn_service(SSN_LOADING_ACCOUNT,0);
        if(!request(false)) { clear(); ssn_service(SSN_ABI_FAILED,0); ssn_failure(3); }
    }
    ssn_ui_changed(); ssn_report();
}
