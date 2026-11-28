#import <Foundation/Foundation.h>
NS_ASSUME_NONNULL_BEGIN
/* 0 profile, 1 follow state, 2 unfollow, 3 follow, 4 notification choice.
 * All writes are explicit user actions. No credentials/SDK models leave here. */
@interface SSNProfileRequest : NSObject
- (instancetype)initWithChannelID:(NSString *)channelID operation:(NSInteger)operation setting:(NSString *)setting;
- (instancetype)initWithAvatarUserID:(uint32_t)userID NS_SWIFT_NAME(init(avatarUserID:));
- (instancetype)initWithCheerChannelID:(NSString *)channelID global:(BOOL)global NS_SWIFT_NAME(init(cheerChannelID:global:));
- (instancetype)initWithChatChannelID:(NSString *)channelID message:(NSString *)message NS_SWIFT_NAME(init(chatChannelID:message:));
@property(nonatomic,readonly) NSInteger phase;
@property(nonatomic,readonly) NSDictionary<NSString *,id> *result;
- (void)poll;
- (void)cancel;
@end
NS_ASSUME_NONNULL_END
