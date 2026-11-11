#include "SSNIntegration.h"
#include "SSNCore.h"
#include <mach-o/dyld.h>
#include <dlfcn.h>
#include <dispatch/dispatch.h>
#include <stdio.h>
static IMP original_connect;
static Class observer_class;
static id observer;
static const struct mach_header *image(const char *name) {
    for(uint32_t i=0;i<_dyld_image_count();i++) {
        const char *path=_dyld_get_image_name(i),*base=strrchr(path,'/');
        if(!strcmp(base?base+1:path,name)) return _dyld_get_image_header(i);
    }
    return NULL;
}
id ssn_logout_target(void) {
    const char *base=(const char*)image(ssn_logout.image);
    Class cls=objc_getClass(ssn_logout.class_name);
    id target=m0(m0(c("UIApplication"),"sharedApplication"),"delegate");
    if(!base || !cls || !kind(target,ssn_logout.class_name) ||
       !method_is(cls,ssn_logout.selector,ssn_logout.encoding,false)) return nil;
    IMP method=class_getMethodImplementation(cls,ss(ssn_logout.selector));
    const void *expected=base+ssn_logout.offset;
    return (const void*)method==expected && !memcmp(expected,ssn_logout.prefix,16)?target:nil;
}
void *ssn_resolve(const char *name) {
    for(size_t i=0;i<sizeof(ssn_abi)/sizeof(*ssn_abi);i++) if(!strcmp(name,ssn_abi[i].name)) {
        const char *base=(const char*)image(ssn_abi[i].image);
        void *symbol=dlsym(RTLD_DEFAULT,name);
        void *expected=base?(void*)(base+ssn_abi[i].offset):NULL;
        if(!expected||memcmp(expected,ssn_abi[i].prefix,16)||symbol!=expected) return NULL;
        return symbol;
    }
    return NULL;
}
static void added(const struct mach_header *header,intptr_t slide) {
    (void)slide;
    for(unsigned i=0;i<SSN_IMAGE_COUNT;i++) if(header==image(ssn_images[i].name)) {
        const char *base=(const char*)header;
        bool valid=!memcmp(base+ssn_images[i].cave,"SSNPROBE",8);
        char proof[65];
        for(unsigned b=0;b<32;b++) snprintf(proof+2*b,3,"%02x",(unsigned char)base[ssn_images[i].cave+8+b]);
        valid=valid&&!strcmp(proof,SSN_PROOF_ID);
        for(unsigned p=0;p<SSN_PROBE_COUNT;p++) if(!strcmp(ssn_specs[p].image,ssn_images[i].name)) {
            uint32_t op; memcpy(&op,base+ssn_specs[p].offset,4); if(op!=ssn_specs[p].opcode) valid=false;
        }
        if(valid) __atomic_store_n((uintptr_t*)(base+ssn_images[i].slot),(uintptr_t)ssn_probe_hit,__ATOMIC_RELEASE);
        ssn_arm_image(i,valid);
    }
}
static void after_restore(void *unused) {
    (void)unused;
    if(num(m0(c("UIApplication"),"sharedApplication"),"applicationState")==0) ssn_account_refresh();
}
static void connect_scene(id self,SEL cmd,id scene,id session,id options) {
    ((void(*)(id,SEL,id,id,id))original_connect)(self,cmd,scene,session,options);
    id window=m0(self,"window");
    if(kind(window,"UIWindow")) ssn_ui_attach(window); else ssn_failure(4);
}
static void active(id self,SEL cmd,id notification) {
    (void)self;(void)cmd;(void)notification;
    ssn_transition(true);
    dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,1000000000),dispatch_get_main_queue(),NULL,after_restore);
}
static void background(id self,SEL cmd,id notification) {
    (void)self;(void)cmd;(void)notification; ssn_transition(false);
}
static void account_change_main(void *unused) {
    (void)unused; ssn_account_changed();
    dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,500000000),dispatch_get_main_queue(),NULL,after_restore);
}
static void account_change(id self,SEL cmd,id notification) {
    (void)self;(void)cmd;(void)notification;
    dispatch_async_f(dispatch_get_main_queue(),NULL,account_change_main);
}
static void observe(id name,const char *selector) {
    if(!kind(name,"NSString")) { ssn_failure(2); return; }
    ((void(*)(id,SEL,id,SEL,id,id))objc_msgSend)(m0(c("NSNotificationCenter"),"defaultCenter"),
        ss("addObserver:selector:name:object:"),observer,ss(selector),name,nil);
}
void ssn_integration_start(void) {
    id manager=m0(c("NSFileManager"),"defaultManager");
    id urls=((id(*)(id,SEL,uintptr_t,uintptr_t))objc_msgSend)(manager,ss("URLsForDirectory:inDomains:"),14,1);
    id directory=m1(num(urls,"count")?at(urls,0):nil,"URLByAppendingPathComponent:",ns("StreamsideNativeProof"));
    BOOL created=((BOOL(*)(id,SEL,id,BOOL,id,id*))objc_msgSend)(manager,ss("createDirectoryAtURL:withIntermediateDirectories:attributes:error:"),directory,YES,nil,NULL);
    const char *path=((const char*(*)(id,SEL))objc_msgSend)(directory,ss("fileSystemRepresentation"));
    if(!created||!path) { ssn_failure(9); return; }
    ssn_core_start(path);
    _dyld_register_func_for_add_image(added);
    Class scene=objc_getClass("_TtC6Twitch13SceneDelegate");
    if(!method_is(scene,"scene:willConnectToSession:options:","v40@0:8@16@24@32",false)||!method_is(scene,"window","@16@0:8",false)) { ssn_failure(2); return; }
    original_connect=method_setImplementation(class_getInstanceMethod(scene,ss("scene:willConnectToSession:options:")),(IMP)connect_scene);
    observer_class=objc_allocateClassPair(objc_getClass("NSObject"),"SSNProofObserver",0);
    if(!observer_class) { ssn_failure(2); return; }
    class_addMethod(observer_class,ss("active:"),(IMP)active,"v24@0:8@16");
    class_addMethod(observer_class,ss("background:"),(IMP)background,"v24@0:8@16");
    class_addMethod(observer_class,ss("account:"),(IMP)account_change,"v24@0:8@16");
    objc_registerClassPair(observer_class); observer=m0((id)observer_class,"new");
    observe(ns("UIApplicationDidBecomeActiveNotification"),"active:");
    observe(ns("UIApplicationDidEnterBackgroundNotification"),"background:");
    const char *symbols[]={"$sSo18NSNotificationNamea14TwitchIdentityE11UserUpdatedABvgZ",
        "$sSo18NSNotificationNamea14TwitchIdentityE15UserIsAvailableABvgZ",
        "$sSo18NSNotificationNamea14TwitchIdentityE12UserDidLogInABvgZ",
        "$sSo18NSNotificationNamea14TwitchIdentityE13UserDidLogOutABvgZ",
        "$sSo18NSNotificationNamea14TwitchIdentityE22UserAccessTokenChangedABvgZ"};
    for(unsigned i=0;i<sizeof(symbols)/sizeof(*symbols);i++) {
        id (__attribute__((swiftcall)) *getter)(void)=ssn_resolve(symbols[i]);
        if(!getter) { ssn_failure(2); continue; }
        id name=getter(); observe(name,"account:"); objc_release(name);
    }
    ssn_report();
}
__attribute__((constructor)) static void initialize(void) { ssn_integration_start(); }
