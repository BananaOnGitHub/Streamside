#import "SSNProfile.h"
#include "SSNProfileRequest.h"
#include "SSNPlaybackRequest.h"
#include "SSNObjC.h"

/* Normalize only profile/follow fields. No HTML execution, SDK value storage,
 * account credentials, error text or unrelated query fields reach SwiftUI. */
static id normalize_panel(id value) {
    id boxed=nil;
    if(![value isKindOfClass:NSDictionary.class]) {
        boxed=ssn_profile_unbox(value);
        if(!boxed)boxed=ssn_profile_unbox_panel(value);
        value=boxed;
    }
    NSMutableDictionary *panel=[NSMutableDictionary dictionary];
    if([value isKindOfClass:NSDictionary.class]) {
        for(NSString *key in @[@"__typename",@"title",@"description",@"imageURL",@"linkURL"]) {
            id field=value[key];
            if([field isKindOfClass:NSString.class]&&[field length]<=65536)panel[key]=field;
        }
    }
    [boxed release];
    return panel.count?panel:nil;
}

static id normalize_panels(id value) {
    id boxed=nil;
    if(![value isKindOfClass:NSArray.class]) {
        if(value==NSNull.null)return value;
        boxed=ssn_profile_unbox_panel_list(value);
        value=boxed;
    }
    if(![value isKindOfClass:NSArray.class]||[value count]>256) {
        [boxed release];return NSNull.null;
    }
    NSMutableArray *panels=[NSMutableArray array];
    BOOL skipped=NO;
    for(id item in value) {
        if(item==NSNull.null)continue;
        if(panels.count>=64)break;
        id panel=normalize_panel(item);
        if(panel)[panels addObject:panel];
        else skipped=YES;
    }
    [boxed release];
    return skipped&&!panels.count?NSNull.null:panels;
}

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
    dispatch_once(&once,^{keys=[[NSSet alloc] initWithArray:@[@"user",@"id",@"login",@"displayName",@"description",@"bannerImageURL",@"profileImageURL",@"followers",@"totalCount",@"currentUser",@"subscriptionBenefit",@"channel",@"socialMedias",@"name",@"title",@"url",@"panels",@"__typename",@"linkURL",@"imageURL",@"roles",@"isPartner",@"connection",@"canFollow",@"follower",@"notificationSettings",@"isEnabled",@"followsSettingState",@"unfollowUser",@"followUser",@"follow",@"followedAt",@"error",@"code",@"setLiveNotificationsEnrollment"]];});
    NSMutableDictionary *result=[NSMutableDictionary dictionary];
    for(id key in value) {
        if(![keys containsObject:key])continue;
        id field=value[key],decoded=nil;
        if([key isEqual:@"panels"]) {
            result[key]=normalize_panels(field);
            continue;
        }
        if([key isEqual:@"followsSettingState"]&&field!=NSNull.null&&![field isKindOfClass:NSString.class]) {
            decoded=ssn_profile_notification_string(field);
            if(![decoded isKindOfClass:NSString.class]) { [decoded release];[unboxed release];return nil; }
            field=decoded;
        }
        id child=normalize(field,depth+1,remaining);
        if(child)result[key]=child;
        [decoded release];
        if(!child) { [unboxed release];return nil; }
    }
    [unboxed release];return result;
}
id ssn_profile_normalize(id object) { unsigned budget=2048;return [normalize(object,0,&budget) retain]; }

unsigned ssn_profile_panel_stage(id result) {
    id user=result[@"user"];
    id panels=[user isKindOfClass:NSDictionary.class]?user[@"panels"]:nil;
    if(!panels)return SSN_PROFILE_PANELS_MISSING;
    if(![panels isKindOfClass:NSArray.class])return SSN_PROFILE_PANELS_UNREADABLE;
    return [panels count]?SSN_PROFILE_PANELS_AVAILABLE:SSN_PROFILE_PANELS_EMPTY;
}

@implementation SSNProfileRequest {
    id _promise,_auth;
    NSDictionary *_result;
    NSInteger _phase;
    unsigned _operation;
    NSTimeInterval _deadline;
}
@synthesize phase=_phase,result=_result;
- (instancetype)initWithChannelID:(NSString *)channelID operation:(NSInteger)operation setting:(NSString *)setting {
    if((self=[super init])) {
        NSAssert(NSThread.isMainThread,@"Profile requests belong to main");
        _operation=operation>=0&&operation<=4?(unsigned)operation:5;
        ssn_profile_event(_operation,SSN_PROFILE_STARTED);
        _result=[@{} retain];_deadline=NSProcessInfo.processInfo.systemUptime+15;
        _auth=[m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth") retain];
        if(operation>=0&&operation<=4&&([@[@"PERSONALIZED",@"ALWAYS",@"LIVE_UP_ONLY",@"NEVER"] containsObject:setting]||operation!=4))
            _promise=ssn_profile_request(channelID,(unsigned)operation,setting);
        if(!_promise)_phase=2;
    }return self;
}
- (void)cancel { if(_promise) { v0(_promise,"requestCancel");[_promise release];_promise=nil; }if(!_phase) { _phase=2;ssn_profile_event(_operation,SSN_PROFILE_CANCELLED); } }
- (void)poll {
    NSAssert(NSThread.isMainThread,@"Profile requests belong to main");if(_phase)return;
    id auth=m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth");
    if(!ssn_playback_authorized()||auth!=_auth) { ssn_profile_event(_operation,SSN_PROFILE_SESSION_CHANGED);[self cancel];return; }
    if(NSProcessInfo.processInfo.systemUptime>=_deadline) { ssn_profile_event(_operation,SSN_PROFILE_TIMED_OUT);[self cancel];return; }
    id value=nil,error=nil;BOOL done=((BOOL(*)(id,SEL,id*,id*))objc_msgSend)(_promise,ss("getValue:error:"),&value,&error);
    if(!done)return;
    if(!error&&[value isKindOfClass:NSDictionary.class]) { [_result release];_result=[value copy];_phase=1;ssn_profile_event(_operation,SSN_PROFILE_COMPLETED); }
    else { _phase=2;ssn_profile_event(_operation,error?SSN_PROFILE_NATIVE_ERROR:SSN_PROFILE_RESPONSE_REJECTED); }
    [_promise release];_promise=nil;
}
- (void)dealloc { [self cancel];[_auth release];[_result release];[super dealloc]; }
@end
