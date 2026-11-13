#import <CoreFoundation/CoreFoundation.h>
#include "SSNLaunch.h"
#if SSN_DEV_LAUNCH_SELECTOR
static CFStringRef const key=CFSTR("dev.streamside.diagnostics.nextLaunchOriginalUI");
unsigned ssn_launch_preference_consume(bool *requested) {
    *requested=false;
    CFPropertyListRef value=CFPreferencesCopyAppValue(key,kCFPreferencesCurrentApplication);
    if(!value) return 0;
    bool valid=CFGetTypeID(value)==CFBooleanGetTypeID();
    bool original=valid&&CFBooleanGetValue((CFBooleanRef)value);
    CFRelease(value);
    /* Commit deletion before permitting original startup, including malformed
     * values. A failed deletion keeps native guards enabled for this launch. */
    CFPreferencesSetAppValue(key,NULL,kCFPreferencesCurrentApplication);
    if(!CFPreferencesAppSynchronize(kCFPreferencesCurrentApplication)) return 1;
    if(!valid) return 3;
    *requested=original;return 0;
}
bool ssn_launch_preference_pending(void) {
    CFPropertyListRef value=CFPreferencesCopyAppValue(key,kCFPreferencesCurrentApplication);
    bool pending=value&&CFGetTypeID(value)==CFBooleanGetTypeID()&&CFBooleanGetValue((CFBooleanRef)value);
    if(value) CFRelease(value);return pending;
}
bool ssn_launch_preference_store(bool requested) {
    CFPreferencesSetAppValue(key,requested?kCFBooleanTrue:NULL,kCFPreferencesCurrentApplication);
    return CFPreferencesAppSynchronize(kCFPreferencesCurrentApplication);
}
#endif
