#include "SSNCore.h"
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
    ssn_service(SSN_READY,2);ssn_scaffold_ready();ssn_transition(true);ssn_transition(false);ssn_transition(true);ssn_report();
    return 0;
}
