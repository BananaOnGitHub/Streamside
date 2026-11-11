#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT NSNotificationName const SSNNativeServiceDidChange;
FOUNDATION_EXPORT void SSNSwiftUIReady(void);

/* Owned Objective-C boundary. Snapshots are presentation-only copies: no token,
 * donor Swift value, protocol witness, or request object crosses into SwiftUI. */
@interface SSNNativeBridge : NSObject
+ (instancetype)sharedBridge NS_SWIFT_NAME(shared());
- (NSDictionary<NSString *, id> *)snapshot;
- (void)refresh;
- (BOOL)beginSignOut;
- (NSArray<NSURL *> *)exportReports;
@end
NS_ASSUME_NONNULL_END
