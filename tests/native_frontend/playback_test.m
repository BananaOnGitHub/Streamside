/* Synthetic IVS/GraphQL doubles exercise the production facade's lifetime on
 * real UIKit. This does NOT test the donor, entitlement or actual video/audio. */
#import <UIKit/UIKit.h>
#import "SSNPlayback.h"
#include "SSNPlaybackRequest.h"
#include <stdlib.h>
static BOOL authorized=YES,pending;
static unsigned requests,cancels,created,released,pauses,decodedEvents;
static BOOL sourceEncoding;
static id identity;
BOOL ssn_playback_authorized(void) { return authorized; }
bool ssn_navigation_guarded(void) { return true; }
void ssn_report(void) {}
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
@interface IVSPlayer : NSObject
@property(nonatomic) NSInteger state;
@property(nonatomic,readonly) id error;
- (void)load:(NSURL *)url;
- (void)play;
- (void)pause;
- (NSInteger)videoFramesDecoded;
- (CGSize)videoSize;
@end
@implementation IVSPlayer
- (instancetype)init { if((self=[super init])) created++;return self; }
- (id)error { return nil; }
- (void)load:(NSURL *)url {
    NSURLComponents *parts=[NSURLComponents componentsWithURL:url resolvingAgainstBaseURL:NO];
    NSMutableDictionary *items=[NSMutableDictionary dictionary];
    for(NSURLQueryItem *item in parts.queryItems) if(item.value) items[item.name]=item.value;
    sourceEncoding=[parts.scheme isEqual:@"https"]&&[parts.host isEqual:@"usher.ttvnw.net"]&&
        [parts.path isEqual:@"/api/channel/hls/synthetic_channel.m3u8"]&&
        [items[@"token"] isEqual:@"synthetic &?+#/ grant"]&&[items[@"sig"] isEqual:@"synthetic+signature"];
    self.state=1;
}
- (void)play { self.state=3; }
- (void)pause { pauses++;self.state=0; }
- (NSInteger)videoFramesDecoded { return self.state==3?1:0; }
- (CGSize)videoSize { return CGSizeMake(1920,1080); }
- (void)dealloc { released++;[super dealloc]; }
@end
@interface IVSPlayerView : UIView
@property(nonatomic,retain) id player;
@property(nonatomic,copy) NSString *videoGravity;
@end
@implementation IVSPlayerView
- (void)dealloc { [_player release];[_videoGravity release];[super dealloc]; }
@end
@interface PlaybackTestDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic,retain) UIWindow *window;
@end
@implementation PlaybackTestDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app;(void)options;identity=[NSObject new];
    self.window=[[[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds] autorelease];
    self.window.rootViewController=[[[UIViewController alloc] init] autorelease];[self.window makeKeyAndVisible];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,1000000000),dispatch_get_main_queue(),^{
        SSNPlayback *playback=[[SSNPlayback alloc] initWithChannel:@"synthetic_channel"];
        [playback start];
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW,1100000000),dispatch_get_main_queue(),^{
            BOOL initial=playback.phase==3&&sourceEncoding&&decodedEvents==1;
            [NSNotificationCenter.defaultCenter postNotificationName:UIApplicationWillResignActiveNotification object:nil];
            BOOL background=playback.phase==5&&created==released&&pauses>0;
            [NSNotificationCenter.defaultCenter postNotificationName:UIApplicationDidBecomeActiveNotification object:nil];
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,1100000000),dispatch_get_main_queue(),^{
                BOOL resumed=playback.phase==3&&requests==2;
                authorized=NO;
                [NSNotificationCenter.defaultCenter postNotificationName:@"SSNNativeServiceDidChange" object:nil];
                BOOL accountStop=playback.phase==7&&playback.errorCode==1&&created==released;
                [playback stop];authorized=YES;pending=YES;[playback start];
                unsigned before=cancels;[playback stop];
                BOOL cancellation=cancels==before+1&&playback.phase==0;
                BOOL teardown=created==released;
                BOOL passed=initial&&background&&resumed&&accountStop&&cancellation&&teardown;
                NSDictionary *receipt=@{@"passed":@(passed),@"background_resume":@(background&&resumed),@"account_stop":@(accountStop),@"cancellation":@(cancellation),@"teardown":@(teardown),@"source_encoding":@(sourceEncoding),@"playing_observed":@(initial)};
                NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
                [[NSJSONSerialization dataWithJSONObject:receipt options:0 error:NULL] writeToURL:[documents URLByAppendingPathComponent:@"playback-test.json"] atomically:YES];
                [playback release];exit(passed?0:1);
            });
        });
    });return YES;
}
@end
int main(int argc,char **argv) { @autoreleasepool { return UIApplicationMain(argc,argv,nil,NSStringFromClass(PlaybackTestDelegate.class)); } }
