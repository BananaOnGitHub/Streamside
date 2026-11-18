/* Production request owner with synthetic native promise and account identity. */
#import <Foundation/Foundation.h>
#import "SSNContentLabels.h"
#import "SSNContentLabelsRequest.h"
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
+ (id)defaultManager { static id instance; if(!instance) instance=[self new];return instance; }
- (id)defaultAuth { return identity; }
@end
@interface FakeLabels : NSObject
- (BOOL)getValue:(id *)result error:(id *)error;
- (void)requestCancel;
@end
@implementation FakeLabels
- (BOOL)getValue:(id *)result error:(id *)error {
    NSCAssert(NSThread.isMainThread,@"Main-thread polling");
    if(pending) return NO;
    *result=value;*error=failed?@"synthetic error":nil;return YES;
}
- (void)requestCancel { cancels++; }
@end
id ssn_content_labels_request(id channel) { NSCAssert([channel isEqual:@"123"],@"Native channel identifier");requests++;return [FakeLabels new]; }
int main(void) {
    @autoreleasepool {
        identity=[NSObject new];value=@[@"Fixture label"];
        SSNContentLabels *r=[[SSNContentLabels alloc] initWithChannelID:@"123"];
        pending=YES;[r poll];NSCAssert(r.phase==0&&r.labels.count==0,@"Pending must not supply labels");
        pending=NO;[r poll];NSCAssert(r.phase==1&&[r.labels isEqual:value],@"Only native result labels");[r release];
        for(id result in @[@[],NSNull.null,@"invalid"]) {
            value=result;r=[[SSNContentLabels alloc] initWithChannelID:@"123"];[r poll];NSCAssert(r.phase==2,@"Missing labels fail closed");[r release];
        }
        value=@[@"Label"];failed=YES;r=[[SSNContentLabels alloc] initWithChannelID:@"123"];[r poll];NSCAssert(r.phase==2,@"Errors fail closed");[r release];failed=NO;
        pending=YES;r=[[SSNContentLabels alloc] initWithChannelID:@"123"];unsigned before=cancels;
        [r cancel];[r cancel];[r poll];NSCAssert(r.phase==2&&cancels==before+1,@"Cancel exactly once");[r release];
        r=[[SSNContentLabels alloc] initWithChannelID:@"123"];id previous=identity;identity=[NSObject new];[r poll];
        NSCAssert(r.phase==2,@"Account replacement cancels pending request");[r release];[previous release];
        r=[[SSNContentLabels alloc] initWithChannelID:@"123"];authorized=NO;[r poll];NSCAssert(r.phase==2,@"Account loss cancels request");[r release];
        NSCAssert(requests==8,@"One query per request owner");[identity release];
        puts("CONTENT_LABELS PASS: pending, result, missing labels, errors, single cancellation, account replacement and loss");
    }return 0;
}
