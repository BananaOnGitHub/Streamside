#import "SSNContentLabels.h"
#include "SSNContentLabelsRequest.h"
#include "SSNPlaybackRequest.h"
#include "SSNObjC.h"
@implementation SSNContentLabels {
    id _promise,_auth;
    NSArray *_labels;
    NSInteger _phase;
    NSTimeInterval _deadline;
}
@synthesize phase=_phase,labels=_labels;
- (instancetype)initWithChannelID:(NSString *)channelID {
    if((self=[super init])) {
        NSAssert(NSThread.isMainThread,@"Content requests belong to main");
        _labels=[@[] retain];_deadline=NSProcessInfo.processInfo.systemUptime+15;
        _auth=[m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth") retain];
        _promise=ssn_content_labels_request(channelID);if(!_promise) _phase=2;
    }return self;
}
- (void)cancel {
    if(_promise) { v0(_promise,"requestCancel");[_promise release];_promise=nil; }
    if(!_phase) _phase=2;
}
- (void)poll {
    NSAssert(NSThread.isMainThread,@"Content requests belong to main");
    if(_phase) return;
    id auth=m0(m0(c("_TtC6PMHTTP11HTTPManager"),"defaultManager"),"defaultAuth");
    if(!ssn_playback_authorized()||auth!=_auth||NSProcessInfo.processInfo.systemUptime>=_deadline) { [self cancel];return; }
    id value=nil,error=nil;
    BOOL done=((BOOL(*)(id,SEL,id*,id*))objc_msgSend)(_promise,ss("getValue:error:"),&value,&error);
    if(!done) return;
    if(!error&&[value isKindOfClass:NSArray.class]&&[value count]>0&&[value count]<=64) {
        [_labels release];_labels=[value copy];_phase=1;
    } else _phase=2;
    [_promise release];_promise=nil;
}
- (void)dealloc { [self cancel];[_auth release];[_labels release];[super dealloc]; }
@end
