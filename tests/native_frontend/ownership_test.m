#import <UIKit/UIKit.h>
#import "SSNWindowOwnership.h"
#import <objc/runtime.h>
#include <stdlib.h>

static unsigned blocked, failures;
static BOOL armed;
static __weak UIViewController *lastRequested;
void ssn_navigation_event(unsigned event) { if(event==0) blocked++; else if(event==3) failures++; }
void ssn_navigation_armed(void) { armed=YES; }
void ssn_failure(unsigned event) { (void)event; failures++; }
void ssn_presentation(unsigned owner) { (void)owner; }
void ssn_report(void) {}
@interface SSNSwiftUIHost : NSObject
+ (void)retainAuthenticationRoot:(UIViewController *)root;
@end
@implementation SSNSwiftUIHost
+ (void)retainAuthenticationRoot:(UIViewController *)root { lastRequested=root; }
@end
@interface OverriddenWindow : UIWindow
@end
@implementation OverriddenWindow
- (void)setRootViewController:(UIViewController *)root { [super setRootViewController:root]; }
@end
@interface TestDelegate : UIResponder <UIApplicationDelegate>
@end
@implementation TestDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app; (void)options;
    BOOL passed=YES;
#define CHECK(condition) do { if(!(condition)) passed=NO; } while(0)
    UIWindow *window=[[UIWindow alloc] initWithFrame:CGRectMake(0,0,320,640)];
    UIWindow *other=[[UIWindow alloc] initWithFrame:window.frame];
    UIViewController *initial=[UIViewController new], *root=[UIViewController new], *donor=[UIViewController new];
    window.rootViewController=initial;
    CHECK(window.rootViewController==initial && blocked==0 && !armed);
#if SSN_NATIVE
    OverriddenWindow *override=[[OverriddenWindow alloc] initWithFrame:window.frame];
    CHECK(!SSNInstallWindowOwnership(override,root) && !armed);
    CHECK(SSNInstallWindowOwnership(window,root) && armed && window.rootViewController==root);
    other.rootViewController=donor;
    CHECK(other.rootViewController==donor && blocked==0);
    other.rootViewController=nil;
    window.rootViewController=donor;
    CHECK(window.rootViewController==root && lastRequested==donor && blocked==1);
    window.rootViewController=nil;
    CHECK(window.rootViewController==root && lastRequested==nil && blocked==2);
    window.rootViewController=root;
    CHECK(window.rootViewController==root && blocked==2);
    CHECK(!SSNInstallWindowOwnership(other,donor));
#else
    CHECK(!SSNInstallWindowOwnership(window,root) && !armed);
    window.rootViewController=donor;
    CHECK(window.rootViewController==donor && blocked==0);
#endif
    CHECK(failures==0);
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,500000000),dispatch_get_main_queue(),^{
    NSDictionary *receipt=@{@"passed":@(passed),@"native":@(SSN_NATIVE),@"blocked":@(blocked),@"failures":@(failures)};
    NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    [[NSJSONSerialization dataWithJSONObject:receipt options:0 error:NULL]
        writeToURL:[documents URLByAppendingPathComponent:@"ownership-test.json"] atomically:YES];
    exit(passed?0:1);
    });
    return YES;
}
@end
int main(int argc,char **argv) { @autoreleasepool { return UIApplicationMain(argc,argv,nil,NSStringFromClass(TestDelegate.class)); } }
