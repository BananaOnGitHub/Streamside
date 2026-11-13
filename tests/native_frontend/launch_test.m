/* Three independent iOS processes, production preferences and root guard.
 * No donor/account/runtime; this validates selection, not Twitch equivalence. */
#import <UIKit/UIKit.h>
#import <objc/runtime.h>
#import "SSNLaunch.h"
#import "SSNWindowOwnership.h"
#include <stdlib.h>
static unsigned failures,armed,frontends;
void ssn_navigation_event(unsigned event) { (void)event;failures++; }
void ssn_navigation_armed(void) { armed++; }
void ssn_failure(unsigned event) { (void)event;failures++; }
void ssn_presentation(unsigned owner) { (void)owner; }
void ssn_report(void) {}
void ssn_frontend_event(unsigned event) { (void)event;frontends++; }
@interface SSNSwiftUIHost : NSObject
+ (void)retainAuthenticationRoot:(UIViewController *)root;
@end
@implementation SSNSwiftUIHost
+ (void)retainAuthenticationRoot:(UIViewController *)root { (void)root;failures++; }
@end
@interface LaunchDelegate : UIResponder <UIApplicationDelegate>
@end
@implementation LaunchDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app;(void)options;
    NSInteger stage=[NSUserDefaults.standardUserDefaults integerForKey:@"fixtureStage"];
    BOOL passed=stage>=0&&stage<=2;
#define CHECK(x) do {if(!(x))passed=NO;}while(0)
    CHECK(ssn_launch_selector_enabled()&&ssn_launch_error()==0);
    CHECK(ssn_native_mode()==(stage!=1));CHECK(ssn_launch_origin()==(stage==1?2:1));
    CHECK(!ssn_launch_pending());
    UIWindow *window=[[UIWindow alloc] initWithFrame:CGRectMake(0,0,320,640)];
    UIViewController *original=[UIViewController new],*native=[UIViewController new];window.rootViewController=original;
    IMP before=class_getMethodImplementation(UIWindow.class,@selector(setRootViewController:));
    BOOL installed=SSNInstallWindowOwnership(window,native);
    CHECK(installed==(stage!=1));
    if(stage==1) {
        CHECK(window.rootViewController==original&&armed==0&&frontends==0);
        CHECK(class_getMethodImplementation(UIWindow.class,@selector(setRootViewController:))==before);
        CHECK(!ssn_launch_schedule_original(YES));
    } else {
        CHECK(window.rootViewController==native&&armed==1&&frontends==1);
        if(stage==0) {CHECK(ssn_launch_schedule_original(YES));CHECK(ssn_launch_pending());}
    }
    ssn_launch_select(); // A repeated call or foregrounding cannot consume a scheduled launch.
    CHECK(ssn_native_mode()==(stage!=1));CHECK(ssn_launch_pending()==(stage==0));CHECK(failures==0);
    [NSUserDefaults.standardUserDefaults setInteger:stage+1 forKey:@"fixtureStage"];
    CHECK([NSUserDefaults.standardUserDefaults synchronize]);
    NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *receiptURL=[documents URLByAppendingPathComponent:@"launch-test.json"];
    NSMutableArray *stages=[[NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfURL:receiptURL]?:[NSData data] options:NSJSONReadingMutableContainers error:NULL] mutableCopy]?:[NSMutableArray new];
    [stages addObject:@{@"stage":@(stage),@"passed":@(passed),@"native":@(ssn_native_mode()),@"pending":@(ssn_launch_pending()),@"origin":@(ssn_launch_origin())}];
    CHECK([[NSJSONSerialization dataWithJSONObject:stages options:0 error:NULL] writeToURL:receiptURL atomically:YES]);
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,300000000),dispatch_get_main_queue(),^{exit(passed?0:1);});
    return YES;
}
@end
int main(int argc,char **argv) { @autoreleasepool {
    ssn_launch_select();return UIApplicationMain(argc,argv,nil,NSStringFromClass(LaunchDelegate.class));
} }
