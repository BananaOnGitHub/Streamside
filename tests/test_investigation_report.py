"""Production bounded numeric transport: hostile input and partial evidence."""
import ctypes as C
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
class ReportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();path=Path(cls.tmp.name)/'report.so'
  subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-pthread',str(ROOT/'src/TASInvestigationReport.c'),'-o',str(path)],check=True)
  cls.lib=C.CDLL(str(path));cls.lib.tas_inv_report_accept.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.c_size_t,C.c_uint64];cls.lib.tas_inv_report_accept.restype=C.c_bool
  cls.lib.tas_inv_report_complete.argtypes=[C.c_uint32,C.c_uint32];cls.lib.tas_inv_report_complete.restype=C.c_bool
  cls.lib.tas_inv_report_format.argtypes=[C.c_void_p,C.c_size_t];cls.lib.tas_inv_report_format.restype=C.c_size_t;cls.seq=0
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):type(self).seq+=1;self.g=10;self.s=type(self).seq
 def accept(self,p,now=1000,g=None,s=None):
  raw=p if isinstance(p,bytes) else json.dumps(p,separators=(',',':')).encode();return self.lib.tas_inv_report_accept(self.g if g is None else g,self.s if s is None else s,raw,len(raw),now)
 def packet(self,part=0,final=0,rows=None):return [4,part,final,rows or [[0 if not part else 1,0,0,0,0,0,0,0,0]]]
 def report(self):
  out=C.create_string_buffer(65536);n=self.lib.tas_inv_report_format(out,len(out));self.assertGreater(n,0);return out.value.decode()
 def test_frozen_partial_then_ordered_complete(self):
  self.assertTrue(self.accept(self.packet()));before=self.report();self.assertIn('complete=0',before)
  self.assertFalse(self.accept(self.packet(1,1),1100));self.assertEqual(self.report(),before)
  self.assertFalse(self.accept(self.packet(2,1),1500));self.assertFalse(self.accept(self.packet(1,1),1500,g=9))
  self.assertTrue(self.accept(self.packet(1,1),1500));self.assertTrue(self.lib.tas_inv_report_complete(self.g,self.s));self.assertIn('complete=1',self.report());self.assertFalse(self.accept(self.packet(2,1),1800))
 def test_reject_strings_objects_floats_nonfinite_and_every_truncation(self):
  valid=json.dumps(self.packet()).encode()
  for bad in [b'NaN',b'Infinity',b'1e1',b'1.0',b'"PRIVATE"',b'{}',b'true',b'null',b'01',b'-10000001',b'10000001']:
   packet=b'[4,0,1,[[0,0,0,0,0,0,0,0,'+bad+b']]]';self.assertFalse(self.accept(packet),bad)
  for at in range(len(valid)):self.assertFalse(self.accept(valid[:at]),at)
  self.assertFalse(self.accept(valid+b' PRIVATE'));self.assertFalse(self.accept(b' '*8193));self.assertTrue(self.accept(valid));self.assertNotIn('PRIVATE',self.report())
 def test_interruption_retains_history_and_blocks_completion(self):
  self.assertTrue(self.accept(self.packet(0,1)));self.lib.tas_inv_report_interrupt();self.assertFalse(self.lib.tas_inv_report_complete(self.g,self.s));self.assertIn('interrupted=1',self.report())
 def test_row_schema_packet_count_size_and_duplicates(self):
  self.assertFalse(self.accept([4,0,0,[[0]*8]]));self.assertFalse(self.accept([4,0,0,[[0]*10]]));self.assertFalse(self.accept([4,0,0,[[0]*9]*2]));self.assertFalse(self.accept([4,0,0,[[0,0,10,0,0,0,0,0,0]]]))
  self.assertTrue(self.accept(self.packet()));self.assertFalse(self.accept(self.packet()));self.assertFalse(self.lib.tas_inv_report_complete(self.g,self.s))
  for part in range(1,8):self.assertTrue(self.accept(self.packet(part,int(part==7)),1000+part*250))
  self.assertFalse(self.accept(self.packet(8,1),4000));self.assertTrue(self.lib.tas_inv_report_complete(self.g,self.s))

 def test_viewport_v3_signed_geometry_measurement_flags_and_profile(self):
  rows=[[0,0,0,0,0,0,0,0,0],[7,1,8,1,0,0,-40,303,5006],[9,1,8,1,1,128|1024|32,119,-1,-3],[9,1,8,1,2,128|2|8,120,0,40],[10,1,8,1,0,1,119,126,8]]
  self.assertFalse(self.accept([1,0,1,rows]))
  self.assertFalse(self.accept([4,0,1,[[0]*9,[13,0,8,1,0,0,0,0,0]]]))
  self.assertFalse(self.accept([4,0,1,[[0]*9,[9,0,8,1,0,2048,0,0,0]]]))
  self.assertTrue(self.accept([4,0,1,rows]));self.assertTrue(self.lib.tas_inv_report_complete(self.g,self.s))
  report=self.report();self.assertIn('numeric-chat-v4',report);self.assertIn('1 unmeasured in current cache,2 measured exactly zero',report);self.assertIn('1024 measurement unavailable',report);self.assertIn('10 range coverage',report);self.assertIn('119,-1,-3',report);self.assertIn('119,126,8',report)


 def test_tail_progress_and_recent_summary_are_derived_from_frozen_numeric_rows(self):
  rows=[[0,0,0,0,0,0,0,0,0]]
  for label in range(1,11):
   rows.extend([[1,label*100,0,12,label,0,2,0,0],[1,label*100+1,1,12,label,0,2,0,0]])
  rows.append([1,9000,1,13,1000,0,2,0,0])
  rows.append([3,11000,4,12,0,0,151,0,11])
  for label in range(1,9):
   rows.append([9,11000,8,12,label,128|(8 if label<=6 else 32),141+label,34000,5500+label*34])
  for index,label in enumerate([10,9,8,7,6,5,4]):
   rows.append([8,11000,4,12,label,32,150-index,0,0])
  rows.extend([[11,11002,4,12,0,1|2|8|512,7,144,150],[10,11002,8,12,0,129,142,149,8]])
  self.assertTrue(self.accept([4,0,1,rows]));self.assertTrue(self.lib.tas_inv_report_complete(self.g,self.s))
  report=self.report()
  self.assertIn('scope=12 available=1 examined=7/151 read_indices=150..144 newest_first=1',report)
  self.assertIn('newest_entry_read=1 all_slots_read=0 time_limited=1 entry_limited=0',report)
  self.assertIn('comparisons_incomplete=1',report)
  self.assertIn('present=6 absent=0 unknown=2',report)
  self.assertIn('selected=8 store_observed=7 visible_list_observed=6',report)
  self.assertIn('unmatched remains unknown',report)
  self.assertIn('11 store traversal',report)

 def test_traversal_unavailable_and_empty_do_not_claim_newest_was_read(self):
  rows=[[0,0,0,0,0,0,0,0,0],[3,1,4,1,0,1,-1,0,0],[11,2,4,1,0,8,0,-1,-1],
        [3,1,4,2,0,0,0,0,0],[11,2,4,2,0,1|4|128,0,-1,-1]]
  self.assertTrue(self.accept([4,0,1,rows]));report=self.report()
  self.assertIn('scope=1 available=0 examined=0/-1',report)
  self.assertIn('scope=2 available=1 examined=0/0',report)
  self.assertEqual(report.count('newest_entry_read=0'),2)
  self.assertIn('empty=1',report)
