#import <Foundation/Foundation.h>
#import "SSNWindowOwnership.h"
#import "SSNPlayback.h"

NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT NSNotificationName const SSNNativeServiceDidChange;
FOUNDATION_EXPORT void SSNSwiftUIReady(void);
FOUNDATION_EXPORT void SSNNavigationEvent(unsigned event);
FOUNDATION_EXPORT void SSNPlayerControlEvent(unsigned event);
FOUNDATION_EXPORT BOOL SSNNavigationPermitted(void);

/* Owned Objective-C boundary. Snapshots are presentation-only copies: no token,
 * donor Swift value, protocol witness, or request object crosses into SwiftUI. */
@interface SSNNativeBridge : NSObject
+ (instancetype)sharedBridge NS_SWIFT_NAME(shared());
- (NSDictionary<NSString *, id> *)snapshot;
- (BOOL)isNativeLaunch;
- (void)refresh;
- (BOOL)scheduleOriginalLaunch:(BOOL)requested;
- (BOOL)beginSignOut;
- (NSArray<NSURL *> *)exportReports;
@end
NS_ASSUME_NONNULL_END
