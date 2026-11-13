#import "SSNWindowOwnership.h"
#import "SSNSwiftUI-Swift.h"
#import <objc/runtime.h>
#include "SSNCore.h"
#include <stdlib.h>
#include <string.h>

static __weak UIWindow *ownedWindow;
static __weak UIViewController *ownedRoot;
static IMP originalSetter;

static void setRoot(UIWindow *window, SEL selector, UIViewController *requested) {
    if(window != ownedWindow || requested == ownedRoot) {
        ((void(*)(id,SEL,UIViewController *))originalSetter)(window,selector,requested);
        return;
    }
    /* The native router still processes account/routing side effects. Only the
     * window handoff is refused. Do not change the requested controller tree. */
    ssn_navigation_event(0);
    if(![NSThread isMainThread]) { ssn_navigation_event(3); ssn_failure(11); ssn_report(); return; }
    [SSNSwiftUIHost retainAuthenticationRoot:requested];
    ssn_presentation(1); ssn_report();
}

BOOL SSNInstallWindowOwnership(UIWindow *window, UIViewController *root) {
    if(!ssn_native_mode() || ![NSThread isMainThread] || !window || !root || ownedWindow) return NO;
    SEL selector=@selector(setRootViewController:);
    Method method=class_getInstanceMethod(UIWindow.class,selector);
    if(!method || method_getNumberOfArguments(method)!=3) return NO;
    char *result=method_copyReturnType(method), *selfType=method_copyArgumentType(method,0);
    char *cmdType=method_copyArgumentType(method,1), *argument=method_copyArgumentType(method,2);
    BOOL valid=result && selfType && cmdType && argument && !strcmp(result,"v") &&
        !strcmp(selfType,"@") && !strcmp(cmdType,":") && !strcmp(argument,"@");
    free(result); free(selfType); free(cmdType); free(argument);
    IMP current=method_getImplementation(method);
    /* Refuse a subclass override rather than silently missing root writes. */
    if(!valid || class_getMethodImplementation(window.class,selector)!=current) return NO;
    originalSetter=current;
    ownedWindow=window; ownedRoot=root;
    method_setImplementation(method,(IMP)setRoot);
    window.rootViewController=root;
    ssn_navigation_armed();ssn_frontend_event(2);
    return window.rootViewController==root;
}
