"""Frozen selection policy with fake persistence; Apple persistence is tested in CI."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
DRIVER=r"""
#include "SSNLaunch.h"
#include <assert.h>
#include <stdlib.h>
static bool pending;static unsigned consumes,stores,error;static bool save=true;
unsigned ssn_launch_preference_consume(bool *requested) { consumes++;*requested=pending;pending=false;return error; }
bool ssn_launch_preference_pending(void) { return pending; }
bool ssn_launch_preference_store(bool requested) { stores++;if(save)pending=requested;return save; }
int main(int argc,char **argv) {
    unsigned scenario=argc>1?atoi(argv[1]):0;pending=scenario==1||scenario==2;
    if(scenario==2)error=1;
    ssn_launch_select();ssn_launch_select();
#if SSN_NATIVE && SSN_DEV_LAUNCH_SELECTOR
    assert(consumes==1);assert(ssn_native_mode()==(scenario!=1));
    assert(ssn_launch_origin()==(scenario==1?2:1));assert(ssn_launch_error()==error);
    if(scenario==1) {assert(!pending);assert(!ssn_launch_schedule_original(true));}
    else {assert(ssn_launch_schedule_original(true));assert(pending);assert(ssn_native_mode());
          ssn_launch_select();assert(consumes==1&&pending);assert(ssn_launch_schedule_original(false));assert(!pending);
          save=false;assert(!ssn_launch_schedule_original(true));assert(ssn_launch_error()==2);}
#else
    assert(consumes==0&&stores==0);assert(ssn_native_mode()==SSN_NATIVE);
    assert(!ssn_launch_selector_enabled());assert(!ssn_launch_schedule_original(true));
#endif
    return 0;
}
"""
class LaunchPolicy(unittest.TestCase):
    def test_selection_is_once_and_scheduling_never_switches_running_mode(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'driver.c').write_text(DRIVER)
            for native,dev in [(1,1),(1,0),(0,0),(0,1)]:
                subprocess.run(['cc','-Wall','-Wextra','-Werror','-DSSN_NATIVE='+str(native),'-DSSN_DEV_LAUNCH_SELECTOR='+str(dev),
                    '-I'+str(ROOT/'native'),str(ROOT/'native/SSNLaunch.c'),str(p/'driver.c'),'-o',str(p/'test')],check=True)
                for scenario in range(3):subprocess.run([str(p/'test'),str(scenario)],check=True)
