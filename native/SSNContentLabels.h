#import <Foundation/Foundation.h>
NS_ASSUME_NONNULL_BEGIN
/* Owns native request lifetime. No credentials or native errors enter SwiftUI. */
@interface SSNContentLabels : NSObject
- (instancetype)initWithChannelID:(NSString *)channelID;
/* 0 pending, 1 loaded, 2 failed/cancelled. Main thread only. */
@property(nonatomic,readonly) NSInteger phase;
@property(nonatomic,readonly) NSArray<NSString *> *labels;
- (void)poll;
- (void)cancel;
@end
NS_ASSUME_NONNULL_END
