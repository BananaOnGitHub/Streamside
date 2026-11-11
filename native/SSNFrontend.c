/* Deliberately small UIKit frontend. No Twitch-specific class, offset, token or
 * GraphQL operation is known here: all donor integration is in SSNIntegration
 * and SSNAccount. Rows are in-memory presentation data and never enter exports. */
#include "SSNIntegration.h"
#include "SSNCore.h"
#include <stdio.h>
#include <dispatch/dispatch.h>
static Class page_class;
static id page,root,window;
static unsigned ui_generation;
static id cell(id table,const char *title,const char *detail) {
    id value=((id(*)(id,SEL,uintptr_t,id))objc_msgSend)(m0(c("UITableViewCell"),"alloc"),ss("initWithStyle:reuseIdentifier:"),3,nil);
    v1(m0(value,"textLabel"),"setText:",ns(title));
    if(detail) v1(m0(value,"detailTextLabel"),"setText:",ns(detail));
    ((void(*)(id,SEL,long))objc_msgSend)(m0(value,"textLabel"),ss("setNumberOfLines:"),0);
    ((void(*)(id,SEL,long))objc_msgSend)(m0(value,"detailTextLabel"),ss("setNumberOfLines:"),0);
    (void)table; return m0(value,"autorelease");
}
static long sections(id self,SEL cmd,id table) { (void)self;(void)cmd;(void)table;return 4; }
static long row_count(id self,SEL cmd,id table,long section) {
    (void)self;(void)cmd;(void)table;
    if(section==2) return SSN_NATIVE&&num(ssn_followed_channels(),"count")?(long)num(ssn_followed_channels(),"count"):1;
    return section==3?(SSN_NATIVE?2:3):1;
}
static id header(id self,SEL cmd,id table,long section) {
    (void)self;(void)cmd;(void)table;
    static const char *names[]={"Runtime diagnostics","Existing Twitch account","Followed channels — first 50","Actions"};
    return ns(section>=0&&section<4?names[section]:"");
}
static const char *utf8(id value) { return kind(value,"NSString")?((const char*(*)(id,SEL))objc_msgSend)(value,ss("UTF8String")):""; }
static id row(id self,SEL cmd,id table,id index) {
    (void)self;(void)cmd; long section=(long)num(index,"section"),r=(long)num(index,"row");
    if(section==0) { char summary[1024]; ssn_summary(summary,sizeof(summary)); return cell(table,summary,"Export includes counts and measurements; account names and channels stay on this screen."); }
    if(section==1) {
        if(!SSN_NATIVE) return cell(table,"Original Twitch account infrastructure","Use Twitch normally, then return to diagnostics.");
        id account=ssn_account_info();
        return account?cell(table,utf8(get(account,"displayName")),utf8(get(account,"username"))):
            cell(table,ssn_state_text(),"This candidate reuses an existing session. It does not provide a separate sign-in flow.");
    }
    if(section==2) {
        id items=ssn_followed_channels();
        if(SSN_NATIVE&&num(items,"count")>(uintptr_t)r) {
            id item=at(items,(uintptr_t)r); return cell(table,utf8(get(item,"displayName")),utf8(get(item,"status")));
        }
        return cell(table,SSN_NATIVE?ssn_state_text():"The baseline uses Twitch's original frontend",SSN_NATIVE?"Refresh to check the current account and request real data through Twitch's native client.":NULL);
    }
    if(r==0) return cell(table,"Refresh",SSN_NATIVE?"Checks the existing account, then loads followed channels.":"Update runtime counters.");
    if(r==1) return cell(table,"Export report","Share the current and previous numeric diagnostic reports.");
    return cell(table,"Return to Twitch",NULL);
}
static void export_report(id sender) {
    ssn_report();
    id files=m0(c("NSMutableArray"),"new");
    const char *latest=ssn_report_path();
    char directory[1024]; snprintf(directory,sizeof(directory),"%s",latest);
    char *end=strrchr(directory,'/'); if(end) *end=0;
    static const char *names[]={"native-latest.json","native-previous.json","baseline-latest.json","baseline-previous.json"};
    for(unsigned i=0;i<sizeof(names)/sizeof(*names);i++) {
        char path[1200]; snprintf(path,sizeof(path),"%s/%s",directory,names[i]);
        id name=ns(path);
        if(((BOOL(*)(id,SEL,id))objc_msgSend)(m0(c("NSFileManager"),"defaultManager"),ss("fileExistsAtPath:"),name))
            v1(files,"addObject:",m1(c("NSURL"),"fileURLWithPath:",name));
    }
    id activity=((id(*)(id,SEL,id,id))objc_msgSend)(m0(c("UIActivityViewController"),"alloc"),ss("initWithActivityItems:applicationActivities:"),files,nil);
    id popover=m0(activity,"popoverPresentationController"),view=m0(page,"view");
    v1(popover,"setSourceView:",view);
    SSNRect bounds=((SSNRect(*)(id,SEL))objc_msgSend)(view,ss("bounds"));
    ((void(*)(id,SEL,SSNRect))objc_msgSend)(popover,ss("setSourceRect:"),(SSNRect){bounds.width/2,bounds.height/2,1,1});
    ((void(*)(id,SEL,id,BOOL,id))objc_msgSend)(page,ss("presentViewController:animated:completion:"),activity,YES,nil);
    objc_release(activity); objc_release(files); (void)sender;
}
static void selected(id self,SEL cmd,id table,id index) {
    (void)self;(void)cmd;
    ((void(*)(id,SEL,id,BOOL))objc_msgSend)(table,ss("deselectRowAtIndexPath:animated:"),index,YES);
    if(num(index,"section")!=3) return;
    switch(num(index,"row")) {
        case 0: if(SSN_NATIVE) ssn_account_refresh(); else { ssn_report(); ssn_ui_changed(); } break;
        case 1: export_report(table); break;
        default: ((void(*)(id,SEL,BOOL,id))objc_msgSend)(page,ss("dismissViewControllerAnimated:completion:"),YES,nil); break;
    }
}
static id make_page(void) {
    id value=((id(*)(id,SEL,long))objc_msgSend)(m0((id)page_class,"alloc"),ss("initWithStyle:"),2);
    v1(value,"setTitle:",ns(SSN_NATIVE?"Streamside Native Proof":"Twitch Baseline Diagnostics"));
    return value;
}
static void open_baseline(id self,SEL cmd,id sender) {
    (void)self;(void)cmd;
    /* UILongPressGestureRecognizer sends several states; present once on began. */
    if(num(sender,"state")!=1 || m0(root,"presentingViewController")) return;
    id presenter=m0(window,"rootViewController");
    for(unsigned i=0;i<16 && m0(presenter,"presentedViewController");i++)
        presenter=m0(presenter,"presentedViewController");
    ((void(*)(id,SEL,id,BOOL,id))objc_msgSend)(presenter,ss("presentViewController:animated:completion:"),root,YES,nil);
    ssn_ui_changed();
}
static void update(void *context) {
    if((unsigned)(uintptr_t)context!=ui_generation) return;
    ssn_ui_changed();
    dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,2000000000),dispatch_get_main_queue(),context,update);
}
void ssn_ui_changed(void) { if(page) v0(m0(page,"tableView"),"reloadData"); }
void ssn_ui_attach(id app_window) {
    if(window) { if(window!=app_window) ssn_failure(4); return; }
    window=objc_retain(app_window);
    page_class=objc_allocateClassPair(objc_getClass("UITableViewController"),"SSNProofPage",0);
    if(!page_class) { ssn_failure(4); return; }
    class_addMethod(page_class,ss("numberOfSectionsInTableView:"),(IMP)sections,"q24@0:8@16");
    class_addMethod(page_class,ss("tableView:numberOfRowsInSection:"),(IMP)row_count,"q32@0:8@16q24");
    class_addMethod(page_class,ss("tableView:titleForHeaderInSection:"),(IMP)header,"@32@0:8@16q24");
    class_addMethod(page_class,ss("tableView:cellForRowAtIndexPath:"),(IMP)row,"@32@0:8@16@24");
    class_addMethod(page_class,ss("tableView:didSelectRowAtIndexPath:"),(IMP)selected,"v32@0:8@16@24");
    class_addMethod(page_class,ss("openProof:"),(IMP)open_baseline,"v24@0:8@16");
    objc_registerClassPair(page_class); page=make_page();
    root=m1(m0(c("UINavigationController"),"alloc"),"initWithRootViewController:",page);
    ((void(*)(id,SEL,double))objc_msgSend)(m0(page,"tableView"),ss("setRowHeight:"),-1);
    ((void(*)(id,SEL,double))objc_msgSend)(m0(page,"tableView"),ss("setEstimatedRowHeight:"),100);
    if(SSN_NATIVE) v1(window,"setRootViewController:",root);
    else {
        /* No overlay may cover Twitch's account/settings controls. A two-finger
         * hold offers diagnostic access without reserving a tappable rectangle. */
        id gesture=((id(*)(id,SEL,id,SEL))objc_msgSend)(m0(c("UILongPressGestureRecognizer"),"alloc"),ss("initWithTarget:action:"),page,ss("openProof:"));
        ((void(*)(id,SEL,uintptr_t))objc_msgSend)(gesture,ss("setNumberOfTouchesRequired:"),2);
        ((void(*)(id,SEL,double))objc_msgSend)(gesture,ss("setMinimumPressDuration:"),1.0);
        ((void(*)(id,SEL,BOOL))objc_msgSend)(gesture,ss("setCancelsTouchesInView:"),NO);
        ((void(*)(id,SEL,BOOL))objc_msgSend)(gesture,ss("setDelaysTouchesBegan:"),NO);
        ((void(*)(id,SEL,BOOL))objc_msgSend)(gesture,ss("setDelaysTouchesEnded:"),NO);
        v1(window,"addGestureRecognizer:",gesture);
        objc_release(gesture);
    }
    ssn_scaffold_ready(); ssn_report(); ui_generation++;
    dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,2000000000),dispatch_get_main_queue(),(void*)(uintptr_t)ui_generation,update);
}
