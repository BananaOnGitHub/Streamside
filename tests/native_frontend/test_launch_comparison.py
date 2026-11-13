import copy
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/native_frontend'))
from compare_launch_modes import compare,PLAN,CONTRACT
class LaunchComparison(unittest.TestCase):
    def setUp(self):
        self.control=dict(schema=1,mode='baseline',launch_origin=0,packaged_native=False,development_launch_selector=False,
            launch_selection_error=0,original_launch_pending=False,probe_contract=CONTRACT,donor_sha256=PLAN['donor_sha256'],
            armed_mask=15,failures=0,probes={p['name']:1 for p in PLAN['probes']},baseline_positive_control=True,
            native_frontend_events=[0]*4,ui_root_owner=2,navigation_guard_armed=0,navigation_events=[0]*5,
            account_events=[0]*5,returned_channel_count=0,playback_events=[0]*9,source_revision='synthetic',proof_id='synthetic',hardware='synthetic',os_kernel='synthetic')
        self.one=copy.deepcopy(self.control);self.one.update(launch_origin=2,packaged_native=True,development_launch_selector=True)
    def test_complete_positive_controls_are_consistent(self):self.assertEqual(compare(self.control,self.one)['failures'],[])
    def test_missing_observation_is_never_absence(self):
        for key in self.one:
            r=copy.deepcopy(self.one);r.pop(key)
            with self.subTest(key=key):self.assertTrue(compare(self.control,r)['failures'])
    def test_native_hooks_or_incomplete_runtime_are_rejected(self):
        for key,value in [('native_frontend_events',[0,1,0,0]),('original_launch_pending',True),('navigation_guard_armed',1),('armed_mask',7),('probes',{})]:
            r=copy.deepcopy(self.one);r[key]=value
            with self.subTest(key=key):self.assertTrue(compare(self.control,r)['failures'])
