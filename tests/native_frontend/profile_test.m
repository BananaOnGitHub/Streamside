/* Production owner/normalizer; synthetic native promise, no donor execution. */
#import <Foundation/Foundation.h>
#import "SSNProfile.h"
#import "SSNProfileRequest.h"
static id identity,value;
static BOOL authorized=YES,pending,failed;
static unsigned cancels,requests;
static unsigned stages[5][SSN_PROFILE_STAGE_COUNT];
void ssn_profile_event(unsigned op,unsigned stage) { if(op<5&&stage<SSN_PROFILE_STAGE_COUNT)stages[op][stage]++; }
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
id ssn_profile_avatar_request(uint32_t user_id) {
    NSCAssert(user_id==123&&authorized,@"Authorized numeric avatar lookup");
    requests++;
    return [FakeProfile new];
}
id ssn_chat_send_request(id channel,id message) {
    NSCAssert(authorized&&[channel isEqual:@"123"]&&[message isEqual:@"Hello chat"],@"Authorized chat write targets the active room");
    requests++;
    return [FakeProfile new];
}
@interface FixtureNotificationValue : NSObject
@end
@implementation FixtureNotificationValue
@end
@interface FixturePanel : NSObject
@end
@implementation FixturePanel
@end
@interface FixturePanelList : NSObject
@end
@implementation FixturePanelList
@end
id ssn_profile_unbox_panel(id object) {
    if(![object isKindOfClass:FixturePanel.class])return nil;
    return [@{@"__typename":@"DefaultPanel",@"title":@"About panel",@"description":@"Panel text"} retain];
}
id ssn_profile_unbox_panel_list(id object) {
    if(![object isKindOfClass:FixturePanelList.class])return nil;
    return [@[NSNull.null,[[[FixturePanel alloc] init] autorelease],@42] retain];
}
id ssn_profile_unbox(id object) { (void)object;return nil; }
id ssn_profile_notification_string(id object) {
    return [object isKindOfClass:FixtureNotificationValue.class]?[@"PERSONALIZED" copy]:nil;
}
int main(void) { @autoreleasepool {
    NSDictionary *raw=@{@"user":@{@"displayName":@"Fixture",@"accessToken":@"never pass",@"panels":@[@{@"__typename":@"DefaultPanel",@"description":@"Panel"}]},@"credentials":@"never pass"};
    id clean=ssn_profile_normalize(raw);
    // Collection literal commas must stay outside assertion macro arguments.
    NSDictionary *expected=@{@"user":@{@"displayName":@"Fixture",@"panels":@[@{@"__typename":@"DefaultPanel",@"description":@"Panel"}]}};
    NSCAssert([clean isEqual:expected],@"Whitelist at every depth");[clean release];
    NSCAssert(!ssn_profile_normalize(@{@"user":[NSObject new]}),@"Reject unknown SDK values");
    NSCAssert(!ssn_profile_normalize(@{@"description":[@"x" stringByPaddingToLength:65537 withString:@"x" startingAtIndex:0]}),@"Bound payloads");
    id boxed=[[[FixtureNotificationValue alloc] init] autorelease];
    NSDictionary *relationship=@{@"user":@{@"connection":@{@"canFollow":@YES,@"follower":@{@"notificationSettings":@{@"followsSettingState":boxed}}}}};
    NSDictionary *normalized=ssn_profile_normalize(relationship);
    NSCAssert([normalized[@"user"][@"connection"][@"follower"][@"notificationSettings"][@"followsSettingState"] isEqual:@"PERSONALIZED"],@"Typed settings decode without losing follow state");
    [normalized release];
    NSCAssert(!ssn_profile_normalize(@{@"followsSettingState":@42}),@"Unexpected scalar types cannot become a setting");
    NSCAssert(!ssn_profile_normalize(@{@"description":boxed}),@"Boxed enum decoder is limited to the notification field");
    id typedList=[[[FixturePanelList alloc] init] autorelease];
    NSDictionary *typedResponse=@{@"user":@{@"displayName":@"Fixture",@"panels":typedList,@"currentUser":@{@"subscriptionBenefit":@{@"id":@"fixture-benefit"}}}};
    NSDictionary *typedProfile=ssn_profile_normalize(typedResponse);
    NSArray *typedPanels=typedProfile[@"user"][@"panels"];
    NSCAssert(typedPanels.count==1&&[typedPanels[0][@"title"] isEqual:@"About panel"],@"Nullable boxed panels survive unrelated malformed entries");
    NSCAssert(ssn_profile_panel_stage(typedProfile)==SSN_PROFILE_PANELS_AVAILABLE,@"Panel availability is numeric");
    NSCAssert([typedProfile[@"user"][@"currentUser"][@"subscriptionBenefit"][@"id"] isEqual:@"fixture-benefit"],@"Native subscription benefit survives the profile whitelist");
    [typedProfile release];
    NSDictionary *missingPanels=@{@"user":@{@"displayName":@"Fixture"}};
    NSDictionary *emptyPanels=@{@"user":@{@"panels":@[]}};
    NSDictionary *invalidPanels=@{@"user":@{@"displayName":@"Fixture",@"panels":@42}};
    NSDictionary *invalidProfile=ssn_profile_normalize(invalidPanels);
    NSCAssert(ssn_profile_panel_stage(missingPanels)==SSN_PROFILE_PANELS_MISSING,@"Missing panels differ from an empty array");
    NSCAssert(ssn_profile_panel_stage(emptyPanels)==SSN_PROFILE_PANELS_EMPTY,@"Explicit empty panel array");
    NSCAssert(ssn_profile_panel_stage(invalidProfile)==SSN_PROFILE_PANELS_UNREADABLE&&[invalidProfile[@"user"][@"displayName"] isEqual:@"Fixture"],@"Malformed panel data must not discard the profile");
    [invalidProfile release];
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
    r=[[SSNProfileRequest alloc] initWithChannelID:@"123" operation:0 setting:@""];
    authorized=NO;
    previous=identity;identity=nil;[previous release];
    [r poll];NSCAssert(r.phase==2,@"Account loss cancels");[r release];

    before=requests;
    r=[[SSNProfileRequest alloc] initWithAvatarUserID:123];
    NSCAssert(r.phase==2&&r.result.count==0&&requests==before,@"Signed-out chat does not resolve avatars");[r release];
    authorized=YES;identity=[NSObject new];pending=NO;value=@{@"avatarURL":@"https://example.invalid/small.png"};
    r=[[SSNProfileRequest alloc] initWithAvatarUserID:123];[r poll];
    NSCAssert(requests==before+1&&r.phase==1&&[r.result isEqual:value],@"Avatar result crosses the native bridge");[r release];
    pending=YES;r=[[SSNProfileRequest alloc] initWithAvatarUserID:123];
    previous=identity;identity=[NSObject new];before=cancels;[r poll];
    NSCAssert(r.phase==2&&cancels==before+1&&r.result.count==0,@"Account switch cancels pending avatar lookup");
    [r release];[previous release];

    before=requests;
    r=[[SSNProfileRequest alloc] initWithChatChannelID:@"invalid" message:@"Hello chat"];
    NSCAssert(r.phase==2&&requests==before,@"Invalid channel never submits a chat write");[r release];
    authorized=NO;
    r=[[SSNProfileRequest alloc] initWithChatChannelID:@"123" message:@"Hello chat"];
    NSCAssert(r.phase==2&&requests==before,@"Signed-out chat never submits a write");[r release];

    NSDictionary *sent=@{@"sendChatMessage":@{@"message":@{@"id":@"fixture-id"},@"dropReason":NSNull.null}};
    NSDictionary *dropped=@{@"sendChatMessage":@{@"message":NSNull.null,@"dropReason":@"SLOW_MODE"}};
    id rejected=ssn_chat_send_result(dropped);
    NSCAssert([rejected[@"sent"] isEqual:@NO]&&[rejected count]==1,@"Drop reason stays inside the native bridge");[rejected release];
    NSCAssert(!ssn_chat_send_result(@{@"sendChatMessage":NSNull.null}),@"No delivery confirmation without the result payload");
    authorized=YES;pending=YES;value=ssn_chat_send_result(sent);
    r=[[SSNProfileRequest alloc] initWithChatChannelID:@"123" message:@"Hello chat"];
    [r poll];NSCAssert(r.phase==0,@"Pending write never claims delivery");
    pending=NO;[r poll];
    NSCAssert(r.phase==1&&[r.result[@"sent"] isEqual:@YES]&&r.result.count==1,@"Only the confirmed status crosses the bridge");
    NSCAssert(requests==before+1,@"One chat submission");
    [r release];[value release];value=nil;
    [identity release];identity=nil;
    for(unsigned op=0;op<5;op++) NSCAssert(stages[op][SSN_PROFILE_STARTED]>0&&stages[op][SSN_PROFILE_COMPLETED]==1,@"Each native operation reports request and completion");
    NSCAssert(stages[0][SSN_PROFILE_CANCELLED]>0&&stages[0][SSN_PROFILE_SESSION_CHANGED]==2,@"Cancellation and account boundaries are numeric");
    puts("PROFILE_NATIVE PASS: whitelist, bounds, five native operations, invalid setting, pending, errors, single cancellation, account replacement/loss");
}return 0; }
