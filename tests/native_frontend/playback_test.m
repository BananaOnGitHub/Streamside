/* Synthetic IVS/GraphQL doubles exercise the production facade's lifetime on
 * real UIKit. This does NOT test the donor, entitlement or actual video/audio. */
#import <UIKit/UIKit.h>
#import "SSNPlayback.h"
#import <AVFAudio/AVFAudio.h>
#include "SSNPlaybackRequest.h"
#include <stdlib.h>
#include <stdatomic.h>
#include <objc/runtime.h>
static BOOL authorized=YES,pending;
static unsigned leaseStarts,leaseEnds;static bool endedLeases[64],validLeases=true;
uint64_t ssn_adblock_begin(void) { return ++leaseStarts; }
void ssn_adblock_end(uint64_t lease) {
    if(!lease) return;
    if(lease>=64||endedLeases[lease]) { validLeases=false;return; }
    endedLeases[lease]=true;leaseEnds++;
}
bool ssn_native_mode(void) { return true; }
static unsigned requests,cancels,pauses,decodedEvents;
static atomic_uint created,released,activationCalls,reportMainCalls,audioRetirements;
static atomic_bool deallocationOffMain=true,retirementHeartbeat;
static BOOL firstPlayerAmbient=NO;
static BOOL sourceEncoding,lastMuted,mutedBeforeLoad,mixingBeforeLoad;
static unsigned muteCalls;
static id identity;
bool ssn_playback_authorized(void) { return authorized; }
bool ssn_navigation_guarded(void) { return true; }
static BOOL observedMuteKnown,observedMuteIntent,observedMuteActual;
void ssn_playback_mute(bool known,bool requested,bool reported) { observedMuteKnown=known;observedMuteIntent=requested;observedMuteActual=reported; }
void ssn_playback_work(unsigned stage,uint64_t us) { (void)us;if(stage==4) atomic_fetch_add(&audioRetirements,1); }
void ssn_report(void) { if(NSThread.isMainThread) atomic_fetch_add(&reportMainCalls,1); }
void ssn_playback_status(unsigned phase,unsigned error) { (void)phase;(void)error; }
void ssn_playback_event(unsigned event) { if(event==4) decodedEvents++; }

