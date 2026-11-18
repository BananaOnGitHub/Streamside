/* Native frontend adapter for the shared, pinned VAFT engine. Only Foundation
 * request boundaries are installed. No legacy constructor/emote/RN code links. */
#import <Foundation/Foundation.h>
#import <objc/message.h>
#import <objc/runtime.h>
#import "SSNAdBlock.h"
#import "SSNPlaybackRequest.h"
#import "SSNCore.h"
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "TASDiagnostics.h"

static _Atomic bool installed, preference;
static _Atomic uint64_t epoch;
static _Atomic unsigned queued;
static _Thread_local uint64_t workEpoch;
static _Thread_local NSTimeInterval workDeadline;
static _Thread_local _Atomic bool *workCancelled;
static dispatch_queue_t engineQueue;
static NSURLSession *transport;
static bool workActive(void) { return (workEpoch&1) && (!workCancelled||!atomic_load(workCancelled)) && workEpoch==atomic_load(&epoch); }
static bool validWork(void) { return workActive()&&NSProcessInfo.processInfo.systemUptime<workDeadline; }
static id msg0(id o,const char *s) { return ((id(*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static id msg2(id o,const char *s,id a,id b) { return ((id(*)(id,SEL,id,id))objc_msgSend)(o,sel_registerName(s),a,b); }
static id nsstr(const char *s) { return s?[NSString stringWithUTF8String:s]:nil; }
static id nsurl(const char *s) { return [NSURL URLWithString:nsstr(s)]; }
static const char *utf8(id o) { return [o UTF8String]; }
static NSInteger imsg0(id o,const char *s) { return ((NSInteger(*)(id,SEL))objc_msgSend)(o,sel_registerName(s)); }
static const uint8_t *data_bytes(id d) { return [d bytes]; }
static size_t data_length(id d) { return [d length]; }
/* Numeric metrics only. Neither the legacy event strings nor URL/content/header
 * diagnostics are forwarded to the native export. */
unsigned tas_diag_policy_word(void) { return 0; }
void tas_diag_metric(TASDiagnosticMetric metric,uint64_t amount) { ssn_adblock_metric((unsigned)metric,amount); }
void tas_diag_log(const char *e,const char *d) { (void)e;(void)d; }
void tas_diag_log_url(const char *e,const char *u,const char *d) { (void)e;(void)u;(void)d; }
void tas_diag_log_stream(const char *e,const char *c,const char *u,const char *d) { (void)e;(void)c;(void)u;(void)d; }
#include "TASVAFT.h"
#include "TASVAFTBlank.h"

static id accountIdentity(void) { return msg0(msg0((id)objc_getClass("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth"); }
@interface SSNVAFTToken : NSObject
@property(nonatomic,strong) id promise;
@property(nonatomic,strong) id account;
@property(nonatomic,strong) NSDictionary *value;
@property(nonatomic) uint64_t epoch;
@property(nonatomic) NSTimeInterval deadline;
@property(atomic) BOOL cancelled;
@property(nonatomic,strong) dispatch_semaphore_t done;
- (void)poll;
- (void)cancel;
@end
@implementation SSNVAFTToken
- (void)cancel {
    if(_promise) { ((void(*)(id,SEL))objc_msgSend)(_promise,sel_registerName("requestCancel"));_promise=nil; }
}
- (void)poll {
    if(self.cancelled||_epoch!=atomic_load(&epoch)||!ssn_playback_authorized()||_account!=accountIdentity()||NSProcessInfo.processInfo.systemUptime>=_deadline) {
        [self cancel];dispatch_semaphore_signal(_done);return;
    }
    id value=nil,error=nil;
    BOOL ready=((BOOL(*)(id,SEL,id*,id*))objc_msgSend)(_promise,sel_registerName("getValue:error:"),&value,&error);
    if(ready) {
        if(!error&&[value isKindOfClass:NSDictionary.class]) _value=value;
        _promise=nil;dispatch_semaphore_signal(_done);return;
    }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,50*NSEC_PER_MSEC),dispatch_get_main_queue(),^{[self poll];});
}
@end
static bool request_access_token(const char *channel,const char *player_type,char *signature,size_t signature_capacity,char *token,size_t token_capacity) {
    if(!validWork()||NSThread.isMainThread) return false;
    SSNVAFTToken *attempt=[SSNVAFTToken new];attempt.epoch=workEpoch;
    attempt.deadline=fmin(workDeadline,NSProcessInfo.processInfo.systemUptime+6);attempt.done=dispatch_semaphore_create(0);
    NSString *name=nsstr(channel),*type=nsstr(player_type);
    dispatch_async(dispatch_get_main_queue(),^{
        if(attempt.cancelled||attempt.epoch!=atomic_load(&epoch)||NSProcessInfo.processInfo.systemUptime>=attempt.deadline||!ssn_playback_authorized()) { dispatch_semaphore_signal(attempt.done);return; }
        attempt.account=accountIdentity();
        // Native request still owns integrity, authorization and renewal. No
        // OAuth/header capture, public token endpoint or synthetic device ID.
        attempt.promise=ssn_playback_request_variant(name,type,[type isEqual:@"autoplay"]?@"android":@"web");
        if(!attempt.promise) { dispatch_semaphore_signal(attempt.done);return; }
        [attempt poll];
    });
    while(dispatch_semaphore_wait(attempt.done,dispatch_time(DISPATCH_TIME_NOW,50*NSEC_PER_MSEC))) {
        if(!validWork()||NSProcessInfo.processInfo.systemUptime>=attempt.deadline) {
            attempt.cancelled=YES;dispatch_async(dispatch_get_main_queue(),^{[attempt cancel];});if(workActive()) tas_diag_metric(TAS_DIAG_TOKEN_FAILURE,1);return false;
        }
    }
    // Completion publication is synchronized by the semaphore. Dictionary never
    // leaves this private worker and is never included in diagnostic evidence.
    NSString *sig=attempt.value[@"signature"],*value=attempt.value[@"value"];
    if(!validWork()) return false;
    if(![sig isKindOfClass:NSString.class]||![value isKindOfClass:NSString.class]||
       !sig.length||!value.length||strlen(sig.UTF8String)>=signature_capacity||strlen(value.UTF8String)>=token_capacity) {
        tas_diag_metric(TAS_DIAG_TOKEN_FAILURE,1);return false;
    }
    copy_string(signature,signature_capacity,sig.UTF8String);copy_string(token,token_capacity,value.UTF8String);return true;
}
static bool safeURL(NSURL *url) {
    NSString *host=url.host.lowercaseString;
    return [url.scheme isEqual:@"https"] && !url.user && !url.password &&
        ([host isEqual:@"ttvnw.net"]||[host hasSuffix:@".ttvnw.net"]||[host isEqual:@"twitch.tv"]||[host hasSuffix:@".twitch.tv"]);
}
static NSData *fetch(NSURLRequest *original,NSHTTPURLResponse **response,NSError **error) {
    if(!validWork()||!safeURL(original.URL)) return nil;
    NSMutableURLRequest *request=[original mutableCopy];[request setValue:@"1" forHTTPHeaderField:@"X-TAS-Internal"];
    request.timeoutInterval=fmax(.05,fmin(6,workDeadline-NSProcessInfo.processInfo.systemUptime));
    __block NSData *body=nil;__block NSHTTPURLResponse *reply=nil;__block NSError *failure=nil;
    dispatch_semaphore_t done=dispatch_semaphore_create(0);
    NSURLSessionDataTask *task=[transport dataTaskWithRequest:request completionHandler:^(NSData *d,NSURLResponse *r,NSError *e) {
        body=d;reply=[r isKindOfClass:NSHTTPURLResponse.class]?(NSHTTPURLResponse *)r:nil;failure=e;dispatch_semaphore_signal(done);
    }];
    [task resume];
    while(dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,50*NSEC_PER_MSEC))) {
        if(!validWork()) { [task cancel];return nil; }
    }
    *response=reply;*error=failure;
    return body;
}
static bool fetch_bytes(const char *url,id *data,id *response) {
    NSHTTPURLResponse *reply=nil;NSError *error=nil;NSData *body=fetch([NSURLRequest requestWithURL:nsurl(url)],&reply,&error);
    *data=body;*response=reply;
    return !error&&reply.statusCode>=200&&reply.statusCode<300&&body.length>=7&&body.length<=TAS_MANIFEST_CAPACITY&&!memcmp(body.bytes,"#EXTM3U",7)&&!memchr(body.bytes,0,body.length);
}
@interface SSNVAFTProtocol : NSURLProtocol {
    BOOL _stopped,_completed;
    _Atomic bool _cancelled;
    uint64_t _epoch;
    NSTimeInterval _deadline;
}
@end
@implementation SSNVAFTProtocol
+ (BOOL)canInitWithRequest:(NSURLRequest *)request {
    if(!atomic_load(&installed)||!(atomic_load(&epoch)&1)||[request valueForHTTPHeaderField:@"X-TAS-Internal"]||
       (request.HTTPMethod&&![request.HTTPMethod isEqual:@"GET"])||!safeURL(request.URL)) return NO;
    const char *url=request.URL.absoluteString.UTF8String;
    return ([request.URL.path.lowercaseString hasSuffix:@".m3u8"]&&is_twitch_hls_url(url))||is_cached_ad_segment(url);
}
+ (NSURLRequest *)canonicalRequestForRequest:(NSURLRequest *)request { return request; }
- (void)stopLoading { atomic_store(&_cancelled,true);@synchronized(self) { _stopped=YES; } }
- (void)deliver:(NSData *)data response:(NSHTTPURLResponse *)response error:(NSError *)error {
    @synchronized(self) {
        if(_stopped||_completed) return;
        if(_epoch!=atomic_load(&epoch)) { data=nil;error=[NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorCancelled userInfo:nil]; }
        _completed=YES;
        if(error||!data||!response) {
            if(error.code!=NSURLErrorCancelled) tas_diag_metric(TAS_DIAG_HLS_FAILURE,1);
            // Never export Foundation errors: their userInfo may hold signed URLs.
            [self.client URLProtocol:self didFailWithError:error?:[NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorCannotLoadFromNetwork userInfo:nil]];return;
        }
        [self.client URLProtocol:self didReceiveResponse:response cacheStoragePolicy:NSURLCacheStorageNotAllowed];
        if(_stopped) return;
        [self.client URLProtocol:self didLoadData:data];
        if(!_stopped) [self.client URLProtocolDidFinishLoading:self];
    }
}
- (void)startLoading {
    _epoch=atomic_load(&epoch);_deadline=NSProcessInfo.processInfo.systemUptime+15;
    if(atomic_fetch_add(&queued,1)>=32) {
        atomic_fetch_sub(&queued,1);[self deliver:nil response:nil error:nil];return;
    }
    dispatch_async(engineQueue,^{ @autoreleasepool {
        workEpoch=self->_epoch;workDeadline=self->_deadline;workCancelled=&self->_cancelled;
        BOOL stopped;@synchronized(self) { stopped=self->_stopped; }
        if(stopped||!validWork()) { [self deliver:nil response:nil error:nil];atomic_fetch_sub(&queued,1);return; }
        NSURLRequest *request=self.request;const char *url=request.URL.absoluteString.UTF8String;
        NSData *data=nil;NSHTTPURLResponse *response=nil;NSError *error=nil;
        if(is_cached_ad_segment(url)) {
            data=[[NSData alloc] initWithBase64EncodedString:@TAS_VAFT_BLANK_BASE64 options:0];
            response=[[NSHTTPURLResponse alloc] initWithURL:request.URL statusCode:200 HTTPVersion:@"HTTP/1.1" headerFields:@{@"Content-Type":@"video/mp4",@"Content-Length":@(data.length).stringValue}];
            tas_diag_metric(TAS_DIAG_SYNTHETIC_SEGMENT,1);
        } else {
            tas_diag_metric(TAS_DIAG_HLS_INTERCEPTED,1);data=fetch(request,&response,&error);
            if(!error&&response.statusCode>=200&&response.statusCode<300&&data.length&&data.length<=TAS_MANIFEST_CAPACITY&&
               data.length>=7&&!memcmp(data.bytes,"#EXTM3U",7)&&!memchr(data.bytes,0,data.length)) {
                char *text=copy_data_text(data),*processed=process_manifest(url,text,false);free(text);
                if(processed) {
                    data=[NSData dataWithBytes:processed length:strlen(processed)];free(processed);
                    // Transfer encoding/content length/encoding headers describe
                    // the origin body and must not survive playlist rewriting.
                    response=[[NSHTTPURLResponse alloc] initWithURL:request.URL statusCode:response.statusCode HTTPVersion:@"HTTP/1.1" headerFields:@{@"Content-Type":@"application/vnd.apple.mpegurl",@"Content-Length":@(data.length).stringValue}];
                }
            }
        }
        if(response.statusCode>=400&&!error) tas_diag_metric(TAS_DIAG_HLS_FAILURE,1);
        [self deliver:data response:response error:error];workEpoch=0;atomic_fetch_sub(&queued,1);
    }});
}
@end
static void addProtocol(NSURLSessionConfiguration *configuration) {
    if(configuration.identifier) return; // Foundation excludes background sessions.
    NSMutableArray *classes=[configuration.protocolClasses mutableCopy]?:[NSMutableArray new];
    if(![classes containsObject:SSNVAFTProtocol.class]) [classes insertObject:SSNVAFTProtocol.class atIndex:0];
    configuration.protocolClasses=classes;
}
static IMP originalDefault,originalEphemeral,originalSession,originalDelegateSession;
static id defaultConfiguration(id self,SEL cmd) { id result=((id(*)(id,SEL))originalDefault)(self,cmd);addProtocol(result);return result; }
static id ephemeralConfiguration(id self,SEL cmd) { id result=((id(*)(id,SEL))originalEphemeral)(self,cmd);addProtocol(result);return result; }
static id sessionConfiguration(id self,SEL cmd,id config) { addProtocol(config);return ((id(*)(id,SEL,id))originalSession)(self,cmd,config); }
static id delegateSession(id self,SEL cmd,id config,id delegate,id queue) { addProtocol(config);return ((id(*)(id,SEL,id,id,id))originalDelegateSession)(self,cmd,config,delegate,queue); }
void ssn_adblock_install(void) {
    NSCAssert(NSThread.isMainThread,@"VAFT startup belongs to main");
    if(!ssn_native_mode()||atomic_load(&installed)) return;
    [NSUserDefaults.standardUserDefaults registerDefaults:@{@SSN_ADBLOCK_KEY:@YES}];
    atomic_store(&preference,[NSUserDefaults.standardUserDefaults boolForKey:@SSN_ADBLOCK_KEY]);
    engineQueue=dispatch_queue_create("dev.streamside.vaft",DISPATCH_QUEUE_SERIAL);
    // Inner transport predates registration and also rejects its own guarded
    // requests. It never receives native account/session headers.
    NSURLSessionConfiguration *config=NSURLSessionConfiguration.ephemeralSessionConfiguration;
    config.HTTPCookieStorage=nil;config.URLCache=nil;config.HTTPAdditionalHeaders=@{};
    transport=[NSURLSession sessionWithConfiguration:config];
    Class cfg=NSURLSessionConfiguration.class,session=NSURLSession.class;
    SEL selectors[]={@selector(defaultSessionConfiguration),@selector(ephemeralSessionConfiguration),@selector(sessionWithConfiguration:),@selector(sessionWithConfiguration:delegate:delegateQueue:)};
    Method methods[]={class_getClassMethod(cfg,selectors[0]),class_getClassMethod(cfg,selectors[1]),class_getClassMethod(session,selectors[2]),class_getClassMethod(session,selectors[3])};
    for(unsigned i=0;i<4;i++) if(!methods[i]) { ssn_adblock_state(atomic_load(&preference),false);return; }
    originalDefault=method_setImplementation(methods[0],(IMP)defaultConfiguration);
    originalEphemeral=method_setImplementation(methods[1],(IMP)ephemeralConfiguration);
    originalSession=method_setImplementation(methods[2],(IMP)sessionConfiguration);
    originalDelegateSession=method_setImplementation(methods[3],(IMP)delegateSession);
    [NSURLProtocol registerClass:SSNVAFTProtocol.class];atomic_store(&installed,true);
    ssn_adblock_state(atomic_load(&preference),true);
}
bool ssn_adblock_enabled(void) { return ssn_native_mode()&&atomic_load(&installed)&&atomic_load(&preference); }
bool ssn_adblock_active(void) { return atomic_load(&installed)&&(atomic_load(&epoch)&1); }
void ssn_adblock_set_enabled(bool enabled) {
    [NSUserDefaults.standardUserDefaults setBool:enabled forKey:@SSN_ADBLOCK_KEY];atomic_store(&preference,enabled);
    ssn_adblock_state(enabled,atomic_load(&installed));
}
uint64_t ssn_adblock_begin(void) {
    if(!ssn_adblock_enabled()) return 0;
    uint64_t next=(atomic_load(&epoch)+2)|1;atomic_store(&epoch,next);
    dispatch_async(engineQueue,^{
        pthread_mutex_lock(&g_lock);
        for(size_t i=0;i<TAS_MAX_STREAMS;i++) clear_stream_context_locked(i,"native_playback_restart");
        memset(g_ad_segments,0,sizeof(g_ad_segments));g_next_ad_segment=0;
        pthread_mutex_unlock(&g_lock);
    });return next;
}
void ssn_adblock_end(uint64_t lease) {
    if(!lease) return;
    uint64_t expected=lease;atomic_compare_exchange_strong(&epoch,&expected,lease+1);
}
