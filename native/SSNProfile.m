#import "SSNProfile.h"
#include "SSNProfileRequest.h"
#include "SSNPlaybackRequest.h"
#include "SSNObjC.h"

/* Normalize only profile/follow fields. No HTML execution, SDK value storage,
 * account credentials, error text or unrelated query fields reach SwiftUI. */
static id normalize(id value,unsigned depth,unsigned *remaining) {
    if(!value||depth>10||!*remaining)return nil;(*remaining)--;
    if(value==NSNull.null)return value;
    if([value isKindOfClass:NSString.class])return [value length]<=65536?value:nil;
    if([value isKindOfClass:NSNumber.class])return value;
    if([value isKindOfClass:NSArray.class]) {
        if([value count]>256)return nil;NSMutableArray *result=[NSMutableArray array];
        for(id item in value) { id child=normalize(item,depth+1,remaining);if(!child)return nil;[result addObject:child]; }return result;
    }
    id unboxed=nil;
    if(![value isKindOfClass:NSDictionary.class]) { unboxed=ssn_profile_unbox(value);value=unboxed; }
    if(![value isKindOfClass:NSDictionary.class]) { [unboxed release];return nil; }
    static NSSet *keys;static dispatch_once_t once;
    dispatch_once(&once,^{keys=[[NSSet alloc] initWithArray:@[@"user",@"id",@"login",@"displayName",@"description",@"bannerImageURL",@"profileImageURL",@"followers",@"totalCount",@"channel",@"socialMedias",@"name",@"title",@"url",@"panels",@"__typename",@"linkURL",@"imageURL",@"roles",@"isPartner",@"connection",@"canFollow",@"follower",@"notificationSettings",@"isEnabled",@"followsSettingState",@"unfollowUser",@"followUser",@"follow",@"followedAt",@"error",@"code",@"setLiveNotificationsEnrollment"]];});
    NSMutableDictionary *result=[NSMutableDictionary dictionary];
    for(id key in value) {
        if(![keys containsObject:key])continue;id child=normalize(value[key],depth+1,remaining);
        if(!child) { [unboxed release];return nil; }result[key]=child;
    }
    [unboxed release];return result;
}
id ssn_profile_normalize(id object) { unsigned budget=2048;return [normalize(object,0,&budget) retain]; }

@implementation SSNProfileRequest {
    id _promise,_auth;
    NSDictionary *_result;
    NSInteger _phase;
    NSTimeInterval _deadline;
}
@synthesize phase=_phase,result=_result;
- (instancetype)initWithChannelID:(NSString *)channelID operation:(NSInteger)operation setting:(NSString *)setting {
    if((self=[super init])) {
        NSAssert(NSThread.isMainThread,@"Profile requests belong to main");
        _result=[@{} retain];_deadline=NSProcessInfo.processInfo.systemUptime+15;
        _auth=[m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth") retain];
        if(operation>=0&&operation<=4&&([@[@"PERSONALIZED",@"ALWAYS",@"LIVE_UP_ONLY",@"NEVER"] containsObject:setting]||operation!=4))
            _promise=ssn_profile_request(channelID,(unsigned)operation,setting);
        if(!_promise)_phase=2;
    }return self;
}
- (void)cancel { if(_promise) { v0(_promise,"requestCancel");[_promise release];_promise=nil; }if(!_phase)_phase=2; }
- (void)poll {
    NSAssert(NSThread.isMainThread,@"Profile requests belong to main");if(_phase)return;
    id auth=m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth");
    if(!ssn_playback_authorized()||auth!=_auth||NSProcessInfo.processInfo.systemUptime>=_deadline) { [self cancel];return; }
    id value=nil,error=nil;BOOL done=((BOOL(*)(id,SEL,id*,id*))objc_msgSend)(_promise,ss("getValue:error:"),&value,&error);
    if(!done)return;
    if(!error&&[value isKindOfClass:NSDictionary.class]) { [_result release];_result=[value copy];_phase=1; }else _phase=2;
    [_promise release];_promise=nil;
}
- (void)dealloc { [self cancel];[_auth release];[_result release];[super dealloc]; }
@end