__attribute__((objc_runtime_name("_TtC6PMHTTP11HTTPManager")))
@interface TestHTTP : NSObject
+ (id)defaultManager;
- (id)defaultAuth;
@end
@implementation TestHTTP
+ (id)defaultManager { static id manager;if(!manager) manager=[self new];return manager; }
- (id)defaultAuth { return identity; }
@end
@interface TestPromise : NSObject
- (BOOL)getValue:(id *)value error:(id *)error;
- (void)requestCancel;
@end
@implementation TestPromise
- (BOOL)getValue:(id *)value error:(id *)error {
    *error=nil;if(pending) return NO;
    *value=@{@"value":@"synthetic &?+#/ grant",@"signature":@"synthetic+signature"};return YES;
}
- (void)requestCancel { cancels++; }
@end
id ssn_playback_request(id channel) { (void)channel;requests++;return [TestPromise new]; }
static BOOL reducedQualities=NO;
static unsigned qualitySwitches;
@interface IVSQuality : NSObject
@property(nonatomic,copy) NSString *name;
@end
@implementation IVSQuality
- (void)dealloc { [_name release];[super dealloc]; }
@end
@interface IVSPlayer : NSObject
@property(nonatomic) NSInteger state;
@property(nonatomic) BOOL muted;
@property(nonatomic,readonly) id error;
@property(nonatomic,readonly) NSArray *qualities;
@property(nonatomic,retain) IVSQuality *quality;
- (void)setQuality:(IVSQuality *)quality adaptive:(BOOL)adaptive;
- (void)load:(NSURL *)url;
- (void)play;
- (void)pause;
- (NSInteger)videoFramesDecoded;
- (CGSize)videoSize;
@end
@implementation IVSPlayer
@synthesize muted=_muted;
- (instancetype)init {
    NSAssert(NSThread.isMainThread,@"IVS init must remain on main");
    if((self=[super init])) {
        if(created==0) firstPlayerAmbient=[AVAudioSession.sharedInstance.category isEqual:AVAudioSessionCategoryAmbient];
        created++;
    }return self;
}
- (NSArray *)qualities {
    NSMutableArray *result=[NSMutableArray array];
    for(NSString *name in (reducedQualities?@[@"720p60"]:@[@"720p60",@"480p"])) {
        IVSQuality *q=[IVSQuality new];q.name=name;[result addObject:q];[q release];
    }return result;
}
- (void)setQuality:(IVSQuality *)quality adaptive:(BOOL)adaptive {
    NSAssert(NSThread.isMainThread&&adaptive,@"Manual quality must use the main-thread adaptive setter");
    self.quality=quality;qualitySwitches++;
}
- (id)error { return nil; }
- (void)setMuted:(BOOL)value { _muted=value;lastMuted=value;muteCalls++; }
- (void)load:(NSURL *)url {
    NSAssert(NSThread.isMainThread,@"IVS load must remain on main");
    mutedBeforeLoad=self.muted;
    mixingBeforeLoad=[AVAudioSession.sharedInstance.category isEqual:AVAudioSessionCategoryAmbient];
    NSURLComponents *parts=[NSURLComponents componentsWithURL:url resolvingAgainstBaseURL:NO];
    NSMutableDictionary *items=[NSMutableDictionary dictionary];
    for(NSURLQueryItem *item in parts.queryItems) if(item.value) items[item.name]=item.value;
    sourceEncoding=[parts.scheme isEqual:@"https"]&&[parts.host isEqual:@"usher.ttvnw.net"]&&
        [parts.path isEqual:@"/api/channel/hls/synthetic_channel.m3u8"]&&
        [items[@"token"] isEqual:@"synthetic &?+#/ grant"]&&[items[@"sig"] isEqual:@"synthetic+signature"];
    self.state=1;
}
- (void)play { NSAssert(NSThread.isMainThread,@"IVS play must remain on main");self.state=3; }
- (void)pause { NSAssert(NSThread.isMainThread,@"IVS pause must remain on main");pauses++;self.state=0; }
- (NSInteger)videoFramesDecoded { return self.state==3?1:0; }
- (CGSize)videoSize { return CGSizeMake(1920,1080); }
- (void)dealloc {
    [_quality release];
    if(NSThread.isMainThread) atomic_store(&deallocationOffMain,false);
    // Require a real main-queue turn while disposal is still in progress.
    dispatch_semaphore_t gate=dispatch_semaphore_create(0);dispatch_retain(gate);
    dispatch_async(dispatch_get_main_queue(),^{dispatch_semaphore_signal(gate);dispatch_release(gate);});
    long result=dispatch_semaphore_wait(gate,dispatch_time(DISPATCH_TIME_NOW,2000000000));
    dispatch_release(gate);atomic_store(&retirementHeartbeat,result==0);
    // A deliberately slow SDK destructor must not stall main-thread input.
    [NSThread sleepForTimeInterval:0.2];released++;[super dealloc];
}
@end
@interface IVSPlayerView : UIView
@property(nonatomic,retain) id player;
@property(nonatomic,copy) NSString *videoGravity;
@end
@implementation IVSPlayerView
- (void)dealloc { [_player release];[_videoGravity release];[super dealloc]; }
@end
static void waitPlaying(SSNPlayback *playback,unsigned expectedDecoded,NSTimeInterval deadline,void (^completion)(BOOL)) {
    if(playback.phase==3&&decodedEvents>=expectedDecoded) { completion(YES);return; }
    if(playback.phase==7||NSProcessInfo.processInfo.systemUptime>=deadline) { completion(NO);return; }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100000000),dispatch_get_main_queue(),^{
        waitPlaying(playback,expectedDecoded,deadline,completion);
    });
}
static void waitPaused(SSNPlayback *playback,NSTimeInterval deadline,void (^completion)(BOOL)) {
    if(playback.phase==8) { completion(YES);return; }
    if(playback.phase==7||NSProcessInfo.processInfo.systemUptime>=deadline) { completion(NO);return; }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100000000),dispatch_get_main_queue(),^{waitPaused(playback,deadline,completion);});
}
static IMP originalActivation;
static BOOL observeActivation(id object,SEL selector,BOOL active,NSError **error) {
    if(active) atomic_fetch_add(&activationCalls,1);
    return ((BOOL(*)(id,SEL,BOOL,NSError **))originalActivation)(object,selector,active,error);
}
static void waitUntil(BOOL (^condition)(void),NSTimeInterval deadline,void (^completion)(BOOL)) {
    if(condition()) { completion(YES);return; }
    if(NSProcessInfo.processInfo.systemUptime>=deadline) { completion(NO);return; }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,50000000),dispatch_get_main_queue(),^{waitUntil(condition,deadline,completion);});
}
@interface PlaybackTestDelegate : UIResponder <UIApplicationDelegate> {
    SSNPlayback *_playback;
    NSString *_originalCategory,*_originalMode;
    AVAudioSessionCategoryOptions _originalOptions;
    NSMutableDictionary *_results;
    BOOL _responsive;
    unsigned _expectedRetirements;
}
@property(nonatomic,retain) UIWindow *window;
@end
@implementation PlaybackTestDelegate
- (void)record:(NSString *)key passed:(BOOL)passed { _results[key]=@(passed); }
- (void)waitRetired:(void (^)(BOOL))completion {
    unsigned expected=++_expectedRetirements;
    waitUntil(^BOOL{
        AVAudioSession *audio=AVAudioSession.sharedInstance;
        return audioRetirements>=expected&&created==released&&[audio.category isEqual:self->_originalCategory]&&[audio.mode isEqual:self->_originalMode]&&audio.categoryOptions==self->_originalOptions;
    },NSProcessInfo.processInfo.systemUptime+5,completion);
}
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app;(void)options;identity=[NSObject new];_results=[NSMutableDictionary new];
    self.window=[[[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds] autorelease];
    self.window.rootViewController=[[[UIViewController alloc] init] autorelease];[self.window makeKeyAndVisible];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,1000000000),dispatch_get_main_queue(),^{
        AVAudioSession *audio=AVAudioSession.sharedInstance;
        [audio setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:NULL];
        // Start cold in a nonmixing category; the facade must install Ambient
        // before the very first synthetic player, not merely before load().
        [audio setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeMoviePlayback options:0 error:NULL];
        self->_originalCategory=[audio.category copy];self->_originalMode=[audio.mode copy];self->_originalOptions=audio.categoryOptions;
        Method method=class_getInstanceMethod(AVAudioSession.class,@selector(setActive:error:));
        originalActivation=method_getImplementation(method);method_setImplementation(method,(IMP)observeActivation);
        SSNPlayback *waiting=[[SSNPlayback alloc] initWithChannel:@"synthetic_channel" preview:YES];
        BOOL pendingPromotion=[waiting enterTheatre];waiting.muted=NO;
        [self record:@"pending_consent_promotion" passed:pendingPromotion&&!waiting.isMuted&&waiting.phase==0&&created==0&&requests==0&&activationCalls==0&&[audio.category isEqual:self->_originalCategory]];
        [waiting stop];[waiting release];
        self->_playback=[[SSNPlayback alloc] initWithChannel:@"synthetic_channel" preview:YES];
        self->_playback.muted=NO;[self->_playback start];
        waitPlaying(self->_playback,1,NSProcessInfo.processInfo.systemUptime+10,^(BOOL observed){[self initial:observed];});
    });return YES;
}
- (void)initial:(BOOL)observed {
    unsigned beforeQualityRequests=requests,beforeQualityPlayers=created;
    BOOL listed=[_playback.qualities isEqual:@[@"720p60",@"480p"]];
    _playback.preferredQuality=@"480p";
    BOOL selected=[_playback.effectiveQuality isEqual:@"480p"]&&qualitySwitches==1;
    reducedQualities=YES;[_playback performSelector:@selector(tick:) withObject:nil];
    BOOL fallback=[_playback.effectiveQuality isEqual:@"auto"]&&[_playback.preferredQuality isEqual:@"480p"];
    reducedQualities=NO;[_playback performSelector:@selector(tick:) withObject:nil];
    [self record:@"quality_selection" passed:listed&&selected&&fallback&&[_playback.effectiveQuality isEqual:@"480p"]&&requests==beforeQualityRequests&&created==beforeQualityPlayers&&_playback.isMuted];
    [self record:@"playing_observed" passed:observed&&_playback.phase==3&&decodedEvents==1];
    [self record:@"source_encoding" passed:sourceEncoding];
    [self record:@"preview_muted_before_load" passed:mutedBeforeLoad&&_playback.isMuted&&observedMuteActual];
    AVAudioSession *audio=AVAudioSession.sharedInstance;float volume=audio.outputVolume;
    NSString *category=audio.category;_playback.muted=YES;
    [self record:@"stream_only_mute" passed:observedMuteKnown&&observedMuteIntent&&observedMuteActual&&_playback.isMuted&&lastMuted&&muteCalls>=2&&volume==audio.outputVolume&&[category isEqual:audio.category]];
    [self record:@"preview_mixes_audio" passed:mixingBeforeLoad&&[audio.category isEqual:AVAudioSessionCategoryAmbient]&&_playback.isMuted];
    NSTimeInterval started=NSProcessInfo.processInfo.systemUptime;[_playback stop];
    _responsive=NSProcessInfo.processInfo.systemUptime-started<0.1;
    [self waitRetired:^(BOOL restored){
        [self record:@"preview_mixes_audio" passed:restored&&[self->_results[@"preview_mixes_audio"] boolValue]];
        [self record:@"async_retirement" passed:restored&&self->_responsive&&atomic_load(&retirementHeartbeat)&&atomic_load(&deallocationOffMain)&&atomic_load(&reportMainCalls)==0];
        [self->_playback start];
        waitPlaying(self->_playback,2,NSProcessInfo.processInfo.systemUptime+10,^(BOOL restarted){[self promote:restarted];});
    }];
}
- (void)promote:(BOOL)restarted {
    [self record:@"preview_cold_audio" passed:restarted&&firstPlayerAmbient&&activationCalls==0&&mixingBeforeLoad];
    unsigned beforeCreated=created,beforeRequests=requests;
    BOOL promoted=restarted&&[_playback enterTheatre]&&_playback.isMuted&&AVAudioSession.sharedInstance.categoryOptions==0&&activationCalls>0;
    _playback.muted=NO;
    [self record:@"theatre_audio_promotion" passed:promoted&&!_playback.isMuted&&!lastMuted&&created==beforeCreated&&requests==beforeRequests];
    _playback.muted=YES;_playback.paused=YES;[_playback performSelector:@selector(tick:) withObject:nil];
    BOOL paused=_playback.phase==8&&_playback.isPaused&&created==beforeCreated&&requests==beforeRequests;
    _playback.paused=NO;[_playback performSelector:@selector(tick:) withObject:nil];
    [self record:@"local_pause_resume" passed:paused&&_playback.phase==3&&!_playback.isPaused&&requests==beforeRequests];
    _playback.paused=YES;[NSNotificationCenter.defaultCenter postNotificationName:UIApplicationWillResignActiveNotification object:nil];
    BOOL background=_playback.phase==5&&pauses>0;
    [self waitRetired:^(BOOL retired){
        [self record:@"background_resume" passed:background&&retired];
        [NSNotificationCenter.defaultCenter postNotificationName:UIApplicationDidBecomeActiveNotification object:nil];
        waitPaused(self->_playback,NSProcessInfo.processInfo.systemUptime+10,^(BOOL pausedAgain){[self resume:pausedAgain];});
    }];
}
- (void)resume:(BOOL)pausedAgain {
    [self record:@"quality_restoration" passed:[_playback.preferredQuality isEqual:@"480p"]&&[_playback.effectiveQuality isEqual:@"480p"]];
    [self record:@"control_intent_retained" passed:pausedAgain&&_playback.isPaused&&_playback.isMuted&&lastMuted];
    _playback.paused=NO;
    waitPlaying(_playback,3,NSProcessInfo.processInfo.systemUptime+10,^(BOOL observed){
        [self record:@"background_resume" passed:observed&&self->_playback.phase==3&&requests==3&&[self->_results[@"background_resume"] boolValue]];
        self->_playback.paused=YES;authorized=NO;
        [NSNotificationCenter.defaultCenter postNotificationName:@"SSNNativeServiceDidChange" object:nil];
        BOOL rejected=self->_playback.phase==7&&self->_playback.errorCode==1;
        [self record:@"quality_teardown" passed:self->_playback.qualities.count==0&&[self->_playback.effectiveQuality isEqual:@"auto"]];
        [self waitRetired:^(BOOL retired){[self record:@"account_stop" passed:rejected&&retired];[self pendingCancellation];}];
    });
}
- (void)pendingCancellation {
    [_playback stop];authorized=YES;pending=YES;
    unsigned beforeRequests=requests;
    [_playback start];[_playback stop]; // Cancel before asynchronous audio admission.
    [self waitRetired:^(BOOL retired){
        [self record:@"audio_preparation_cancellation" passed:retired&&requests==beforeRequests&&self->_playback.phase==0];
        [self->_playback start];
        waitUntil(^BOOL{return requests>beforeRequests;},NSProcessInfo.processInfo.systemUptime+5,^(BOOL requested){
            unsigned before=cancels;[self->_playback stop];
            BOOL cancelled=requested&&cancels==before+1&&self->_playback.phase==0;
            [self waitRetired:^(BOOL restored){
                [self record:@"cancellation" passed:cancelled&&restored];
                [self record:@"teardown" passed:created==released&&atomic_load(&deallocationOffMain)];
                [self retirementOrdering];
            }];
        });
    }];
}
- (void)retirementOrdering {
    pending=NO;
    SSNPlayback *first=[[SSNPlayback alloc] initWithChannel:@"synthetic_channel" preview:YES];[first start];
    waitPlaying(first,4,NSProcessInfo.processInfo.systemUptime+10,^(BOOL firstPlaying){
        [first stop];[first release];self->_expectedRetirements++;
        [self->_playback release];self->_playback=[[SSNPlayback alloc] initWithChannel:@"synthetic_channel" preview:YES];
        [self->_playback start];
        waitPlaying(self->_playback,5,NSProcessInfo.processInfo.systemUptime+10,^(BOOL nextPlaying){
            waitUntil(^BOOL{return created==released+1;},NSProcessInfo.processInfo.systemUptime+5,^(BOOL oldDisposed){
                BOOL mixing=[AVAudioSession.sharedInstance.category isEqual:AVAudioSessionCategoryAmbient]&&
                    [AVAudioSession.sharedInstance.mode isEqual:AVAudioSessionModeDefault];
                [self record:@"audio_retirement_ordering" passed:firstPlaying&&nextPlaying&&oldDisposed&&mixing&&self->_playback.isMuted];
                [self->_playback stop];[self waitRetired:^(BOOL restored){
                    [self record:@"teardown" passed:restored&&created==released&&[self->_results[@"teardown"] boolValue]];
                    [self finish];
                }];
            });
        });
    });
}
- (void)finish {
    [self record:@"vaft_lifetime" passed:validLeases&&leaseStarts>=requests&&leaseStarts==leaseEnds];
    BOOL passed=YES;for(NSNumber *result in _results.allValues) passed=passed&&result.boolValue;
    _results[@"passed"]=@(passed);
    NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    [[NSJSONSerialization dataWithJSONObject:_results options:0 error:NULL] writeToURL:[documents URLByAppendingPathComponent:@"playback-test.json"] atomically:YES];
    [_playback release];[_originalCategory release];[_originalMode release];exit(passed?0:1);
}
@end
int main(int argc,char **argv) { @autoreleasepool { return UIApplicationMain(argc,argv,nil,NSStringFromClass(PlaybackTestDelegate.class)); } }
