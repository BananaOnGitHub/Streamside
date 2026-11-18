#import <UIKit/UIKit.h>
NS_ASSUME_NONNULL_BEGIN
/* Owned facade; no donor SDK header, token or playback URL reaches SwiftUI. */
@interface SSNPlayback : NSObject
- (instancetype)initWithChannel:(NSString *)channel NS_SWIFT_NAME(init(channel:));
/* Preview is always muted, uses Ambient mixing without explicit activation,
 * and retires SDK/audio resources asynchronously. Promotion is
 * explicit and happens only after theatre presentation; it retains the player.
 * Before start, promotion changes intent only; no SDK/audio work is performed. */
- (instancetype)initWithChannel:(NSString *)channel preview:(BOOL)preview NS_SWIFT_NAME(init(channel:preview:));
- (BOOL)enterTheatre;
@property(nonatomic,readonly) UIView *view;
/* 0 stopped, 1 requesting, 2 loading, 3 playing, 4 buffering, 5 background,
 * 6 ended, 7 failed, 8 user-paused. errorCode is a bounded owned category, never donor text. */
@property(nonatomic,readonly) NSInteger phase;
@property(nonatomic,readonly) NSInteger errorCode;
/* Local player controls only; never change the shared system volume. Intent
 * survives start and inactive teardown/recreation. Set muted before start for
 * previews: it is applied before the player loads or plays any media. Pause is
 * reset on start; a new facade defaults to unpaused/unmuted. */
@property(nonatomic,getter=isPaused) BOOL paused;
@property(nonatomic,getter=isMuted) BOOL muted;
- (void)start;
- (void)stop;
@end
NS_ASSUME_NONNULL_END
