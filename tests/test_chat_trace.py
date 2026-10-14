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
            value={'passed':True,'factory_executed':True,'inputs':fingerprints(),'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA}
            path.write_text(json.dumps(value));check_gate(path)
            for field,bad in (('passed',False),('factory_executed',False),('inputs',{}),('runtime_commit','wrong'),('donor_sha256','wrong')):
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
            bad=[b'',b'[',b'[]',b'[0,1,0,0,0,0,0',b'[0,1,0,0,0,0,0,0]x',b'[0,1,0,0,0,0,0,0,0]',b'[0,1,0,0,"secret",0,0,0]',b'[0,1,0,0,NaN,0,0,0]',b'[0,1,0,0,01,0,0,0]',b'[0,3,0,0,0,0,0,0]',b'[0,1,257,0,0,0,0,0]',b'[9,1,1,0,-1,0,0,0]',b'[11,1,0,0,1.5,0,0,0]']
            for packet in bad:
                with self.subTest(packet=packet):self.assertFalse(lib.tas_chat_trace_packet(packet))
            self.assertTrue(lib.tas_chat_trace_packet(b'[0,1,0,0,1,0,0,0]'))
            self.assertTrue(lib.tas_chat_trace_packet(b'[6,1,1,3,44,100,0,-1.5e2]'))
            out=ctypes.create_string_buffer(24576);lib.tas_chat_trace_status(out,len(out));self.assertIn(b's1 m1',out.value);self.assertNotIn(b'secret',out.value)
            for n in (1,2,32,256):lib.tas_chat_trace_status(ctypes.create_string_buffer(n),n)
    def test_native_limits_and_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder)
            self.assertTrue(lib.tas_chat_trace_packet(b'[0,1,0,0,1,0,0,0]'))
            self.assertTrue(lib.tas_chat_trace_packet(b'[11,1,0,0,1,0,0,0]'))
            self.assertFalse(lib.tas_chat_trace_packet(b'[6,1,1,0,44,100,0,0]'))
            self.assertTrue(lib.tas_chat_trace_packet(b'[0,2,0,0,1,0,0,0]'))
            lib.advance(132);self.assertFalse(lib.tas_chat_trace_packet(b'[10,2,0,0,1,0,0,0]'))
        with tempfile.TemporaryDirectory() as folder:
            lib=self.native(folder)
            for i in range(1536):self.assertTrue(lib.tas_chat_trace_packet(b'[10,1,0,0,1,0,0,0]'))
            self.assertFalse(lib.tas_chat_trace_packet(b'[10,1,0,0,1,0,0,0]'))
    @unittest.skipUnless(shutil.which('node'),'Node required for host React mock')
    def test_scoped_observer_preserves_behavior_and_privacy(self):
        script="global._runtimeGlobal=global;\n"+(ROOT/'src/rn/ChatTrace.js').read_text()+(ROOT/'tests/fixtures/chat_trace_exercise.js').read_text()
        subprocess.run(['node','-e',script],check=True)
    @unittest.skipUnless(shutil.which('node'),'Node required for host React mock')
    def test_js_packet_label_and_session_caps(self):
        prefix=(ROOT/'tests/fixtures/chat_trace_exercise.js').read_text().split('var original=')[0]
        script="global._runtimeGlobal=global;\n"+(ROOT/'src/rn/ChatTrace.js').read_text()+prefix+(ROOT/'tests/fixtures/chat_trace_limits.js').read_text()
        subprocess.run(['node','-e',script],check=True)
