/* Production owner/normalizer; synthetic native promise, no donor execution. */
#import <Foundation/Foundation.h>
#import "SSNProfile.h"
#import "SSNProfileRequest.h"
static id identity,value;
static BOOL authorized=YES,pending,failed;
static unsigned cancels,requests;
bool ssn_playback_authorized(void) { return authorized; }
__attribute__((objc_runtime_name("_TtC6PMHTTP11HTTPManager")))
@interface FakeHTTP : NSObject
+ (id)defaultManager;
- (id)defaultAuth;
@end
@implementation FakeHTTP
+ (id)defaultManager { static id instance;if(!instance)instance=[self new];return instance; }
- (id)defaultAuth { return identity; }
@end
@interface FakeProfile : NSObject
- (BOOL)getValue:(id *)result error:(id *)error;
- (void)requestCancel;
@end
@implementation FakeProfile
- (BOOL)getValue:(id *)result error:(id *)error { if(pending)return NO;*result=value;*error=failed?@"Fixture failure":nil;return YES; }
- (void)requestCancel { cancels++; }
@end
id ssn_profile_request(id channel,unsigned operation,id setting) {
    (void)setting;NSCAssert([channel isEqual:@"123"]&&operation<=4,@"Native query identity");requests++;return [FakeProfile new];
}
id ssn_profile_unbox(id object) { (void)object;return nil; }
int main(void) { @autoreleasepool {
    NSDictionary *raw=@{@"user":@{@"displayName":@"Fixture",@"accessToken":@"never pass",@"panels":@[@{@"__typename":@"DefaultPanel",@"description":@"Panel"}]},@"credentials":@"never pass"};
    id clean=ssn_profile_normalize(raw);
    NSCAssert([clean isEqual:@{@"user":@{@"displayName":@"Fixture",@"panels":@[@{@"__typename":@"DefaultPanel",@"description":@"Panel"}]}}],@"Whitelist at every depth");[clean release];
    NSCAssert(!ssn_profile_normalize(@{@"user":[NSObject new]}),@"Reject unknown SDK values");
    NSCAssert(!ssn_profile_normalize(@{@"description":[@"x" stringByPaddingToLength:65537 withString:@"x" startingAtIndex:0]}),@"Bound payloads");
    identity=[NSObject new];value=@{@"user":@{@"displayName":@"Fixture"}};
    for(unsigned op=0;op<5;op++) {
        SSNProfileRequest *r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:op setting:@"PERSONALIZED"];
        pending=YES;[r poll];NSCAssert(r.phase==0&&r.result.count==0,@"No synthetic success while pending");
        pending=NO;[r poll];NSCAssert(r.phase==1&&[r.result isEqual:value],@"Native result");[r release];
    }
    unsigned before=requests;SSNProfileRequest *r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:4 setting:@"INVALID"];
    NSCAssert(r.phase==2&&requests==before,@"Unknown setting never writes");[r release];
    failed=YES;r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:0 setting:@""];[r poll];NSCAssert(r.phase==2,@"Error fails closed");[r release];failed=NO;
    pending=YES;r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:0 setting:@""];before=cancels;
    [r cancel];[r cancel];[r poll];NSCAssert(r.phase==2&&cancels==before+1,@"Cancel exactly once");[r release];
    r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:0 setting:@""];id previous=identity;identity=[NSObject new];[r poll];
    NSCAssert(r.phase==2,@"Account replacement cancels");[r release];[previous release];
    r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:0 setting:@""];authorized=NO;[r poll];NSCAssert(r.phase==2,@"Account loss cancels");[r release];[identity release];
    puts("PROFILE_NATIVE PASS: whitelist, bounds, five native operations, invalid setting, pending, errors, single cancellation, account replacement/loss");
}return 0; }
