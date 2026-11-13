#include "SSNLaunch.h"
#ifndef SSN_NATIVE
#error Default package frontend must be explicit
#endif
static bool selected,native_mode=SSN_NATIVE;
static unsigned origin=SSN_NATIVE?1:0,selection_error;
#if SSN_DEV_LAUNCH_SELECTOR
/* Platform owns application-local preference I/O, never account credentials. */
extern unsigned ssn_launch_preference_consume(bool *requested);
extern bool ssn_launch_preference_pending(void);
extern bool ssn_launch_preference_store(bool requested);
#endif
void ssn_launch_select(void) {
    if(selected) return;
    selected=true;
#if SSN_DEV_LAUNCH_SELECTOR
    if(SSN_NATIVE) {
        bool requested=false;
        selection_error=ssn_launch_preference_consume(&requested);
        if(!selection_error&&requested) { native_mode=false;origin=2; }
    }
#endif
}
bool ssn_native_mode(void) { return native_mode; }
unsigned ssn_launch_origin(void) { return origin; }
unsigned ssn_launch_error(void) { return selection_error; }
bool ssn_launch_selector_enabled(void) { return SSN_DEV_LAUNCH_SELECTOR&&SSN_NATIVE; }
bool ssn_launch_pending(void) {
#if SSN_DEV_LAUNCH_SELECTOR
    return ssn_launch_selector_enabled()&&ssn_launch_preference_pending();
#else
    return false;
#endif
}
bool ssn_launch_schedule_original(bool requested) {
#if SSN_DEV_LAUNCH_SELECTOR
    if(!selected||!native_mode||!SSN_NATIVE) return false;
    if(!ssn_launch_preference_store(requested)) { selection_error=2;return false; }
    return true;
#else
    (void)requested;return false;
#endif
}
