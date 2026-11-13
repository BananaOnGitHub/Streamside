import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/native_frontend'))
from probes import generate_header
from compare_reports import compare
PLAN=json.loads((ROOT/'native/twitch32.json').read_text())


class CoreEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.directory=Path(cls.temp.name)
        generate_header(PLAN,'1'*64,'host-synthetic-selftest',cls.directory/'SSNBuild.h')
        for mode in [0,1]:
            subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-pthread','-DSSN_NATIVE='+str(mode),
                            '-I'+str(cls.directory),'-I'+str(ROOT/'native'),str(ROOT/'native/SSNCore.c'),
                            str(ROOT/'tests/native_frontend/core_driver.c'),'-o',str(cls.directory/str(mode))],check=True)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def run_core(self,mode,scenario,directory):
        result=subprocess.run([str(self.directory/str(mode)),str(directory),scenario])
        report=json.loads((directory/('native-latest.json' if mode else 'baseline-latest.json')).read_text())
        return result,report

    def test_unobserved_baseline_is_not_zero_activity_proof(self):
        with tempfile.TemporaryDirectory() as d:
            result,report=self.run_core(0,'unknown',Path(d))
            self.assertEqual(result.returncode,0);self.assertFalse(report['baseline_positive_control'])
            self.assertEqual(report['armed_mask'],0);self.assertFalse((Path(d)/'baseline-calibration').exists())

    def test_only_positive_control_arms_matching_native_calibration(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            _,baseline=self.run_core(0,'positive',path);self.assertTrue(baseline['baseline_positive_control'])
            _,native=self.run_core(1,'armed',path);self.assertTrue(native['baseline_calibrated'])
            (path/'baseline-calibration').write_text('0'*64)
            _,mismatch=self.run_core(1,'armed',path);self.assertFalse(mismatch['baseline_calibrated'])
            self.assertEqual(json.loads((path/'native-previous.json').read_text()),native)

    def test_guard_stops_process_and_preserves_failure_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            result,report=self.run_core(1,'deny',Path(d))
            self.assertEqual(result.returncode,86);self.assertEqual(report['failures']&2,2)
            self.assertEqual(report['probes']['hermes_engine'],1)

    def test_export_is_bounded_private_and_contains_only_whitelisted_fields(self):
        with tempfile.TemporaryDirectory() as d:
            _,report=self.run_core(1,'armed',Path(d));path=Path(d)/'native-latest.json'
            self.assertLess(path.stat().st_size,16384);self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertEqual(set(report['probes']),{p['name'] for p in PLAN['probes']})
            self.assertNotIn('username',report);self.assertNotIn('tokens',report);self.assertNotIn('channels',report)
            self.assertFalse(report['memory_available']);self.assertFalse(report['baseline_calibrated'])

    def test_replaced_root_is_reported_separately_from_runtime_activity(self):
        with tempfile.TemporaryDirectory() as d:
            _,report=self.run_core(1,'replaced',Path(d))
            self.assertEqual(report['ui_root_owner'],2)
            self.assertTrue(all(value==0 for value in report['probes'].values()))
            self.assertEqual(report['failures'],0)

    def test_navigation_evidence_is_bounded_and_failure_is_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            _,report=self.run_core(1,'navigation',Path(d))
            self.assertEqual(report['navigation_guard_armed'],1)
            self.assertEqual(report['navigation_events'],[1,1,1,1,1])
            self.assertEqual(report['failures'],1<<11)
            self.assertTrue(all(value==0 for value in report['probes'].values()))

    def test_information_refresh_preserves_only_verified_context_and_records_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            result,report=self.run_core(1,'account-events',Path(d))
            self.assertEqual(result.returncode,0)
            self.assertEqual(report['account_events'],[2,2,2,2,2])
            self.assertEqual(report['account_updates_retained'],2)
            self.assertEqual(report['account_data_clears'],2)
            self.assertEqual(report['failures'],0)
            self.assertTrue(all(value==0 for value in report['probes'].values()))

    def test_playback_failure_survives_closing_without_changing_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            result,report=self.run_core(1,'playback',Path(d))
            self.assertEqual(result.returncode,0)
            self.assertEqual(report['playback_phase'],0)
            self.assertEqual(report['playback_error'],0)
            self.assertEqual(report['playback_last_error'],6)
            self.assertEqual(report['playback_events'],[1]*9)
            self.assertEqual(report['failures'],0)
            self.assertTrue(all(value==0 for value in report['probes'].values()))

    def test_comparison_rejects_host_and_missing_observations(self):
        with tempfile.TemporaryDirectory() as d:
            _,baseline=self.run_core(0,'positive',Path(d));_,native=self.run_core(1,'armed',Path(d))
            self.assertTrue(compare(baseline,native)['failures'])
            del native['probes']['hermes_engine']
            self.assertIn('native: incomplete/invalid probe observations',compare(baseline,native)['failures'])


if __name__=='__main__':unittest.main()
