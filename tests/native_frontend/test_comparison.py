"""Explicitly synthetic JSON fixtures, never device validation evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/native_frontend'))
from compare_reports import compare,PLAN


def fixture(mode,sequence):
    return dict(schema=1,mode=mode,donor_sha256=PLAN['donor_sha256'],proof_id='synthetic-test',
                armed_mask=15,failures=0,memory_available=True,hardware='synthetic-device',os_kernel='synthetic-os',
                baseline_positive_control=mode=='baseline',launch_sequence=sequence,
                account_list_state=4,foregrounds=2,backgrounds=1,
                probes={p['name']:1 if mode=='baseline' else 0 for p in PLAN['probes']})


class Comparison(unittest.TestCase):
    def setUp(self):self.baseline=fixture('baseline',1);self.previous=fixture('native',1);self.native=fixture('native',2)
    def test_complete_consistent_report_sequence(self):self.assertFalse(compare(self.baseline,self.native,self.previous)['failures'])
    def test_missing_baseline_worklet_observation_is_not_zero(self):
        self.baseline['probes']['worklet_runtime']=0
        self.assertIn('Baseline did not observe worklet_runtime',compare(self.baseline,self.native,self.previous)['failures'])
    def test_previous_launch_is_required_and_must_be_distinct(self):
        self.assertTrue(compare(self.baseline,self.native)['failures'])
        self.assertTrue(compare(self.baseline,self.native,self.native)['failures'])
    def test_runtime_attempt_in_previous_launch_is_preserved(self):
        self.previous['probes']['rn_factory']=1
        self.assertTrue(compare(self.baseline,self.native,self.previous)['failures'])
    def test_different_build_donor_device_and_failed_account_reject(self):
        for key,value in [('proof_id','different'),('donor_sha256','different'),('hardware','different'),('account_list_state',6),('armed_mask',7),('failures',1)]:
            native=copy.deepcopy(self.native);native[key]=value
            with self.subTest(key=key):self.assertTrue(compare(self.baseline,native,self.previous)['failures'])


if __name__=='__main__':unittest.main()
