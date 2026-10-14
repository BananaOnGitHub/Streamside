"""Trace collector/observer tests; host mocks are not device rendering evidence."""
import ctypes
import shutil
import subprocess
import tempfile
import unittest
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
class ChatTraceTests(unittest.TestCase):
    def test_gate_refuses_missing_failed_and_stale_records(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from validate_chat_trace import fingerprints,check_gate,RUNTIME_COMMIT,DONOR_SHA
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'record.json'
            with self.assertRaises(FileNotFoundError):check_gate(path)
            value={'passed':True,'factory_executed':True,'redemption_executed':True,'inputs':fingerprints(),'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA}
            path.write_text(json.dumps(value));check_gate(path)
            for field,bad in (('passed',False),('factory_executed',False),('redemption_executed',False),('inputs',{}),('runtime_commit','wrong'),('donor_sha256','wrong')):
                changed=dict(value);changed[field]=bad;path.write_text(json.dumps(changed))
                with self.subTest(field=field),self.assertRaises(ValueError):check_gate(path)
    def native(self, folder):
        path=Path(folder)/'trace.c'
        path.write_text('#define TAS_CHAT_TRACE_DIAGNOSTIC 1\nstatic double clock_value=1;\n#define TAS_CHAT_TRACE_NOW() clock_value\n#include "TASChatTrace.c"\nvoid advance(double x){clock_value=x;}\n')
        lib=Path(folder)/'trace.so'
        subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-I',str(ROOT/'src'),str(path),'-pthread','-lm','-o',str(lib)],check=True)
        dll=ctypes.CDLL(str(lib));dll.tas_chat_trace_packet.argtypes=[ctypes.c_char_p];dll.tas_chat_trace_packet.restype=ctypes.c_bool
        dll.tas_chat_trace_status.argtypes=[ctypes.c_void_p,ctypes.c_size_t];dll.advance.argtypes=[ctypes.c_double]
        return dll
    def test_numeric_schema_rejects_text_and_malformed_packets(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder)
            bad=[b'',b'[',b'[]',b'[0,1,0,0,0,0,0',b'[0,1,0,0,0,0,0,0,0,0]x',b'[0,1,0,0,0,0,0,0,0]',b'[0,1,0,0,"secret",0,0,0,0,0]',b'[0,1,0,0,NaN,0,0,0,0,0]',b'[0,1,0,0,01,0,0,0,0,0]',b'[0,0,0,0,0,0,0,0,0,0]',b'[0,1,10000001,0,0,0,0,0,0,0]',b'[9,1,1,0,-1,0,0,0,0,0]',b'[13,1,0,0,1.5,0,0,0,0,0]']
            for packet in bad:
                with self.subTest(packet=packet):self.assertFalse(lib.tas_chat_trace_packet(packet))
            self.assertTrue(lib.tas_chat_trace_packet(b'[0,1,0,0,1,0,0,0,1,0]'))
            self.assertTrue(lib.tas_chat_trace_packet(b'[6,1,1,3,44,100,0,-1.5e2,1,0]'))
            out=ctypes.create_string_buffer(32768);lib.tas_chat_trace_status(out,len(out));self.assertIn(b's1 m1',out.value);self.assertNotIn(b'secret',out.value)
            for n in (1,2,32,256):lib.tas_chat_trace_status(ctypes.create_string_buffer(n),n)
    def test_native_ring_rate_limit_and_long_running_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder)
            self.assertTrue(lib.tas_chat_trace_packet(b'[9,1,1,1,1,0,0,0,1,0]'))
            for i in range(3000):
                lib.advance(i+2)
                self.assertTrue(lib.tas_chat_trace_packet(f'[6,1,{i+2},0,44,100,0,0,1,0]'.encode()))
            lib.advance(5000);self.assertTrue(lib.tas_chat_trace_packet(b'[2,5,3001,1,1,0,0,0,2,0]'))
            out=ctypes.create_string_buffer(32768);lib.tas_chat_trace_status(out,len(out))
            self.assertIn(b'Retained: 2048/2048',out.value);self.assertIn(b'overwrites=954',out.value)
            self.assertIn(b's5 m3001',out.value);self.assertIn(b'e=9 s=1 m=1',out.value);self.assertIn(b'Running elapsed: 4999',out.value)
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder)
            for i in range(64):self.assertTrue(lib.tas_chat_trace_packet(b'[10,1,0,0,1,0,0,0,1,0]'))
            self.assertFalse(lib.tas_chat_trace_packet(b'[10,1,0,0,1,0,0,0,1,0]'))
            self.assertTrue(lib.tas_chat_trace_packet(b'[9,1,1,0,1,0,0,0,1,0]'))
            lib.advance(10000);self.assertTrue(lib.tas_chat_trace_packet(b'[10,1,0,0,1,0,0,0,1,0]'))
    def test_geometry_is_not_combined_across_frames_or_reopen_cycles(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder);out=ctypes.create_string_buffer(32768)
            for packet in (b'[14,1,0,0,1,1,0,0,1,7]',b'[8,1,0,0,0,0,400,800,1,7]',b'[7,1,1,0,0,500,100,40,1,7]'):
                self.assertTrue(lib.tas_chat_trace_packet(packet))
            lib.tas_chat_trace_status(out,len(out));self.assertIn(b'visibility=vertical-overlap',out.value)
            lib.advance(10);self.assertTrue(lib.tas_chat_trace_packet(b'[14,1,0,0,1,1,0,0,1,8]'))
            lib.tas_chat_trace_status(out,len(out));self.assertNotIn(b'visibility=vertical-overlap',out.value)
            for packet in (b'[14,1,0,0,1,1,0,0,2,7]',b'[8,1,0,0,0,0,400,800,2,7]',b'[4,1,1,0,1,0,0,0,2,0]'):
                self.assertTrue(lib.tas_chat_trace_packet(packet))
            lib.tas_chat_trace_status(out,len(out));self.assertIn(b'm1 cycle=1',out.value);self.assertIn(b'm1 cycle=2',out.value)
            self.assertNotIn(b'visibility=vertical-overlap',out.value);self.assertIn(b'local=unobserved',out.value)
    @unittest.skipUnless(shutil.which('node'),'Node required for host React mock')
    def test_scoped_observer_preserves_behavior_and_privacy(self):
        script="global._runtimeGlobal=global;\n"+(ROOT/'src/rn/ChatTrace.js').read_text()+(ROOT/'tests/fixtures/chat_trace_exercise.js').read_text()
        subprocess.run(['node','-e',script],check=True)
    @unittest.skipUnless(shutil.which('node'),'Node required for host React mock')
    def test_js_rolling_capture_late_reopen_rotating_labels_and_rate_caps(self):
        prefix=(ROOT/'tests/fixtures/chat_trace_exercise.js').read_text().split('var original=')[0]
        script="global._runtimeGlobal=global;\n"+(ROOT/'src/rn/ChatTrace.js').read_text()+prefix+(ROOT/'tests/fixtures/chat_trace_limits.js').read_text()
        subprocess.run(['node','-e',script],check=True)
    @unittest.skipUnless(shutil.which('node'),'Node required for host React mock')
    def test_redemption_routes_store_catalog_null_and_list_container(self):
        prefix=(ROOT/'tests/fixtures/chat_trace_exercise.js').read_text().split('var original=')[0]
        script="global._runtimeGlobal=global;\n"+(ROOT/'src/rn/ChatTrace.js').read_text()+prefix+(ROOT/'tests/fixtures/chat_trace_rewards.js').read_text()
        subprocess.run(['node','-e',script],check=True)
    def test_target_schema_and_report_preserve_unknown_and_zero_measurements(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder);out=ctypes.create_string_buffer(65536)
            for p in ('[17,1,1,64,3,1,0,0,1,0]','[18,1,1,64,4,1,1,0,1,0]',
                      '[19,1,1,64,-1,40,1,1,1,7]','[21,1,1,64,2,5,4,0,1,0]','[22,1,0,0,2,1,1,1,1,0]'):
                self.assertFalse(lib.tas_chat_trace_packet(p.encode()))
            for p in ('[17,1,1,64,2,1,0,0,1,0]','[18,1,1,64,1,1,1,0,1,0]',
                      '[21,1,1,64,2,1,1,0,1,0]','[19,1,1,64,60,40,1,1,1,7]',
                      '[20,1,1,64,0,140,400,60,1,7]'):
                self.assertTrue(lib.tas_chat_trace_packet(p.encode()))
            lib.tas_chat_trace_status(out,len(out));text=out.value
            self.assertIn(b'route=2 phase=1 store=2',text);self.assertIn(b'catalog=1 render=1',text)
            self.assertIn(b'list-known=1 size/position=60.00/40.00',text)
            self.assertIn(b'cell=measured y/h=140.00/60.00 frame=7',text)
            for p in ('[19,1,1,64,-1,40,0,1,1,8]','[20,1,1,64,0,140,400,0,1,8]'):
                self.assertTrue(lib.tas_chat_trace_packet(p.encode()))
            lib.tas_chat_trace_status(out,len(out))
            self.assertIn(b'list-known=0 size/position=-1.00/40.00',out.value)
            self.assertIn(b'cell=measured y/h=140.00/0.00 frame=8',out.value)
    def test_target_lifecycle_cannot_starve_own_priority_and_tail_survives_rotation(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder);out=ctypes.create_string_buffer(65536)
            for i in range(16):self.assertTrue(lib.tas_chat_trace_packet(b'[17,1,1,64,2,1,0,0,1,0]'))
            self.assertFalse(lib.tas_chat_trace_packet(b'[17,1,1,64,2,1,0,0,1,0]'))
            self.assertTrue(lib.tas_chat_trace_packet(b'[2,1,2,1,1,0,0,0,1,0]'))
            for i in range(2200):
                lib.advance(i+2);self.assertTrue(lib.tas_chat_trace_packet(b'[10,1,0,0,1,1,0,0,1,0]'))
            lib.tas_chat_trace_status(out,len(out))
            self.assertIn(b'Retained: 2048/2048',out.value);self.assertIn(b'Target tail: 16/512',out.value)
            self.assertIn(b'e=17 s=1 m=1',out.value);self.assertIn(b'e=2 s=1 m=2 flags=1',out.value)
