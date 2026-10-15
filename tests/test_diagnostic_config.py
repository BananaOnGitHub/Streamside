"""Production policy/export/preferences with host Foundation adapters, not UIKit."""
import ctypes
import ast
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def function(source,name):
    start=source.index(name+'(')
    start=source.rfind('\n',0,start)+1
    brace=source.index('{',start); depth=1; end=brace+1
    # All selected functions have balanced brace literals.
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]+'\n'

class DiagnosticConfigurationTests(unittest.TestCase):
    def policy(self,folder):
        lib=Path(folder)/'policy.so'
        subprocess.run(['cc','-shared','-fPIC','-pthread','-I',str(ROOT/'src'),str(ROOT/'src/TASDiagnosticPolicy.c'),'-o',str(lib)],check=True)
        dll=ctypes.CDLL(str(lib))
        dll.tas_diag_events_report.argtypes=[ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
        dll.tas_diag_event_store.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_char_p,ctypes.c_char_p]
        return dll
    def test_presets_defaults_validation_and_independent_categories(self):
        with tempfile.TemporaryDirectory() as f:
            p=self.policy(f)
            self.assertEqual(p.tas_diag_policy_word(),1)
            for i,w in enumerate([1,259,285,289]):
                self.assertEqual(p.tas_diag_preset_word(i),w)
                self.assertEqual(p.tas_diag_preset_for(w),i)
            self.assertEqual(p.tas_diag_config_normalize(0xffffffff),1)
            self.assertEqual(p.tas_diag_config_normalize(256|8),264)
            self.assertEqual(p.tas_diag_preset_for(264),4)
            self.assertEqual(p.tas_diag_preset_for(513),4)
    def test_disabled_collection_does_not_dereference_or_retain_details(self):
        with tempfile.TemporaryDirectory() as f:
            p=self.policy(f);b=ctypes.create_string_buffer(8192)
            p.tas_diag_event_store(1,1,b'HLS_REQUEST',ctypes.cast(1,ctypes.c_char_p))
            p.tas_diag_policy_initialize(259);p.tas_diag_events_report(1,b,len(b))
            self.assertIn(b'accepted=0',b.value)
            p.tas_diag_events_clear();p.tas_diag_policy_initialize(3)
            p.tas_diag_event_store(1,1,b'HLS_REQUEST',b'unrecorded')
            p.tas_diag_event_store(1,0,b'TOKEN_FAILURE',b'count=1')
            p.tas_diag_events_report(1,b,len(b))
            self.assertIn(b'accepted=1',b.value);self.assertNotIn(b'HLS_REQUEST',b.value)
            self.assertIn(b'TOKEN_FAILURE',b.value)
    def test_category_rings_overwrite_export_limits_and_truncation(self):
        with tempfile.TemporaryDirectory() as f:
            p=self.policy(f);p.tas_diag_policy_initialize(319);b=ctypes.create_string_buffer(8192)
            p.tas_diag_event_store(5,1,b'CHAT_EVIDENCE',b'flags=1')
            for i in range(200):p.tas_diag_event_store(1,1,b'HLS_REQUEST',str(i).encode())
            p.tas_diag_events_report(5,b,len(b));self.assertIn(b'CHAT_EVIDENCE',b.value)
            self.assertIn(b'overwritten=0',b.value)
            p.tas_diag_events_report(1,b,len(b));self.assertIn(b'overwritten=152',b.value)
            self.assertIn(b'export-omitted=36',b.value);self.assertEqual(b.value.count(b'HLS_REQUEST'),12)
            p.tas_diag_event_store(1,1,b'HLS_RESPONSE',b'x'*1000)
            p.tas_diag_events_report(1,b,len(b));self.assertIn(b'shortened=1',b.value)
            small=ctypes.create_string_buffer(128);p.tas_diag_events_report(1,small,len(small))
            self.assertIn(b'export truncated',small.value)
            p.tas_diag_events_clear();p.tas_diag_events_report(1,b,len(b));self.assertIn(b'accepted=0',b.value)
    def test_settings_save_launch_apply_and_actual_report_category_routing(self):
        source=(ROOT/'src/TASDiagnostics.c').read_text()
        selected='\n'.join(function(source,n) for n in ['saved_diagnostic_config','tas_diagnostics_load_preferences','save_diagnostic_config','tas_diag_metric','tas_diag_log','tas_diag_log_url','tas_diag_log_stream','report_append','diagnostic_report_create'])
        prelude=r'''
#include "TASDiagnostics.h"
#include "TASPrivacy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
typedef const char *SEL;typedef long NSInteger;typedef void *id;
#define TAS_REPORT_VERSION "test-build"
#define nil NULL
static pthread_mutex_t g_diag_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t g_metrics[TAS_DIAG_METRIC_COUNT];
static unsigned saved;static int exists;
static char report[131072];static int called[6];
static id defaults(void){return (id)2;}
static id nsstr(const char *s){return (id)s;}
static const char *utf8(id o){return o;}
static SEL sel_registerName(const char *s){return s;}
static void preference_set(id o,SEL s,NSInteger v,id key){(void)o;(void)s;assert(!strcmp(key,TAS_DIAG_CONFIG_KEY));saved=(unsigned)v;exists=1;}
#define objc_msgSend preference_set
static id objc_getClass(const char *s){return (id)s;}
static id objc_retain(id o){return o;}
static id msg0(id o,const char *s){(void)s;return o;}
static id msg1(id o,const char *s,id value){
 if(!strcmp(s,"objectForKey:"))return exists==1?(id)&saved:exists==2?(id)17:nil;
 if(!strcmp(s,"stringWithString:")){snprintf(report,sizeof(report),"%s",(char *)value);return report;}
 if(!strcmp(s,"objectForInfoDictionaryKey:"))return (id)"donor-build";
 return o;
}
static NSInteger imsg0(id o,const char *s){(void)s;return *(unsigned *)o;}
static int bmsg1(id o,const char *s,id cls){(void)s;(void)cls;return o==&saved;}
static void vmsg1(id o,const char *s,id v){assert(o==report && !strcmp(s,"appendString:"));strncat(report,v,sizeof(report)-strlen(report)-1);}
#define MENU_GET(v) (v)
static uint64_t g_reload_actions_added,g_native_reload_button_taps;static int g_native_action_sheet_hooked;
static void tas_emotes_status_category(unsigned c,char *b,size_t n){called[c]++;snprintf(b,n,"category=%u\n",c);}
static void tas_image_transport_status(char *b,size_t n){called[3]++;snprintf(b,n,"transport-summary\n");}
static void tas_emote_ui_status(char *b,size_t n){snprintf(b,n,"render-summary\n");}
static void ss_composer_status(char *b,size_t n){snprintf(b,n,"composer-summary\n");}
static void tas_rn_composer_ui_status(char *b,size_t n){snprintf(b,n,"rn-composer-summary\n");}
static void ss_legacy_palette_status(char *b,size_t n){snprintf(b,n,"palette-detail\n");}
static void tas_demand_status(char *b,size_t n){snprintf(b,n,"demand-detail\n");}
static void tas_emote_probe_status(char *b,size_t n){snprintf(b,n,"emote-detail\n");}
static void tas_image_probe_status(char *b,size_t n){snprintf(b,n,"decoder-detail\n");}
'''
        main=r'''
int main(void){
 exists=2;tas_diagnostics_load_preferences();assert(tas_diag_policy_word()==1);exists=0;
 tas_diagnostics_load_preferences();assert(tas_diag_policy_word()==1);
 save_diagnostic_config(289);assert(saved==289 && tas_diag_policy_word()==1);
 char *r=diagnostic_report_create();assert(strstr(r,"RELAUNCH REQUIRED"));
 assert(!strstr(r,"--- Playback") && !strstr(r,"--- Chat"));
 tas_diagnostics_load_preferences();assert(tas_diag_policy_word()==289);
 tas_diag_log_url("HLS_REQUEST","https://private.example/secret?token=secret","bytes=7");
 tas_diag_log_stream("RN_CHAT_EVENT","privateStreamer","https://example/secret","flags=1");
 r=diagnostic_report_create();assert(strstr(r,"--- Chat / Redemptions ---"));
 assert(!strstr(r,"--- Playback") && !strstr(r,"--- Image Transport"));
 assert(called[3]==0 && called[2]==0 && called[4]==0);
 assert(!strstr(r,"privateStreamer") && !strstr(r,"secret"));
 save_diagnostic_config(259);tas_diagnostics_load_preferences();r=diagnostic_report_create();
 assert(strstr(r,"HLS intercepted:") && !strstr(r,"HLS_REQUEST"));
 for(unsigned c=0;c<6;c++){
  save_diagnostic_config(256|(1U<<c));tas_diagnostics_load_preferences();memset(called,0,sizeof(called));
  r=diagnostic_report_create();for(unsigned j=0;j<6;j++)if(j!=c)assert(called[j]==0);
 }
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'export.c';path.write_text(prelude+selected+main)
            for compiled in [0,1]:
                binary=Path(f)/('export'+str(compiled))
                subprocess.run(['cc','-I',str(ROOT/'src'),'-DTAS_EMOTE_DIAGNOSTIC='+str(compiled),'-DTAS_IMAGE_DEMAND_DIAGNOSTIC='+str(compiled),'-DTAS_CHAT_TRACE_DIAGNOSTIC=0',str(path),str(ROOT/'src/TASDiagnosticPolicy.c'),str(ROOT/'src/TASPrivacy.c'),'-pthread','-o',str(binary)],check=True)
                subprocess.run([str(binary)],check=True)
    def test_playback_protocol_still_intercepts_and_completes_with_logging_disabled(self):
        import test_protocol
        prelude=test_protocol.PRELUDE+'\n#include "TASDiagnosticPolicy.h"\nunsigned tas_diag_policy_word(void){return 1;}\n'
        test_protocol.ProtocolTests().run_transport(False,prelude_override=prelude)

    def test_disabled_demand_probe_never_reads_requests_or_installs_native_hooks(self):
        tree=ast.parse((ROOT/'tests/test_image_demand.py').read_text())
        prelude=next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prelude' for t in n.targets))
        source=(ROOT/'src/TASImageDemand.c').read_text().replace('#include <objc/runtime.h>','').replace('#include <objc/message.h>','')
        main=r'''
int main(void){
 assert(!tas_demand_snapshot((const char *)1,1));
 tas_demand_request((void *)1,1);tas_demand_mark_url((void *)1,1);
 tas_demand_event(1,1,(const char *)1,0,0);sample((id)1,false);
 tas_demand_install();assert(!move_original && !layout_original);
 assert(tas_demand_delegate()==NULL && events[1][1]==0 && unique_assets==0);
 tas_diag_policy_initialize(272);tas_demand_event(1,1,"https://private/secret",0,0);
 assert(events[1][1]==1 && unique_assets==1);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'demand.c';path.write_text(prelude+source+main);binary=Path(f)/'demand'
            subprocess.run(['cc','-I',str(ROOT/'src'),'-DTAS_IMAGE_DEMAND_DIAGNOSTIC=1',str(path),str(ROOT/'src/TASDiagnosticPolicy.c'),'-pthread','-lm','-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)

