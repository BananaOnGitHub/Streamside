"""Launch-policy admission around the unchanged rolling observer/graft."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent

class ChatTracePolicyTests(unittest.TestCase):
    def test_disabled_and_summary_collection_return_before_packet_inspection(self):
        with tempfile.TemporaryDirectory() as f:
            lib=Path(f)/'trace-policy.so'
            subprocess.run(['cc','-shared','-fPIC','-DTAS_CHAT_TRACE_DIAGNOSTIC=1','-I',str(ROOT/'src'),str(ROOT/'src/TASChatTrace.c'),str(ROOT/'src/TASDiagnosticPolicy.c'),'-pthread','-lm','-o',str(lib)],check=True)
            p=ctypes.CDLL(str(lib));p.tas_chat_trace_packet.argtypes=[ctypes.c_char_p];p.tas_chat_trace_packet.restype=ctypes.c_bool
            p.tas_chat_trace_status.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
            self.assertFalse(p.tas_chat_trace_packet(ctypes.cast(1,ctypes.c_char_p)))
            p.tas_diag_policy_initialize(33)
            self.assertFalse(p.tas_chat_trace_packet(ctypes.cast(1,ctypes.c_char_p)))
            p.tas_diag_policy_initialize(289)
            self.assertTrue(p.tas_chat_trace_packet(b'[2,1,1,1,1,0,0,0,1,0]'))
            out=ctypes.create_string_buffer(65536);p.tas_chat_trace_status(out,len(out))
            self.assertIn(b'lifetime accepted/schema-refused/rate-limited: 1/0/0',out.value)
            self.assertIn(b'e=2 s=1 m=1 flags=1',out.value)

    def test_production_module_registers_only_selected_diagnostic_bridges(self):
        from test_rn_incoming import HARNESS,RUNTIME
        source='static unsigned trace_methods,demand_methods;\n'+HARNESS
        source=source.replace('    else {\n        assert(cls==local_meta);',r'''
    else if(!strcmp(selector,"trace:")){assert(cls==local_allocated_class && imp==(IMP)rn_chat_trace);trace_methods++;}
    else if(!strcmp(selector,"observe:scope:asset:a:b:")){assert(cls==local_allocated_class && imp==(IMP)rn_demand_observe);demand_methods++;}
    else {
        assert(cls==local_meta);''')
        source=source.replace('        else if(!strcmp(selector,"__rct_export__streamsideComposer"))',r'''
        else if(!strcmp(selector,"__rct_export__streamsideChatTrace")){assert(imp==(IMP)rn_chat_trace_export);trace_methods++;}
        else if(!strcmp(selector,"__rct_export__streamsideDemand")){assert(imp==(IMP)rn_demand_export);demand_methods++;}
        else if(!strcmp(selector,"__rct_export__streamsideComposer"))''')
        source=source.replace('static void local_registration(void) {',r'''
static void local_registration(void) {
    tas_diag_policy_initialize((unsigned)strtoul(getenv("TAS_TEST_DIAGNOSTIC_WORD"),NULL,10));''')
        source=source.replace('    install_rn_local();assert(local_allocations==1 && local_exports==1);',r'''
    install_rn_local();assert(local_allocations==1 && local_exports==1);
    assert(trace_methods==(tas_diag_wants(TAS_DIAG_CHAT,TAS_DIAG_DETAILED)?2U:0U));
    assert(demand_methods==(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)?2U:0U));''')
        source+='''
void tas_demand_event(unsigned e,unsigned s,const char *u,double a,double b){(void)e;(void)s;(void)u;(void)a;(void)b;}
void tas_demand_mark_url(void *u,unsigned s){(void)u;(void)s;}
unsigned tas_demand_url_scope(void *u){(void)u;return 0;}
void tas_demand_install(void){}
bool tas_demand_snapshot(const char *u,double slot){(void)u;(void)slot;return true;}
'''
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);(root/'objc').mkdir()
            for name in ['runtime.h','objc.h','message.h']:
                (root/'objc'/name).write_text(RUNTIME+'\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n')
            path=root/'admission.c';path.write_text(source);binary=root/'admission'
            zig=os.environ.get('ZIG') or shutil.which('zig');self.assertTrue(zig)
            command=[zig,'cc','-fblocks','-DTAS_CHAT_TRACE_DIAGNOSTIC=1','-DTAS_IMAGE_DEMAND_DIAGNOSTIC=1','-ffunction-sections','-fdata-sections','-I',str(root),'-I',str(ROOT/'src'),str(path),str(ROOT/'src/TASChatTrace.c'),str(ROOT/'src/TASDiagnosticPolicy.c'),'-Wl,--gc-sections','-pthread','-o',str(binary)]
            built=subprocess.run(command,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr)
            for word in [1,3,259,33,289,272,319]:
                ran=subprocess.run([str(binary),'registration'],capture_output=True,text=True,env={**os.environ,'TAS_TEST_DIAGNOSTIC_WORD':str(word)})
                self.assertEqual(ran.returncode,0,str(word)+ran.stderr)

