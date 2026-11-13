#import "SSNNativeBridge.h"
#import <UIKit/UIKit.h>
#include "SSNIntegration.h"
#include "SSNCore.h"
#import "SSNSwiftUI-Swift.h"

NSNotificationName const SSNNativeServiceDidChange = @"SSNNativeServiceDidChange";
void SSNPlayerControlEvent(unsigned event) { ssn_player_control_event(event); ssn_report(); }
void SSNNavigationEvent(unsigned event) { ssn_navigation_event(event); ssn_report(); }
BOOL SSNNavigationPermitted(void) { return ssn_native_mode() && ssn_navigation_guarded() && ssn_armed() && !ssn_failed(); }
static NSInteger signout_state;
static unsigned signout_ticks;
void SSNSwiftUIReady(void) { ssn_presentation((unsigned)[SSNSwiftUIHost rootOwner]); ssn_scaffold_ready(); ssn_report(); }

void ssn_ui_changed(void) {
    if(![NSThread isMainThread]) {
        dispatch_async(dispatch_get_main_queue(), ^{ ssn_ui_changed(); });
        return;
    }
    [SSNSwiftUIHost accountStateChanged];
    [[NSNotificationCenter defaultCenter] postNotificationName:SSNNativeServiceDidChange object:nil];
}
void ssn_ui_attach(id app_window) {
    [SSNSwiftUIHost attachToWindow:app_window];
}

static void check_signout(void) {
    if(!m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth")) {
        signout_state=0;
        ssn_account_refresh();
        return;
    }
    if(++signout_ticks>=120) {
        signout_state=2;
        ssn_service(SSN_REQUEST_FAILED,0);
        ssn_report(); ssn_ui_changed();
        return;
    }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,250000000),dispatch_get_main_queue(),^{ check_signout(); });
}

@implementation SSNNativeBridge
+ (instancetype)sharedBridge {
    static SSNNativeBridge *bridge;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ bridge=[SSNNativeBridge new]; });
    return bridge;
}
- (BOOL)isNativeLaunch { return ssn_native_mode(); }
- (NSDictionary<NSString *,id> *)snapshot {
    NSAssert([NSThread isMainThread],@"Native service snapshots belong to the main thread");
    unsigned owner=(unsigned)[SSNSwiftUIHost rootOwner];
    ssn_presentation(owner);
    char summary[2048]; ssn_summary(summary,sizeof(summary));
    NSMutableArray *runtime=[NSMutableArray arrayWithCapacity:SSN_PROBE_COUNT];
    for(unsigned i=0;i<SSN_PROBE_COUNT;i++)
        [runtime addObject:@{@"name":@(ssn_specs[i].name),@"count":@(ssn_count(i)),@"guarded":@(ssn_specs[i].guard)}];
    BOOL masked=!ssn_native_mode() || signout_state!=0 || ssn_state()==SSN_SIGNED_OUT || ssn_state()==SSN_SESSION_CHANGED;
    return @{@"launchSelector":@(ssn_launch_selector_enabled()),@"launchOrigin":@(ssn_launch_origin()),@"launchError":@(ssn_launch_error()),@"originalLaunchPending":@(ssn_launch_pending()),@"phase":@(ssn_state()),@"account":masked?@{}:(ssn_account_info()?:@{}),
             @"channels":masked?@[]:(ssn_followed_channels()?:@[]),
             @"refreshing":@(ssn_account_refreshing()),@"nativeMode":@(ssn_native_mode()),@"rootOwner":@(owner),@"signOutState":@(signout_state),
             @"canSignOut":@(ssn_native_mode() && ssn_armed() && !ssn_failed() && ssn_logout_target()!=nil),
             @"summary":@(summary),@"runtimeCounts":runtime};
}
- (BOOL)scheduleOriginalLaunch:(BOOL)requested {
    NSAssert([NSThread isMainThread],@"Launch selection belongs to the main thread");
    BOOL saved=ssn_launch_schedule_original(requested);
    ssn_report();ssn_ui_changed();return saved;
}
- (void)refresh {
    NSAssert([NSThread isMainThread],@"Native service actions belong to the main thread");
    if(signout_state==1) return;
    signout_state=0;
    if(ssn_native_mode()) ssn_account_refresh();
    else { ssn_report(); ssn_ui_changed(); }
}
- (BOOL)beginSignOut {
    NSAssert([NSThread isMainThread],@"Native service actions belong to the main thread");
    if(!ssn_native_mode() || signout_state==1 || !ssn_armed() || ssn_failed()) return NO;
    id target=ssn_logout_target();
    if(!target) return NO;
    signout_state=1; signout_ticks=0;
    ssn_account_changed(); ssn_report();
    /* Donor's existing Objective-C adapter owns its Swift witness dispatch and
     * account cleanup. We never read credentials or call a guessed Swift ABI. */
    ((void(*)(id,SEL,BOOL))objc_msgSend)(target,ss("logoutUserWithUserInitiated:"),YES);
    check_signout();
    return YES;
}
- (NSArray<NSURL *> *)exportReports {
    NSAssert([NSThread isMainThread],@"Diagnostic export belongs to the main thread");
    ssn_presentation((unsigned)[SSNSwiftUIHost rootOwner]);
    ssn_report();
    NSString *directory=[@(ssn_report_path()) stringByDeletingLastPathComponent];
    NSString *flavor=ssn_native_mode()?@"native":@"baseline";
    NSMutableArray *urls=[NSMutableArray array];
    for(NSString *suffix in @[@"latest",@"previous"]) {
        NSString *path=[directory stringByAppendingPathComponent:[NSString stringWithFormat:@"%@-%@.json",flavor,suffix]];
        if([[NSFileManager defaultManager] fileExistsAtPath:path]) [urls addObject:[NSURL fileURLWithPath:path]];
    }
    return urls;
}
@end
