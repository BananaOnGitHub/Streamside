#import <UIKit/UIKit.h>
NS_ASSUME_NONNULL_BEGIN
/* Owned facade; no donor SDK header, token or playback URL reaches SwiftUI. */
@interface SSNPlayback : NSObject
- (instancetype)initWithChannel:(NSString *)channel NS_SWIFT_NAME(init(channel:));
@property(nonatomic,readonly) UIView *view;
/* 0 stopped, 1 requesting, 2 loading, 3 playing, 4 buffering, 5 background,
 * 6 ended, 7 failed, 8 user-paused. errorCode is a bounded owned category, never donor text. */
@property(nonatomic,readonly) NSInteger phase;
@property(nonatomic,readonly) NSInteger errorCode;
/* Local player controls only; never change the shared system volume. Intent
 * survives inactive teardown/recreation, and is reset for a new start. */
@property(nonatomic,getter=isPaused) BOOL paused;
@property(nonatomic,getter=isMuted) BOOL muted;
- (void)start;
- (void)stop;
@end
NS_ASSUME_NONNULL_END
