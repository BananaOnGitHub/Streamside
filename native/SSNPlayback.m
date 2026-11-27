#import "SSNPlayback.h"
#import "SSNAdBlock.h"
#import <AVFAudio/AVFAudio.h>
#import <CoreMedia/CMTime.h>
#include "SSNPlaybackRequest.h"
#include "SSNIntegration.h"
#include "SSNCore.h"
#include <stdatomic.h>
#include <math.h>

static id auth(void) { return m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth"); }
static BOOL same(NSString *a,NSString *b) { return [a isEqualToString:b]; }
static void timedWork(unsigned stage,NSTimeInterval began) {
    NSTimeInterval elapsed=NSProcessInfo.processInfo.systemUptime-began;
    ssn_playback_work(stage,(uint64_t)(fmin(60,fmax(0,elapsed))*1000000));
}
static BOOL playerABI(void) {
    Class p=NSClassFromString(@"IVSPlayer"),v=NSClassFromString(@"IVSPlayerView");
    return p&&[v isSubclassOfClass:UIView.class]&&
        method_is(p,"init","@16@0:8",false)&&method_is(p,"load:","v24@0:8@16",false)&&
        method_is(p,"play","v16@0:8",false)&&method_is(p,"pause","v16@0:8",false)&&
        method_is(p,"setMuted:","v20@0:8B16",false)&&method_is(p,"muted","B16@0:8",false)&&
        method_is(p,"state","q16@0:8",false)&&method_is(p,"error","@16@0:8",false)&&
        method_is(p,"videoFramesDecoded","q16@0:8",false)&&
        method_is(p,"videoSize","{CGSize=dd}16@0:8",false)&&
        method_is(v,"setPlayer:","v24@0:8@16",false)&&method_is(v,"setVideoGravity:","v24@0:8@16",false);
}
static BOOL qualityABI(void) {
    Class p=NSClassFromString(@"IVSPlayer"),q=NSClassFromString(@"IVSQuality");
    return q&&method_is(p,"qualities","@16@0:8",false)&&
        method_is(p,"setQuality:","v24@0:8@16",false)&&
        method_is(p,"setQuality:adaptive:","v28@0:8@16B24",false)&&
        method_is(q,"name","@16@0:8",false)&&method_is(q,"width","q16@0:8",false)&&method_is(q,"height","q16@0:8",false);
}
static BOOL latencyABI(void) {
    Class p=NSClassFromString(@"IVSPlayer");
    return method_is(p,"setLiveLowLatencyEnabled:","v20@0:8B16",false)&&
        method_is(p,"setRebufferToLive:","v20@0:8B16",false)&&
        method_is(p,"isLiveLowLatency","B16@0:8",false)&&
        method_is(p,"liveLatency","{?=qiIq}16@0:8",false)&&
        method_is(p,"buffered","{?=qiIq}16@0:8",false);
}
static int64_t durationMillis(CMTime time) {
    if(!CMTIME_IS_NUMERIC(time)||time.timescale<=0||time.value<0) return -1;
    double ms=(double)time.value*1000.0/time.timescale;
    return ms<=120000?(int64_t)llround(ms):-1;
}
// SDK calls and UIKit detachment stay on main. Final SDK disposal is isolated
// from audio mutations; SDK >=1.45 explicitly permits off-main deallocation.
static dispatch_queue_t retirementQueue(void) {
    static dispatch_queue_t queue;static dispatch_once_t once;
    dispatch_once(&once,^{queue=dispatch_queue_create("dev.streamside.playback-lifetime",DISPATCH_QUEUE_SERIAL);});
    return queue;
}
static dispatch_queue_t audioQueue(void) {
    static dispatch_queue_t queue;static dispatch_once_t once;
    dispatch_once(&once,^{queue=dispatch_queue_create("dev.streamside.playback-audio",DISPATCH_QUEUE_SERIAL);});
    return queue;
}
static void reportPlayback(void) {
    static atomic_bool pending;
    static atomic_uint revision;
    atomic_fetch_add(&revision,1);
    bool expected=false;
    if(!atomic_compare_exchange_strong(&pending,&expected,true)) return;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY,0),^{
        unsigned writing=atomic_load(&revision);ssn_report();atomic_store(&pending,false);
        if(atomic_load(&revision)!=writing) reportPlayback();
    });
}
@interface SSNPlaybackAudio : NSObject {
    NSString *_previousCategory,*_previousMode,*_installedCategory,*_installedMode;
    AVAudioSessionCategoryOptions _previousOptions,_installedOptions;
    BOOL _configured;
    atomic_bool _cancelled;
}
- (BOOL)configurePreview:(BOOL)preview;
- (BOOL)installPreview:(BOOL)preview;
- (void)cancel;
- (void)restore;
@end
@implementation SSNPlaybackAudio
- (instancetype)init { if((self=[super init])) atomic_init(&_cancelled,false);return self; }
- (void)cancel { atomic_store(&_cancelled,true); }
- (BOOL)configurePreview:(BOOL)preview {
    @autoreleasepool {
        NSTimeInterval began=NSProcessInfo.processInfo.systemUptime;
        BOOL result=[self installPreview:preview];timedWork(3,began);return result;
    }
}
- (BOOL)installPreview:(BOOL)preview {
    if(atomic_load(&_cancelled)) return NO;
    AVAudioSession *audio=AVAudioSession.sharedInstance;
    if(!_configured) {
        _previousCategory=[audio.category copy];_previousMode=[audio.mode copy];_previousOptions=audio.categoryOptions;
    }
    // Ambient inherently mixes. A silent preview never explicitly activates
    // audio, including the first cold SDK initialization. Watch opts in later.
    NSString *category=preview?AVAudioSessionCategoryAmbient:AVAudioSessionCategoryPlayback;
    NSString *mode=preview?AVAudioSessionModeDefault:AVAudioSessionModeMoviePlayback;
    if(![audio setCategory:category mode:mode options:0 error:NULL]) return NO;
    _configured=YES;
    [_installedCategory release];_installedCategory=[audio.category copy];
    [_installedMode release];_installedMode=[audio.mode copy];_installedOptions=audio.categoryOptions;
    if(atomic_load(&_cancelled)) return NO;
    return preview||[audio setActive:YES error:NULL];
}
- (void)restore {
    NSTimeInterval began=NSProcessInfo.processInfo.systemUptime;
    if(!_configured) { timedWork(4,began);return; }
    AVAudioSession *audio=AVAudioSession.sharedInstance;
    if(same(audio.category,_installedCategory)&&same(audio.mode,_installedMode)&&audio.categoryOptions==_installedOptions) {
        [audio setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:NULL];
        [audio setCategory:_previousCategory mode:_previousMode options:_previousOptions error:NULL];
    }
    _configured=NO;timedWork(4,began);
}
- (void)dealloc {
    [_previousCategory release];[_previousMode release];[_installedCategory release];[_installedMode release];[super dealloc];
}
@end

