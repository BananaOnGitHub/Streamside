#import "SSNPlayback.h"
#import <AVFAudio/AVFAudio.h>
#include "SSNPlaybackRequest.h"
#include "SSNIntegration.h"
#include "SSNCore.h"

static id auth(void) { return m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth"); }
static BOOL same(NSString *a,NSString *b) { return [a isEqualToString:b]; }
static BOOL playerABI(void) {
    Class p=NSClassFromString(@"IVSPlayer"),v=NSClassFromString(@"IVSPlayerView");
    return p&&[v isSubclassOfClass:UIView.class]&&
        method_is(p,"init","@16@0:8",false)&&method_is(p,"load:","v24@0:8@16",false)&&
        method_is(p,"play","v16@0:8",false)&&method_is(p,"pause","v16@0:8",false)&&
        method_is(p,"state","q16@0:8",false)&&method_is(p,"error","@16@0:8",false)&&
        method_is(p,"videoFramesDecoded","q16@0:8",false)&&
        method_is(p,"videoSize","{CGSize=dd}16@0:8",false)&&
        method_is(v,"setPlayer:","v24@0:8@16",false)&&method_is(v,"setVideoGravity:","v24@0:8@16",false);
}
@implementation SSNPlayback {
    UIView *_view,*_playerView;
    NSString *_channel,*_previousCategory,*_previousMode;
    AVAudioSessionCategoryOptions _previousOptions;
    id _player,_promise,_requestAuth;
    NSTimer *_timer;
    NSInteger _phase,_errorCode;
    NSTimeInterval _deadline;
    BOOL _opened,_foreground,_audioActive,_wasPlaying,_decoded;
}
@synthesize view=_view,phase=_phase,errorCode=_errorCode;
- (instancetype)initWithChannel:(NSString *)channel {
    if((self=[super init])) {
        _channel=[channel copy];_view=[UIView new];_view.backgroundColor=UIColor.blackColor;
        NSNotificationCenter *n=NSNotificationCenter.defaultCenter;
        [n addObserver:self selector:@selector(background:) name:UIApplicationWillResignActiveNotification object:nil];
        [n addObserver:self selector:@selector(foreground:) name:UIApplicationDidBecomeActiveNotification object:nil];
        [n addObserver:self selector:@selector(accountChanged:) name:@"SSNNativeServiceDidChange" object:nil];
    }return self;
}
- (void)setPhase:(NSInteger)phase error:(NSInteger)code {
    _phase=phase;_errorCode=code;ssn_playback_status((unsigned)phase,(unsigned)code);ssn_report();
}
- (void)releaseMedia {
    if(_promise) { v0(_promise,"requestCancel");[_promise release];_promise=nil; }
    if(_player) { v0(_player,"pause");v1(_playerView,"setPlayer:",nil);[_player release];_player=nil;ssn_playback_event(5); }
    [_playerView removeFromSuperview];[_playerView release];_playerView=nil;
    [_requestAuth release];_requestAuth=nil;
    if(_audioActive) {
        AVAudioSession *audio=AVAudioSession.sharedInstance;
        // Restore only the configuration we installed; never overwrite a later
        // donor/account/audio-route owner that has changed the shared session.
        if(same(audio.category,AVAudioSessionCategoryPlayback)&&same(audio.mode,AVAudioSessionModeMoviePlayback)&&audio.categoryOptions==0) {
            [audio setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:NULL];
            [audio setCategory:_previousCategory mode:_previousMode options:_previousOptions error:NULL];
        }
        _audioActive=NO;
    }
    [_previousCategory release];_previousCategory=nil;[_previousMode release];_previousMode=nil;
}
- (void)fail:(NSInteger)code {
    [self releaseMedia];ssn_playback_event(6);[self setPhase:7 error:code];
    [_timer invalidate];[_timer release];_timer=nil;
}
- (void)start {
    NSAssert(NSThread.isMainThread,@"Playback belongs to the main thread");
    [self stop];_opened=YES;_foreground=UIApplication.sharedApplication.applicationState==UIApplicationStateActive;
    ssn_playback_event(0);
    if(!_foreground) { [self setPhase:5 error:0];return; }
    [self requestSource];
}
- (void)requestSource {
    [self releaseMedia];_wasPlaying=NO;_decoded=NO;
    if(!ssn_native_mode()||!ssn_playback_authorized()||!ssn_navigation_guarded()) { [self fail:1];return; }
    if(!playerABI()) { [self fail:2];return; }
    NSCharacterSet *allowed=[NSCharacterSet characterSetWithCharactersInString:@"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"];
    if(!_channel.length||_channel.length>128||[_channel rangeOfCharacterFromSet:allowed.invertedSet].location!=NSNotFound) { [self fail:3];return; }
    _requestAuth=[auth() retain];
    _promise=ssn_playback_request(_channel);
    if(!_promise) { [self fail:3];return; }
    ssn_playback_event(1);[self setPhase:1 error:0];
    _deadline=NSProcessInfo.processInfo.systemUptime+30;
    if(!_timer) _timer=[[NSTimer scheduledTimerWithTimeInterval:0.25 target:self selector:@selector(tick:) userInfo:nil repeats:YES] retain];
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
                     [NSURLQueryItem queryItemWithName:@"allow_audio_only" value:@"true"]];
    NSURL *source=url.URL;[url release];
    if(!source) { [self fail:4];return; }
    AVAudioSession *audio=AVAudioSession.sharedInstance;
    _previousCategory=[audio.category copy];_previousMode=[audio.mode copy];_previousOptions=audio.categoryOptions;
    if(![audio setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeMoviePlayback options:0 error:NULL]) { [self fail:5];return; }
    _audioActive=YES;
    if(![audio setActive:YES error:NULL]) { [self fail:5];return; }
    _player=[[NSClassFromString(@"IVSPlayer") alloc] init];
    _playerView=[[NSClassFromString(@"IVSPlayerView") alloc] initWithFrame:_view.bounds];
    if(!_player||!_playerView) { [self fail:2];return; }
    _playerView.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    [_view addSubview:_playerView];v1(_playerView,"setVideoGravity:",@"AVLayerVideoGravityResizeAspect");v1(_playerView,"setPlayer:",_player);
    ssn_playback_event(2);[self setPhase:2 error:0];
    _deadline=NSProcessInfo.processInfo.systemUptime+30;
    v1(_player,"load:",source);
}
- (void)tick:(NSTimer *)timer {
    (void)timer;
    if(!_opened||!_foreground) return;
    if(!ssn_playback_authorized()||auth()!=_requestAuth) { [self fail:1];return; }
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
    if(m0(_player,"error")) { [self fail:7];return; }
    NSInteger state=((NSInteger(*)(id,SEL))objc_msgSend)(_player,ss("state"));
    // IVSPlayerState: idle 0, ready 1, buffering 2, playing 3, ended 4.
    if(state==1) v0(_player,"play");
    if(state==3) {
        if(!_wasPlaying) { _wasPlaying=YES;ssn_playback_event(3);[self setPhase:3 error:0]; }
        else if(_phase!=3) [self setPhase:3 error:0];
        _deadline=NSProcessInfo.processInfo.systemUptime+30;
        if(!_decoded&&((NSInteger(*)(id,SEL))objc_msgSend)(_player,ss("videoFramesDecoded"))>0) {
            _decoded=YES;ssn_playback_event(4);ssn_report();
        }
    } else if(state==4) { [self releaseMedia];[self setPhase:6 error:0]; }
    else if(NSProcessInfo.processInfo.systemUptime>=_deadline) [self fail:6];
    else if(state==2&&_phase!=4) [self setPhase:4 error:0];
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
    [NSNotificationCenter.defaultCenter removeObserver:self];[self stop];[_channel release];[_view release];[super dealloc];
}
@end
