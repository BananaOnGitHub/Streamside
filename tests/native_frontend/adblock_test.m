/* Real Foundation and production VAFT/transport, synthetic network and native
 * promise. No donor, credentials, ads from a real account, or public traffic. */
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import "SSNAdBlock.h"
#import "SSNPlaybackRequest.h"
#include <stdatomic.h>
#include <stdlib.h>
static BOOL nativeMode,authorized=YES,allStitched,pendingToken;
static id identity;
static atomic_uint tokenCalls,tokenCancels,originAdRequests;
static uint64_t metrics[11];
static BOOL stateEnabled,stateInstalled;
bool ssn_native_mode(void) { return nativeMode; }
bool ssn_playback_authorized(void) { return authorized; }
void ssn_adblock_state(bool enabled,bool installed) { stateEnabled=enabled;stateInstalled=installed; }
void ssn_adblock_metric(unsigned key,uint64_t n) { NSCAssert(key<11,@"metric index");metrics[key]+=n; }
__attribute__((objc_runtime_name("_TtC6PMHTTP11HTTPManager")))
@interface FakeHTTP : NSObject
+ (id)defaultManager;
- (id)defaultAuth;
@end
@implementation FakeHTTP
+ (id)defaultManager { static id value;static dispatch_once_t once;dispatch_once(&once,^{value=[self new];});return value; }
- (id)defaultAuth { return identity; }
@end
@interface FakeGrant : NSObject
@property(nonatomic,strong) NSString *type;
@property(nonatomic,strong) id account;
- (BOOL)getValue:(id *)value error:(id *)error;
- (void)requestCancel;
@end
@implementation FakeGrant
- (BOOL)getValue:(id *)value error:(id *)error {
    NSCAssert(NSThread.isMainThread,@"Native promise poll must remain on main");(void)error;
    if(pendingToken) return NO;
    *value=@{@"signature":@"fixture-signature",@"value":_type};return YES;
}
- (void)requestCancel { atomic_fetch_add(&tokenCancels,1); }
@end
id ssn_playback_request_variant(id channel,id type,id platform) {
    NSCAssert(NSThread.isMainThread&&authorized&&[channel length],@"Native request boundary");
    NSCAssert(([@[@"embed",@"popout",@"autoplay"] containsObject:type]),@"VAFT player order");
    NSCAssert([platform isEqual:[type isEqual:@"autoplay"]?@"android":@"web"],@"Pinned platform pair");
    atomic_fetch_add(&tokenCalls,1);FakeGrant *grant=[FakeGrant new];grant.type=type;grant.account=identity;return grant;
}
static NSString *master(NSString *path) {
    return [NSString stringWithFormat:@"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=4000000,RESOLUTION=1280x720,FRAME-RATE=60\nhttps://video.ttvnw.net/%@.m3u8\n",path];
}
static NSString *media(BOOL stitched,NSString *segment) {
    return [NSString stringWithFormat:@"#EXTM3U\n%@#EXT-X-TARGETDURATION:2\n#EXTINF:2.0,%@\n%@.ts\n",stitched?@"#EXT-X-DATERANGE:ID=\"stitched-ad\"\n":@"",stitched?@"ad":@"live",segment];
}
@interface FakeNetwork : NSURLProtocol
@end
@implementation FakeNetwork
+ (BOOL)canInitWithRequest:(NSURLRequest *)request { return [request.URL.host hasSuffix:@".ttvnw.net"]; }
+ (NSURLRequest *)canonicalRequestForRequest:(NSURLRequest *)r { return r; }
- (void)stopLoading {}
- (void)startLoading {
    NSURL *url=self.request.URL;NSString *path=url.path;NSString *text;
    NSCAssert(![self.request valueForHTTPHeaderField:@"Authorization"]&&![self.request valueForHTTPHeaderField:@"Client-Integrity"],@"No captured native credentials");
    if([path containsString:@"/channel/hls/"]) {
        NSString *token=@"original";
        for(NSURLQueryItem *item in [NSURLComponents componentsWithURL:url resolvingAgainstBaseURL:YES].queryItems)
            if([item.name isEqual:@"token"]) token=item.value;
        BOOL beta=[path containsString:@"beta"];
        text=master([token isEqual:@"original"]?(beta?@"beta-original":@"original"):[@"alternate-" stringByAppendingString:token]);
    } else if([path containsString:@"alternate-"]) {
        text=media(allStitched,@"alternate-content");
    } else if([path containsString:@"beta-original"]) {
        text=media(NO,@"beta-live");
    } else if([path hasSuffix:@".ts"]) {
        atomic_fetch_add(&originAdRequests,1);text=@"ORIGIN AD SEGMENT";
    } else {
        text=media(YES,@"original-ad");
    }
    NSData *data=[text dataUsingEncoding:NSUTF8StringEncoding];
    NSHTTPURLResponse *response=[[NSHTTPURLResponse alloc] initWithURL:url statusCode:200 HTTPVersion:@"HTTP/1.1" headerFields:@{@"Content-Type":@"application/vnd.apple.mpegurl",@"Content-Length":@(data.length).stringValue}];
    [self.client URLProtocol:self didReceiveResponse:response cacheStoragePolicy:NSURLCacheStorageNotAllowed];
    [self.client URLProtocol:self didLoadData:data];[self.client URLProtocolDidFinishLoading:self];
}
@end
static IMP originalEphemeral;
static id testEphemeral(id self,SEL cmd) {
    NSURLSessionConfiguration *config=((id(*)(id,SEL))originalEphemeral)(self,cmd);
    config.protocolClasses=@[FakeNetwork.class];return config;
}
static BOOL waitUntil(BOOL (^condition)(void),NSTimeInterval seconds) {
    NSTimeInterval deadline=NSProcessInfo.processInfo.systemUptime+seconds;
    while(!condition()&&NSProcessInfo.processInfo.systemUptime<deadline)
        [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.01]];
    return condition();
}
@interface FetchResult : NSObject
@property(atomic) BOOL done;
@property(nonatomic,strong) NSData *body;
@property(nonatomic,strong) NSError *error;
@property(nonatomic,strong) NSHTTPURLResponse *response;
@end
@implementation FetchResult
@end
static NSURLSessionDataTask *start(NSURLSession *session,NSString *url,FetchResult *result) {
    NSURLSessionDataTask *task=[session dataTaskWithURL:[NSURL URLWithString:url] completionHandler:^(NSData *d,NSURLResponse *r,NSError *e) {
        result.body=d;result.error=e;result.response=(NSHTTPURLResponse *)r;result.done=YES;
    }];[task resume];return task;
}
static NSData *get(NSURLSession *session,NSString *url) {
    FetchResult *result=[FetchResult new];start(session,url,result);
    NSCAssert(waitUntil(^BOOL{return result.done;},10),@"Transport deadline");
    NSCAssert(!result.error&&result.response.statusCode==200&&result.body.length,@"Fixture transport failed: %@",result.error);
    NSCAssert([result.response.allHeaderFields[@"Content-Length"] longLongValue]==(long long)result.body.length,@"Rewritten content length");
    return result.body;
}
static NSString *text(NSURLSession *session,NSString *url) { return [[NSString alloc] initWithData:get(session,url) encoding:NSUTF8StringEncoding]; }
static NSString *const source=@"https://usher.ttvnw.net/api/channel/hls/fixture.m3u8?token=original&sig=fixture";
int main(int argc,const char **argv) { @autoreleasepool {
    NSCAssert(argc==2,@"native/baseline required");nativeMode=strcmp(argv[1],"baseline")!=0;identity=[NSObject new];
    if(!strcmp(argv[1],"restored-off")) {
        ssn_adblock_install();NSCAssert(stateInstalled&&!stateEnabled&&!ssn_adblock_enabled()&&!ssn_adblock_begin(),@"Off persists across process restart");
        puts("VAFT_PREFERENCE PASS: restored Off in fresh process");return 0;
    }
    [NSUserDefaults.standardUserDefaults removeObjectForKey:@SSN_ADBLOCK_KEY];
    originalEphemeral=method_setImplementation(class_getClassMethod(NSURLSessionConfiguration.class,@selector(ephemeralSessionConfiguration)),(IMP)testEphemeral);
    NSArray *before=NSURLSessionConfiguration.ephemeralSessionConfiguration.protocolClasses;
    ssn_adblock_install();
    if(!nativeMode) {
        NSCAssert(!stateInstalled&&!stateEnabled&&!ssn_adblock_enabled()&&!ssn_adblock_begin(),@"Baseline must stay untouched");
        NSCAssert([before isEqual:NSURLSessionConfiguration.ephemeralSessionConfiguration.protocolClasses],@"Baseline session adapter installed");
        puts("VAFT_BASELINE PASS: no registration, session changes, lease or filtering");return 0;
    }
    NSCAssert(stateInstalled&&stateEnabled&&ssn_adblock_enabled(),@"Default enabled");
    Class protocol=NSClassFromString(@"SSNVAFTProtocol");
    uint64_t lease=ssn_adblock_begin();NSCAssert(lease&&ssn_adblock_active(),@"Playback-scoped admission");
    for(NSString *url in @[@"https://ttvnw.net.attacker.example/a.m3u8",@"https://attacker.example/ttvnw.net/a.m3u8",@"https://gql.twitch.tv/gql",@"https://cdn.7tv.app/a.webp",@"http://video.ttvnw.net/a.m3u8"]) {
        NSCAssert(![protocol canInitWithRequest:[NSURLRequest requestWithURL:[NSURL URLWithString:url]]],@"Overbroad request admission");
    }
    NSURLSession *session=[NSURLSession sessionWithConfiguration:NSURLSessionConfiguration.ephemeralSessionConfiguration];
    NSCAssert([text(session,source) containsString:@"original.m3u8"],@"Master registration");
    NSString *clean=text(session,@"https://video.ttvnw.net/original.m3u8");
    NSCAssert(![clean containsString:@"stitched"]&&[clean containsString:@"https://video.ttvnw.net/alternate-content.ts"],@"Clean alternate and relative URL base");
    NSCAssert(metrics[4]==1&&atomic_load(&tokenCalls)==1,@"Native embed token and clean swap");
    clean=text(session,@"https://video.ttvnw.net/original.m3u8");
    NSCAssert(![clean containsString:@"stitched"]&&atomic_load(&tokenCalls)==1,@"Clean variant reuse");
    text(session,@"https://usher.ttvnw.net/api/channel/hls/beta.m3u8?token=original");
    NSCAssert([text(session,@"https://video.ttvnw.net/beta-original.m3u8") containsString:@"beta-live.ts"],@"Independent stream ownership");
    NSString *unmapped=text(session,@"https://video.ttvnw.net/unmapped.m3u8");
    NSCAssert([unmapped containsString:@"original-ad.ts"]&&![unmapped containsString:@"alternate-content"]&&metrics[7]==1,@"Unmapped variant must not borrow another stream");
    ssn_adblock_end(lease);lease=ssn_adblock_begin();allStitched=YES;
    text(session,source);text(session,@"https://video.ttvnw.net/original.m3u8");
    NSCAssert(atomic_load(&tokenCalls)==4&&metrics[5]>0,@"All VAFT candidates then segment fallback");
    NSData *blank=get(session,@"https://video.ttvnw.net/alternate-content.ts");
    NSCAssert(blank.length>100&&memmem(blank.bytes,blank.length,"ftyp",4)&&!atomic_load(&originAdRequests)&&metrics[8]==1,@"Actual blank media payload, no origin ad download");
    ssn_adblock_end(lease);ssn_adblock_set_enabled(false);
    NSCAssert(!stateEnabled&&!ssn_adblock_enabled()&&!ssn_adblock_begin()&&![NSUserDefaults.standardUserDefaults boolForKey:@SSN_ADBLOCK_KEY],@"Saved Off preference");
    [NSUserDefaults.standardUserDefaults synchronize];
    NSTask *restart=[NSTask new];restart.executableURL=[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[0]]];restart.arguments=@[@"restored-off"];
    NSCAssert([restart launchAndReturnError:NULL],@"Launch preference restoration subprocess");[restart waitUntilExit];
    NSCAssert(restart.terminationStatus==0,@"Off restoration failed");
    uint64_t intercepted=metrics[0];
    NSCAssert([text(session,@"https://video.ttvnw.net/original.m3u8") containsString:@"original-ad.ts"]&&metrics[0]==intercepted,@"Disabled is original passthrough");
    ssn_adblock_set_enabled(true);lease=ssn_adblock_begin();text(session,source);pendingToken=YES;
    unsigned prior=atomic_load(&tokenCalls);FetchResult *cancelled=[FetchResult new];
    NSURLSessionDataTask *task=start(session,@"https://video.ttvnw.net/original.m3u8",cancelled);
    NSCAssert(waitUntil(^BOOL{return atomic_load(&tokenCalls)>prior;},5),@"Pending native token");
    [task cancel];ssn_adblock_end(lease);
    NSCAssert(waitUntil(^BOOL{return atomic_load(&tokenCancels)>0&&cancelled.done;},3),@"Cancellation releases pending promise");
    pendingToken=NO;lease=ssn_adblock_begin();text(session,source);pendingToken=YES;
    prior=atomic_load(&tokenCalls);unsigned cancels=atomic_load(&tokenCancels);FetchResult *account=[FetchResult new];
    start(session,@"https://video.ttvnw.net/original.m3u8",account);
    NSCAssert(waitUntil(^BOOL{return atomic_load(&tokenCalls)>prior;},5),@"Pending account-bound token");
    authorized=NO;identity=[NSObject new];ssn_adblock_end(lease);
    NSCAssert(waitUntil(^BOOL{return atomic_load(&tokenCancels)>cancels&&account.done;},3),@"Account change cancels native token and stale transport");
    NSCAssert(account.error&&atomic_load(&tokenCalls)==prior+1,@"No stale delivery or later alternate token after account change");
    [session invalidateAndCancel];[NSUserDefaults.standardUserDefaults removeObjectForKey:@SSN_ADBLOCK_KEY];
    puts("VAFT_NATIVE PASS: default/on/off; authenticated native token boundary; clean alternate/cache; exact stream ownership; all-candidate fallback; real blank payload; cancellation/account loss");
    return 0;
}}