@interface SSNPlayback ()
- (void)setPhase:(NSInteger)phase error:(NSInteger)code;
- (void)syncQualities;
@end

@implementation SSNPlayback {
    UIView *_view,*_playerView;
    NSString *_channel,*_preferredQuality,*_appliedQuality;
    NSArray *_qualities;
    BOOL _qualitySupported,_qualityReady,_latencySupported,_lowLatency;
    NSTimeInterval _nextLatencySample;
    SSNPlaybackAudio *_audio;
    NSUInteger _generation;
    uint64_t _adblockLease;
    id _player,_promise,_requestAuth;
    NSTimer *_timer;
    NSInteger _phase,_errorCode;
    NSTimeInterval _deadline;
    BOOL _opened,_foreground,_preparingAudio,_wasPlaying,_decoded,_paused,_muted,_preview;
}
@synthesize view=_view,phase=_phase,errorCode=_errorCode;
- (NSArray<NSString *> *)qualities { return _qualities?:@[]; }
- (NSString *)preferredQuality { return _preferredQuality?:@"auto"; }
- (NSString *)effectiveQuality { return _appliedQuality?:@"auto"; }
- (void)setPreferredQuality:(NSString *)name {
    NSAssert(NSThread.isMainThread,@"Quality belongs to the main thread");
    if(![name isKindOfClass:NSString.class]||!name.length||name.length>128) return;
    if([name isEqual:self.preferredQuality]) return;
    [_preferredQuality release];_preferredQuality=[name copy];
    [self syncQualities];
}
- (void)syncQualities {
    if(!_qualitySupported||!_qualityReady||!_player||!_opened||!_foreground||!ssn_playback_authorized()||auth()!=_requestAuth) return;
    id source=m0(_player,"qualities");
    if(![source isKindOfClass:NSArray.class]||[source count]>64) return;
    NSMutableDictionary *objects=[NSMutableDictionary dictionary];NSMutableArray *names=[NSMutableArray array];
    for(id quality in source) {
        if(![quality isKindOfClass:NSClassFromString(@"IVSQuality")]) continue;
        if(((NSInteger(*)(id,SEL))objc_msgSend)(quality,ss("width"))<=0 ||
           ((NSInteger(*)(id,SEL))objc_msgSend)(quality,ss("height"))<=0) continue;
        id name=m0(quality,"name");
        if(![name isKindOfClass:NSString.class]||![name length]||[name length]>128||[name isEqual:@"auto"]||objects[name]) continue;
        objects[name]=quality;[names addObject:name];
    }
    if(![_qualities isEqual:names]) { [_qualities release];_qualities=[names copy]; }
    NSString *chosen=objects[self.preferredQuality]?self.preferredQuality:@"auto";
    if([chosen isEqual:_appliedQuality]) return;
    if([chosen isEqual:@"auto"]) v1(_player,"setQuality:",nil);
    else ((void(*)(id,SEL,id,BOOL))objc_msgSend)(_player,ss("setQuality:adaptive:"),objects[chosen],YES);
    [_appliedQuality release];_appliedQuality=[chosen copy];
}
- (BOOL)isPaused { return _paused; }
- (BOOL)isMuted { return _muted; }
- (void)observeMute {
    BOOL actual=_player?((BOOL(*)(id,SEL))objc_msgSend)(_player,ss("muted")):NO;
    ssn_playback_mute(_player!=nil,_muted,actual);
}
- (void)setMuted:(BOOL)muted {
    NSAssert(NSThread.isMainThread,@"Playback controls belong to the main thread");
    _muted=_preview?YES:muted;
    if(_player) ((void(*)(id,SEL,BOOL))objc_msgSend)(_player,ss("setMuted:"),_muted);
    [self observeMute];reportPlayback();
}
- (void)setPaused:(BOOL)paused {
    NSAssert(NSThread.isMainThread,@"Playback controls belong to the main thread");
    if(_paused==paused) return;_paused=paused;
    if(!_opened||!_foreground||!_player) return;
    if(paused) { v0(_player,"pause");[self setPhase:8 error:0]; }
    else { _deadline=NSProcessInfo.processInfo.systemUptime+30;v0(_player,"play");[self setPhase:2 error:0]; }
}
- (instancetype)initWithChannel:(NSString *)channel { return [self initWithChannel:channel preview:NO]; }
- (instancetype)initWithChannel:(NSString *)channel preview:(BOOL)preview {
    if((self=[super init])) {
        _preview=preview;_muted=preview;
        _channel=[channel copy];_view=[UIView new];_view.backgroundColor=UIColor.blackColor;
        NSNotificationCenter *n=NSNotificationCenter.defaultCenter;
        [n addObserver:self selector:@selector(background:) name:UIApplicationWillResignActiveNotification object:nil];
        [n addObserver:self selector:@selector(foreground:) name:UIApplicationDidBecomeActiveNotification object:nil];
        [n addObserver:self selector:@selector(accountChanged:) name:@"SSNNativeServiceDidChange" object:nil];
    }return self;
}
- (void)setPhase:(NSInteger)phase error:(NSInteger)code {
    _phase=phase;_errorCode=code;ssn_playback_status((unsigned)phase,(unsigned)code);reportPlayback();
}
- (void)releaseMedia {
    _generation++;_preparingAudio=NO;_qualityReady=NO;_qualitySupported=NO;_latencySupported=NO;_nextLatencySample=0;
    [_qualities release];_qualities=nil;
    [_appliedQuality release];_appliedQuality=nil;
    ssn_adblock_end(_adblockLease);_adblockLease=0;
    if(_promise) { v0(_promise,"requestCancel");[_promise release];_promise=nil; }
    // Transfer the existing +1 to the serial queue as an unretained C pointer;
    // block copying must not add a final main-thread Objective-C release.
    void *retired=(void *)_player;_player=nil;
    if(retired) {
        NSTimeInterval began=NSProcessInfo.processInfo.systemUptime;v0((id)retired,"pause");timedWork(0,began);
    }
    if(_playerView) {
        NSTimeInterval began=NSProcessInfo.processInfo.systemUptime;
        v1(_playerView,"setPlayer:",nil);[_playerView removeFromSuperview];[_playerView release];_playerView=nil;
        timedWork(1,began);
    }
    SSNPlaybackAudio *audio=_audio;_audio=nil;[audio cancel];
    if(retired) dispatch_async(retirementQueue(),^{
        @autoreleasepool {
            NSTimeInterval began=NSProcessInfo.processInfo.systemUptime;
            [(id)retired release];timedWork(2,began);ssn_playback_event(5);reportPlayback();
        }
    });
    // Pause/detach already stopped the audible source. FIFO restoration is
    // enqueued now, ahead of the next facade's audio setup; it never races a
    // later owner or waits for a destructor that might need a main-queue turn.
    if(audio) dispatch_async(audioQueue(),^{@autoreleasepool { [audio restore];reportPlayback(); }});
    [audio release];
    [self observeMute];[_requestAuth release];_requestAuth=nil;
}
- (void)fail:(NSInteger)code {
    [self releaseMedia];ssn_playback_event(6);[self setPhase:7 error:code];
    [_timer invalidate];[_timer release];_timer=nil;
}
- (void)start {
    NSAssert(NSThread.isMainThread,@"Playback belongs to the main thread");
    [self stop];_paused=NO;_opened=YES;_foreground=UIApplication.sharedApplication.applicationState==UIApplicationStateActive;
    ssn_playback_event(0);
    if(!_foreground) { [self setPhase:5 error:0];return; }
    [self requestSource];
}
- (void)requestSource {
    [self releaseMedia];_wasPlaying=NO;_decoded=NO;
    if(!ssn_native_mode()||!ssn_playback_authorized()||!ssn_navigation_guarded()) { [self fail:1];return; }
    NSCharacterSet *allowed=[NSCharacterSet characterSetWithCharactersInString:@"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"];
    if(!_channel.length||_channel.length>128||[_channel rangeOfCharacterFromSet:allowed.invertedSet].location!=NSNotFound) { [self fail:3];return; }
    _requestAuth=[auth() retain];
    _adblockLease=ssn_adblock_begin();
    [self setPhase:1 error:0];_preparingAudio=YES;
    _deadline=NSProcessInfo.processInfo.systemUptime+30;
    if(!_timer) _timer=[[NSTimer scheduledTimerWithTimeInterval:0.25 target:self selector:@selector(tick:) userInfo:nil repeats:YES] retain];
    SSNPlaybackAudio *audio=[SSNPlaybackAudio new];_audio=audio;
    NSUInteger generation=_generation;BOOL preview=_preview;
    dispatch_async(audioQueue(),^{
        BOOL configured=[audio configurePreview:preview];
        dispatch_async(dispatch_get_main_queue(),^{
            if(generation!=self->_generation||!self->_opened) return;
            self->_preparingAudio=NO;
            if(!configured) { [self fail:5];return; }
            if(!ssn_playback_authorized()||auth()!=self->_requestAuth) { [self fail:1];return; }
            // Audio policy precedes even the first cold Objective-C SDK access.
            if(!playerABI()) { [self fail:2];return; }
            self->_promise=ssn_playback_request(self->_channel);
            if(!self->_promise) { [self fail:3];return; }
            ssn_playback_event(1);
        });
    });
}
- (BOOL)configureTheatreAudio {
    // Promotion is an explicit Watch action. Serialize it with any in-flight
    // audio preparation/restoration; preview loading and dismissal never wait here.
    SSNPlaybackAudio *audio=_audio;if(!audio) return YES;
    __block BOOL configured=NO;
    dispatch_sync(audioQueue(),^{configured=[audio configurePreview:NO];});
    return configured;
}
- (BOOL)enterTheatre {
    NSAssert(NSThread.isMainThread,@"Playback promotion belongs to the main thread");
    if(!ssn_playback_authorized()||!ssn_navigation_guarded()||(_requestAuth&&auth()!=_requestAuth)) return NO;
    if(!_opened) {
        if(UIApplication.sharedApplication.applicationState!=UIApplicationStateActive||_player||_audio||_promise) return NO;
        _preview=NO;return YES; // Consent still owns admission; no media/audio work.
    }
    if(!_foreground) return NO;
    if(!_preview) return YES;
    _preview=NO;
    // Upgrade the same queued audio lease in place, even while authorization
    // is pending, without creating another playback request or IVS player.
    if(![self configureTheatreAudio]) { [self fail:5];return NO; }
    return YES;
}
- (void)loadValue:(NSDictionary *)value {
    NSString *token=[value objectForKey:@"value"],*signature=[value objectForKey:@"signature"];
    if(![token isKindOfClass:NSString.class]||![signature isKindOfClass:NSString.class]) { [self fail:4];return; }
    // Only the native GraphQL result supplies these short-lived media grants.
    // NSURLComponents percent-encodes them; no OAuth/defaultAuth header is read
    // or forwarded. IVS owns manifest/segment access and enforces signed policy.
    NSURLComponents *url=[NSURLComponents new];url.scheme=@"https";url.host=@"usher.ttvnw.net";
    url.path=[NSString stringWithFormat:@"/api/channel/hls/%@.m3u8",_channel];
    url.queryItems=@[[NSURLQueryItem queryItemWithName:@"sig" value:signature],
                     [NSURLQueryItem queryItemWithName:@"token" value:token],
                     [NSURLQueryItem queryItemWithName:@"allow_source" value:@"true"],
                     [NSURLQueryItem queryItemWithName:@"allow_audio_only" value:@"false"],
                     // Match the inspected original player's media-delivery
                     // capabilities, irrespective of the local IVS latency toggle.
                     [NSURLQueryItem queryItemWithName:@"fast_bread" value:@"true"],
                     [NSURLQueryItem queryItemWithName:@"player_backend" value:@"mediaplayer"]];
    NSURL *source=url.URL;[url release];
    if(!source) { [self fail:4];return; }
    _qualitySupported=qualityABI();
    _player=[[NSClassFromString(@"IVSPlayer") alloc] init];
    _playerView=[[NSClassFromString(@"IVSPlayerView") alloc] initWithFrame:_view.bounds];
    if(!_player||!_playerView) { [self fail:2];return; }
    _playerView.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    [_view addSubview:_playerView];v1(_playerView,"setVideoGravity:",@"AVLayerVideoGravityResizeAspect");v1(_playerView,"setPlayer:",_player);
    ((void(*)(id,SEL,BOOL))objc_msgSend)(_player,ss("setMuted:"),_muted);
    // The SDK defaults to low latency on compatible streams. Make the chosen
    // mode explicit and recover toward live after rebuffer, rather than keep
    // accumulating delay. Keep the SDK's initial buffer and ABR defaults.
    NSUserDefaults *defaults=NSUserDefaults.standardUserDefaults;
    NSString *latencyKey=@"dev.streamside.player.lowLatency";
    _lowLatency=[defaults objectForKey:latencyKey]==nil||[defaults boolForKey:latencyKey];
    _latencySupported=latencyABI();
    if(_latencySupported) {
        ((void(*)(id,SEL,BOOL))objc_msgSend)(_player,ss("setLiveLowLatencyEnabled:"),_lowLatency);
        ((void(*)(id,SEL,BOOL))objc_msgSend)(_player,ss("setRebufferToLive:"),_lowLatency);
    }
    ssn_playback_latency_config(_latencySupported?(_lowLatency?1:0):2);
    ssn_playback_event(2);[self setPhase:2 error:0];
    _deadline=NSProcessInfo.processInfo.systemUptime+30;
    v1(_player,"load:",source);
}
- (void)tick:(NSTimer *)timer {
    (void)timer;
    if(!_opened||!_foreground) return;
    if(!ssn_playback_authorized()||auth()!=_requestAuth) { [self fail:1];return; }
    if(_preparingAudio) {
        if(NSProcessInfo.processInfo.systemUptime>=_deadline) [self fail:6];
        return;
    }
    if(_promise) {
        id value=nil,error=nil;
        BOOL done=((BOOL(*)(id,SEL,id*,id*))objc_msgSend)(_promise,ss("getValue:error:"),&value,&error);
        if(done) {
            [value retain];[_promise release];_promise=nil;
            if(error||![value isKindOfClass:NSDictionary.class]) [self fail:4];else [self loadValue:value];
            [value release];
        } else if(NSProcessInfo.processInfo.systemUptime>=_deadline) [self fail:6];
        return;
    }
    if(!_player) return;
    [self observeMute];
    if(m0(_player,"error")) { [self fail:7];return; }
    NSInteger state=((NSInteger(*)(id,SEL))objc_msgSend)(_player,ss("state"));
    // IVSPlayerState: idle 0, ready 1, buffering 2, playing 3, ended 4.
    if(state==4) { [self releaseMedia];[self setPhase:6 error:0];return; }
    if(state<0||state>4) { [self fail:2];return; }
    if(state>=1&&state<=3) { _qualityReady=YES;[self syncQualities]; }
    // A user pause is not a stalled load. Authorization continues to be checked
    // above, but there is no playback deadline or automatic READY-state play.
    if(_paused) { if(_phase!=8) [self setPhase:8 error:0];return; }
    if(state==1) v0(_player,"play");
    if(state==3) {
        if(!_wasPlaying) { _wasPlaying=YES;ssn_playback_event(3);[self setPhase:3 error:0]; }
        else if(_phase!=3) [self setPhase:3 error:0];
        _deadline=NSProcessInfo.processInfo.systemUptime+30;
        if(!_decoded&&((NSInteger(*)(id,SEL))objc_msgSend)(_player,ss("videoFramesDecoded"))>0) {
            _decoded=YES;ssn_playback_event(4);reportPlayback();
        }
        // Sample actual SDK server-to-player delay and remaining buffer only
        // while decoded theatre video is playing (not preloads or pauses).
        NSTimeInterval now=NSProcessInfo.processInfo.systemUptime;
        if(_latencySupported&&_decoded&&!_preview&&now>=_nextLatencySample) {
            _nextLatencySample=now+2;
            BOOL effective=((BOOL(*)(id,SEL))objc_msgSend)(_player,ss("isLiveLowLatency"));
            CMTime latency=((CMTime(*)(id,SEL))objc_msgSend)(_player,ss("liveLatency"));
            CMTime buffer=((CMTime(*)(id,SEL))objc_msgSend)(_player,ss("buffered"));
            ssn_playback_latency_sample(_lowLatency,effective,durationMillis(latency),durationMillis(buffer));
        }
    } else if(state==4) { [self releaseMedia];[self setPhase:6 error:0]; }
    else if(NSProcessInfo.processInfo.systemUptime>=_deadline) [self fail:6];
    else if(state==2&&_phase!=4) {
        if(_latencySupported&&_wasPlaying&&!_preview) ssn_playback_latency_rebuffer(_lowLatency);
        [self setPhase:4 error:0];
    }
    else if(state<0||state>4) [self fail:2];
}
- (void)background:(NSNotification *)note {
    (void)note;if(!_opened||!_foreground) return;
    _foreground=NO;[self releaseMedia];ssn_playback_event(7);[self setPhase:5 error:0];
}
- (void)foreground:(NSNotification *)note {
    (void)note;if(!_opened||_foreground) return;
    _foreground=YES;[self requestSource];
}
- (void)accountChanged:(NSNotification *)note {
    (void)note;
    if(_opened&&(!ssn_playback_authorized()||(_requestAuth&&auth()!=_requestAuth))) [self fail:1];
}
- (void)stop {
    NSAssert(NSThread.isMainThread,@"Playback belongs to the main thread");
    [_timer invalidate];[_timer release];_timer=nil;
    [self releaseMedia];
    if(_opened) { _opened=NO;ssn_playback_event(8);[self setPhase:0 error:0]; }
}
- (void)dealloc {
    [NSNotificationCenter.defaultCenter removeObserver:self];[self stop];[_preferredQuality release];[_channel release];[_view release];[super dealloc];
}
@end
