"""Compiled production graft, not a reimplementation of snapshot generation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from validate_rn_snapshot import check_gate, fingerprints, RUNTIME_COMMIT, DONOR_SHA, WINDOW_BASELINE

class SnapshotGateTests(unittest.TestCase):
    def test_missing_failed_and_stale_records_block_build_gate(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'record.json'
            with self.assertRaises(FileNotFoundError):check_gate(path)
            data={'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA,'accepted_snapshots':0,'passed':True,'inputs':fingerprints()}
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):check_gate(path)
            data['accepted_snapshots']=1;data['inputs']['src/TASImageDemand.c']='stale'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):check_gate(path)
            data['inputs']=fingerprints();data['passed']=False;path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):check_gate(path)
            data['passed']=True;data.update(window_algorithm_validated=True,window_baseline=WINDOW_BASELINE['id'],window_scenarios=WINDOW_BASELINE['expected_window_calculations'])
            path.write_text(json.dumps(data));check_gate(path)

    def test_missing_failed_partial_or_wrong_donor_virtualization_evidence_blocks_gate(self):
        good={'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA,'accepted_snapshots':32,'passed':True,'inputs':fingerprints(),
              'window_algorithm_validated':True,'window_baseline':WINDOW_BASELINE['id'],'window_scenarios':WINDOW_BASELINE['expected_window_calculations']}
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'record.json'
            for key,value in [('window_algorithm_validated',None),('window_algorithm_validated',False),('window_baseline',None),('window_baseline','old-baseline'),('window_scenarios',1584),('donor_sha256','different-Twitch-bundle')]:
                with self.subTest(key=key,value=value):
                    data=dict(good)
                    if value is None:data.pop(key)
                    else:data[key]=value
                    path.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):check_gate(path)
            path.write_text(json.dumps(good));check_gate(path)

    @unittest.skipUnless(all(os.environ.get(k) for k in ['TAS_HERMES_SNAPSHOT_RUNNER','TAS_HERMES_SOURCE','TAS_HERMESC','TAS_RN_DONOR','ZIG']),
                         'Matching Hermes runner required; release gate cannot skip runtime validation')
    def test_grafted_bytecode_generates_and_delivers_real_snapshots(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'record.json'
            result=subprocess.run([sys.executable,str(ROOT/'tools/validate_rn_snapshot.py'),
                '--record',str(path),'--donor',os.environ['TAS_RN_DONOR'],'--zig',os.environ['ZIG'],
                '--hermesc',os.environ['TAS_HERMESC'],'--runner',os.environ['TAS_HERMES_SNAPSHOT_RUNNER'],
                '--runtime-source',os.environ['TAS_HERMES_SOURCE']],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads(path.read_text());self.assertEqual(data['accepted_snapshots'],32);self.assertTrue(data['window_algorithm_validated']);self.assertEqual(data['window_baseline'],WINDOW_BASELINE['id']);self.assertEqual(data['window_scenarios'],WINDOW_BASELINE['expected_window_calculations']);check_gate(path)
            report=(path.parent/'snapshot-runtime-report.txt').read_text()
            self.assertIn('viewport/content=370.00/10360.00',report)
            self.assertIn('calc list=2 transition=16',report)
            for name in ['props/catalog','content/scroll metrics','numeric classification','base values','metric getter','metric observer install','frame sampling','metric observer restore','result values','frame packing','serialization','native delivery']:
                line=next(x for x in report.splitlines() if x.startswith('Snapshot step '+name+' attempted/passed/failed:'))
                self.assertGreaterEqual(int(line.rsplit('/',1)[1]),1)
