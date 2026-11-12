#include "SSNCore.h"
#include "SSNSessionPolicy.h"
#include <string.h>
int main(int argc,char **argv) {
    if(argc!=3) return 2;
    ssn_core_start(argv[1]);
    if(strcmp(argv[2],"unknown")) for(unsigned i=0;i<SSN_IMAGE_COUNT;i++) ssn_arm_image(i,true);
    if(!strcmp(argv[2],"positive")) for(unsigned i=0;i<SSN_PROBE_COUNT;i++) ssn_probe_hit(i);
    if(!strcmp(argv[2],"deny")) {
        for(unsigned i=0;i<SSN_PROBE_COUNT;i++) if(!strcmp(ssn_specs[i].name,"hermes_engine")) ssn_probe_hit(i);
        return 3;
    }
    if(!strcmp(argv[2],"replaced")) { ssn_presentation(1); ssn_presentation(2); }
    if(!strcmp(argv[2],"navigation")) {
        ssn_navigation_armed();
        for(unsigned i=0;i<5;i++) ssn_navigation_event(i);
        ssn_navigation_event(99);
    }
    if(!strcmp(argv[2],"account-events")) {
        for(unsigned event=0;event<7;event++) {
            /* Repeated same-authorization refresh, then a replacement/no context.
             * Login/logout/token and unknown events must never retain data. */
            ssn_account_observed(event,ssn_preserve_account_event(event,true));
            ssn_account_observed(event,ssn_preserve_account_event(event,false));
            if(ssn_preserve_account_event(event,false)) return 4;
            if(event>=2 && ssn_preserve_account_event(event,true)) return 5;
        }
        if(!ssn_preserve_account_event(SSN_USER_UPDATED,true) ||
           !ssn_preserve_account_event(SSN_USER_AVAILABLE,true)) return 6;
        ssn_account_data_cleared();ssn_account_data_cleared();
    }
    ssn_service(SSN_READY,2);ssn_scaffold_ready();ssn_transition(true);ssn_transition(false);ssn_transition(true);ssn_report();
    return 0;
}
