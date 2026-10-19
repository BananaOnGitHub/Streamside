"""Production native parser, pinned trust and asynchronous coordinator contracts."""
import copy
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
MANIFEST=ROOT/'diagnostics/investigations/rn-chat-gaps/1.json'
class Manifest(C.Structure):
    _fields_=[('version',C.c_uint32),('capabilities',C.c_uint32),('events',C.c_uint32),('limits',C.c_uint32*14),('return_armed',C.c_bool),('title',C.c_char*65),('description',C.c_char*257)]
class Donor(C.Structure):
    _fields_=[(x,C.c_char_p) for x in ['version','build','main_uuid','main_text_sha256','hermes_uuid','hermes_text_sha256','hbc_sha256']]+[('hbc_version',C.c_uint32),('hbc_bytes',C.c_uint32)]
class Command(C.Structure):
    _fields_=[('operation',C.c_uint32),('generation',C.c_uint32),('sequence',C.c_uint32),('manifest',Manifest)]
class Status(C.Structure):
    _fields_=[(x,C.c_uint32) for x in ['state','reason','generation','sequence','pending','registry_source','ready_capabilities']]+[('deadline_ms',C.c_uint64)]
SHA=C.CFUNCTYPE(C.c_bool,C.c_void_p,C.c_size_t,C.c_void_p)
def donor():
    inventory=json.loads((ROOT/'docs/investigations/TWITCH_31_6_HOTFIX_INVENTORY.json').read_text())['donors']['31.6.2']
    native=inventory['binaries']['Twitch'];hermes=inventory['binaries']['Frameworks/hermesvm.framework/hermesvm']
    return Donor(*[x.encode() for x in ['31.6.2',inventory['info']['CFBundleVersion'],native['uuid'],native['text_sha256'],hermes['uuid'],hermes['text_sha256'],inventory['bundle_sha256']]],98,inventory['bundle_bytes'])

class InvestigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();lib=Path(cls.folder.name)/'inv.so'
        subprocess.run(['cc','-std=c11','-shared','-fPIC','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'src'),str(ROOT/'src/TASInvestigation.c'),'-o',str(lib)],check=True)
        cls.lib=C.CDLL(str(lib));l=cls.lib
        l.tas_inv_parse.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Manifest)];l.tas_inv_parse.restype=C.c_bool
        l.tas_inv_registry.argtypes=[C.c_void_p,C.c_size_t,SHA,C.POINTER(Manifest),C.POINTER(C.c_uint)];l.tas_inv_registry.restype=C.c_bool
        l.tas_inv_initialize.argtypes=[SHA];l.tas_inv_initialize.restype=C.c_bool
        l.tas_inv_donor_matches.argtypes=[C.POINTER(Donor)];l.tas_inv_donor_matches.restype=C.c_bool
        l.tas_inv_admit.argtypes=[C.POINTER(Donor),C.c_uint32,C.c_uint32];l.tas_inv_admit.restype=C.c_bool
        l.tas_inv_status.restype=Status
        l.tas_inv_begin.argtypes=[C.c_uint,C.c_uint64,C.POINTER(Command)];l.tas_inv_begin.restype=C.c_bool
        l.tas_inv_ack.argtypes=[C.c_uint32,C.c_uint32,C.c_uint,C.c_bool];l.tas_inv_ack.restype=C.c_bool
        l.tas_inv_expire.argtypes=[C.c_uint64];l.tas_inv_expire.restype=C.c_bool
        l.tas_inv_invalidate.argtypes=[C.c_uint]
        @SHA
        def sha(data,n,out):
            C.memmove(out,hashlib.sha256(C.string_at(data,n)).digest(),32);return True
        cls.sha=sha
        cls.raw=MANIFEST.read_bytes();cls.default=json.loads(cls.raw)
    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()
    def setUp(self):
        self.lib.tas_inv_invalidate(4)
        self.assertTrue(self.lib.tas_inv_initialize(self.sha))
    def parse(self,obj):
        raw=obj if isinstance(obj,bytes) else json.dumps(obj,ensure_ascii=False).encode()
        result=Manifest();ok=self.lib.tas_inv_parse(raw,len(raw),C.byref(result))
        if not ok:self.assertEqual(bytes(result),bytes(Manifest()))
        return ok,result
    def admitted(self):self.assertTrue(self.lib.tas_inv_admit(C.byref(donor()),7,1))
    def begin(self,op,now=100):
        cmd=Command();self.assertTrue(self.lib.tas_inv_begin(op,now,C.byref(cmd)));return cmd
    def ack(self,cmd,ok=True):self.assertTrue(self.lib.tas_inv_ack(cmd.generation,cmd.sequence,cmd.operation,ok))
    def test_valid_manifest_and_narrower_limits_event_selection(self):
        ok,m=self.parse(self.raw);self.assertTrue(ok);self.assertEqual((m.capabilities,m.events),(7,1023));self.assertTrue(m.return_armed)
        smaller=copy.deepcopy(self.default);smaller['capabilities'].pop();smaller['sampling']['events']=['emission','list'];smaller['activation']['after_capture']='dormant'
        smaller['limits']={k:1 for k in smaller['limits']};smaller['report']['max_bytes']=1
        ok,m=self.parse(smaller);self.assertTrue(ok);self.assertEqual((m.capabilities,m.events),(3,258));self.assertFalse(m.return_armed)
    def test_unknown_duplicate_escaped_duplicate_and_executable_fields_rejected(self):
        for name in ['javascript','selectors','function_id','offset','property_path','url','endpoint','fields']:
            obj=copy.deepcopy(self.default);obj[name]='unsafe';self.assertFalse(self.parse(obj)[0],name)
        for location in ['limits','activation','sampling','report','streamside']:
            obj=copy.deepcopy(self.default);obj[location]['unexpected']=1;self.assertFalse(self.parse(obj)[0],location)
        for prefix in [b'{"id":"rn-chat-gaps",',b'{"\\u0069d":"rn-chat-gaps",']:
            self.assertFalse(self.parse(prefix+self.raw.lstrip()[1:])[0])
        raw=self.raw.replace(b'"max_lists": 2',b'"max_lists": 2, "max_lists": 1');self.assertFalse(self.parse(raw)[0])
    def test_all_compiled_limits_enforced_and_numeric_types_are_exact(self):
        for name,value in self.default['limits'].items():
            for bad in [value+1,0,-1,True,1.0,'1',None,4294967296]:
                obj=copy.deepcopy(self.default);obj['limits'][name]=bad
                with self.subTest(name=name,bad=bad):self.assertFalse(self.parse(obj)[0])
        for spelling in [b'2e0',b'2.0',b'02',b'+2',b'NaN',b'Infinity']:
            self.assertFalse(self.parse(self.raw.replace(b'"max_lists": 2',b'"max_lists": '+spelling))[0])
    def test_wrong_versions_profiles_capabilities_and_sampling_refused(self):
        for section,key,bad in [('streamside','runtime_abi',2),('snapshot','profile','arbitrary.path'),('sampling','periodic_hz',1),('sampling','mode','periodic'),('activation','requires_restart',True),('report','profile','raw-chat')]:
            obj=copy.deepcopy(self.default);obj[section][key]=bad;self.assertFalse(self.parse(obj)[0])
        for key,bad in [('version','31.6.1'),('bundle_build','262821841498166537'),('hermes_version',99),('native_profile','unknown'),('original_hbc_sha256','0'*64)]:
            obj=copy.deepcopy(self.default);obj['donors'][0][key]=bad;self.assertFalse(self.parse(obj)[0])
        for version in [0,2,True]:
            obj=copy.deepcopy(self.default);obj['capabilities'][0]['version']=version;self.assertFalse(self.parse(obj)[0])
        obj=copy.deepcopy(self.default);obj['capabilities'].pop();self.assertFalse(self.parse(obj)[0])
        obj=copy.deepcopy(self.default);obj['capabilities'].append(obj['capabilities'][0]);self.assertFalse(self.parse(obj)[0])
    def test_utf8_escapes_depth_size_and_every_truncation(self):
        obj=copy.deepcopy(self.default);obj['description']='Unicode \N{SNOWMAN} \N{GRINNING FACE}'
        self.assertTrue(self.parse(obj)[0]);self.assertTrue(self.parse(json.dumps(obj).encode())[0])
        for raw in [self.raw+b'x',self.raw.replace(b'RN chat gaps',b'\xff'),b'['*10+b'0'+b']'*10,b' '*16385,self.raw.replace(b'RN chat gaps',b'\\uD800'),self.raw.replace(b'RN chat gaps',b'\\u0000')]:self.assertFalse(self.parse(raw)[0])
        for n in range(len(self.raw.rstrip())):self.assertFalse(self.parse(self.raw[:n])[0],n)
    def test_pinned_integrity_cache_fallback_and_crypto_failure(self):
        for raw,expected in [(None,0),(self.raw,1),(self.raw+b' ',2),(b'{broken',2)]:
            out=Manifest();source=C.c_uint();self.assertTrue(self.lib.tas_inv_registry(raw,len(raw or b''),self.sha,C.byref(out),C.byref(source)));self.assertEqual(source.value,expected)
        @SHA
        def broken(data,n,out):return False
        out=Manifest();source=C.c_uint();self.assertFalse(self.lib.tas_inv_registry(None,0,broken,C.byref(out),C.byref(source)))
    def test_native_and_hermes_admission_require_all_exact_identities(self):
        valid=donor();self.assertTrue(self.lib.tas_inv_donor_matches(C.byref(valid)))
        for name,kind in Donor._fields_:
            changed=donor();setattr(changed,name,b'wrong' if kind==C.c_char_p else 1)
            self.assertFalse(self.lib.tas_inv_donor_matches(C.byref(changed)),name)
        self.assertFalse(self.lib.tas_inv_admit(C.byref(valid),0,1));self.assertFalse(self.lib.tas_inv_admit(C.byref(valid),1,1));self.assertFalse(self.lib.tas_inv_admit(C.byref(valid),7,0))
    def test_unavailable_runtime_cannot_arm_and_admission_stays_dormant(self):
        self.assertFalse(self.lib.tas_inv_begin(1,0,C.byref(Command())))
        self.admitted();self.assertEqual(self.lib.tas_inv_status().state,1)
        self.assertFalse(self.lib.tas_inv_ack(self.lib.tas_inv_status().generation,0,0,True))
    def test_ack_required_busy_late_activation_and_no_armed_expiration(self):
        self.admitted();cmd=self.begin(1,10**9);self.assertEqual(self.lib.tas_inv_status().state,1)
        self.assertFalse(self.lib.tas_inv_begin(1,10**9,C.byref(Command())));self.ack(cmd)
        self.assertEqual(self.lib.tas_inv_status().state,2);self.assertFalse(self.lib.tas_inv_expire(10**12));self.assertEqual(self.lib.tas_inv_status().state,2)
    def test_capture_returns_armed_and_disarm_invalidates_pending_callbacks(self):
        self.admitted();self.ack(self.begin(1));capture=self.begin(2);self.assertEqual(self.lib.tas_inv_status().state,3)
        self.ack(capture);self.assertEqual(self.lib.tas_inv_status().state,2)
        capture=self.begin(2);stop=self.begin(3);self.assertEqual(self.lib.tas_inv_status().state,1)
        self.assertFalse(self.lib.tas_inv_ack(capture.generation,capture.sequence,capture.operation,True));self.ack(stop)
        for _ in range(100):self.ack(self.begin(1));self.ack(self.begin(2));self.ack(self.begin(3))
    def test_failed_or_expired_commands_invalidate_generation_and_require_readmission(self):
        self.admitted();cmd=self.begin(1,100);self.assertFalse(self.lib.tas_inv_expire(2099));self.assertTrue(self.lib.tas_inv_expire(2100))
        self.assertFalse(self.lib.tas_inv_ack(cmd.generation,cmd.sequence,cmd.operation,True));self.assertEqual(self.lib.tas_inv_status().state,0)
        self.admitted();cmd=self.begin(1);self.ack(cmd,False);self.assertEqual(self.lib.tas_inv_status().state,0)
        self.admitted();cmd=self.begin(1);self.lib.tas_inv_invalidate(3);self.assertFalse(self.lib.tas_inv_ack(cmd.generation,cmd.sequence,cmd.operation,True))
    def test_generated_registry_is_current(self):
        subprocess.run(['python3',str(ROOT/'tools/generate_investigation_registry.py'),'--check'],check=True)
