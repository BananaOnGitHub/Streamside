"""v1 resource lifecycle, immutable provenance and export scheduling regressions.
Platform-only UIKit/RCT behavior remains subject to the device gate.
"""
from pathlib import Path
import json, os, re, shutil, subprocess, tempfile, unittest
from test_investigation_startup import function
ROOT=Path(__file__).resolve().parent.parent

def execute(source, linked=(), blocks=False):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"case.c"; exe=Path(tmp)/"case"; path.write_text(source)
        if blocks:
            zig=os.environ.get("ZIG") or str(ROOT/"build/toolchains/zig-0.14.0/zig")
            compiler=[zig,"cc","-fblocks"]
        else: compiler=["cc"]
        subprocess.run(compiler+["-std=c11","-Wall","-Wextra","-Werror","-Wno-cast-function-type",
            "-pthread","-I",str(ROOT/"src"),str(path)]+[str(ROOT/p) for p in linked]+["-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

class HardeningTests(unittest.TestCase):
    def test_production_recorder_loss_and_copied_wrapper_cycles(self):
        node=shutil.which("node")
        if not node:self.skipTest("Node.js required")
        source=(ROOT/"src/rn/Investigation.js").read_text()
        fixture=(ROOT/"tests/fixtures/investigation_bootstrap.js").read_text()
        cases=(ROOT/"tests/fixtures/investigation_hardening.js").read_text()
        # Execute the production helper at exact saturation boundaries.
        increment=re.search(r"function increment\(n\)\{[^}]+\}",source).group()
        script=fixture+"\n"+source+"\n"+cases+"\nexerciseHardening(install());\n"+increment+"\ncheck(increment(9999999)===10000000 && increment(10000000)===10000000,'counter saturation');"
        code="const vm=require('vm'),c=vm.createContext({});c._runtimeGlobal=c;c._observeNative=()=>1;vm.runInContext("+json.dumps(script)+",c);"
        subprocess.run([node,"-e",code],check=True,capture_output=True)

    def test_capture_metadata_copy_export_isolation_cancellation_and_text_ceiling(self):
        execute(r'''
#include "TASInvestigationReport.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void) {
 TASInvReportMetadata m={.available=true,.manifest_version=5,.vm_epoch=7,
  .capabilities=7,.arm_generation=2,.arm_sequence=1,.general_policy=33,
  .arm_requested_ms=100,.capture_requested_ms=200};
 strcpy(m.manifest_sha256,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
 strcpy(m.original_hbc,"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
 strcpy(m.patched_hbc,"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc");
 for(unsigned i=0;i<TAS_INV_LIMITS;i++)m.limits[i]=i+1;
 const char *p="[4,0,1,[[0,3,0,0,0,0,0,0,0],[12,3,0,0,0,3,10000000,10000000,0]]]";
 char a[65536],b[65536],small[1024];
 tas_inv_report_prepare(2,2,&m);m.manifest_version=99;m.general_policy=0;
 assert(tas_inv_report_accept(2,2,p,strlen(p),210));assert(tas_inv_report_complete(2,2));
 assert(tas_inv_report_export_begin());assert(!tas_inv_report_export_begin());
 size_t n=tas_inv_report_export_format(a,sizeof(a));assert(n && n<sizeof(a));
 assert(strstr(a,"revision=5") && strstr(a,"VM epoch=7") && strstr(a,"general-policy=33"));
 assert(strstr(a,"1,2,3,4,5") && strstr(a,"12,3,0,0,0,3,10000000,10000000,0"));
 assert(strstr(a,"counterpart")==NULL || strstr(a,"unknown")!=NULL);
 // Simulate a new lease/config, source epoch, new capture and pressure/Stop
 // while the first immutable export is in progress.
 m.vm_epoch=8;tas_inv_report_prepare(3,3,&m);
 assert(tas_inv_report_accept(3,3,p,strlen(p),310));tas_inv_report_stop(TAS_INV_MEMORY);
 assert(tas_inv_report_export_format(b,sizeof(b))==n && !strcmp(a,b));
 tas_inv_report_export_end();
 assert(tas_inv_report_format(b,sizeof(b))>0 && strstr(b,"revision=99"));
 assert(strstr(b,"interrupted=1") && strstr(b,"native stop-reason=9"));
 assert(tas_inv_report_format(small,sizeof(small))>0 && strstr(small,"EXPORT_TRUNCATED"));
 assert(tas_inv_report_available());
 assert(tas_inv_report_export_begin());tas_inv_report_export_cancel();
 assert(tas_inv_report_export_cancelled() && tas_inv_report_export_format(a,sizeof(a))==0);
 tas_inv_report_export_end();assert(tas_inv_report_format(a,sizeof(a))>0);
 assert(tas_inv_report_owned_bytes()<65536);
 // Multiple valid traversal rows cannot force an over-cap export or erase
 // useful numeric evidence: CSV is emitted before optional summary text.
 unsigned sequence=4;
 for(unsigned part=0;part<8;part++){
  char packet[8192];size_t used=(size_t)sprintf(packet,"[4,%u,%u,[",part,part==7);
  for(unsigned i=0;i<64;i++)used+=(size_t)sprintf(packet+used,"%s[%u,9999999,4,%u,0,2047,9999999,9999999,9999999]",i?",":"",!part&&!i?0:11,i+1);
  used+=(size_t)sprintf(packet+used,"]]");
  assert(tas_inv_report_accept(4,sequence,packet,used,1000+part*250));
 }
 assert(tas_inv_report_format(a,sizeof(a))>0);
 assert(strstr(a,"EXPORT_TRUNCATED") && strstr(a,"11,9999999,4,2"));
}''',["src/TASInvestigationReport.c"])

    def test_runtime_resource_events_without_page_and_acknowledged_cleanup(self):
        source=(ROOT/"src/TASInvestigationHost.c").read_text().replace("bool tas_inv_host_request(unsigned operation) {","static bool tas_inv_host_request(unsigned operation) {")
        selected="\n".join(function(source,n) for n in ["current_resource_reason","resource_stop","schedule_resource","resource_changed","memory_warning","install_resource_observers","prepare_capture","tas_inv_host_request"])
        prelude=r'''
#include "TASInvestigation.h"
#include "TASInvestigationReport.h"
#include "TASInvestigationRegistry.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
typedef void *id;typedef const char *SEL;typedef unsigned char BOOL;
#define nil ((id)0)
static pthread_mutex_t host_lock=PTHREAD_MUTEX_INITIALIZER;
static id target=(id)1;
static bool resource_observers_ready,pong=true,on_main=true,delivery=true;
static unsigned resource_pending,resource_queued,source_epoch=7,arm_generation,arm_sequence;
static unsigned queued,subscriptions,invocations,last_op,last_g,last_s;
static uint64_t last_capture,arm_requested_ms,time_ms=100;
static char patched_hbc[65],fingerprints[8][65];
static void *block;
void *_NSConcreteGlobalBlock[32];
struct Block {void *isa;int flags,reserved;void(*invoke)(void *);};
static SEL sel_registerName(const char *s){return s;}
static id objc_getClass(const char *s){return (id)s;}
static uintptr_t send(id o,SEL s,...){
 (void)o;va_list a;va_start(a,s);uintptr_t result=1;
 if(!strcmp(s,"isMainThread")) result=on_main;
 else if(!strcmp(s,"applicationState")) {extern long app_state;result=(uintptr_t)app_state;}
 else if(!strcmp(s,"thermalState")) {extern long thermal;result=(uintptr_t)thermal;}
 else if(!strcmp(s,"addOperationWithBlock:")) {assert(!block);block=va_arg(a,id);queued++;}
 else if(!strcmp(s,"addObserver:selector:name:object:"))subscriptions++;
 va_end(a);return result;
}
static uintptr_t (*objc_msgSend)(id,SEL,...)=send;
static id m0(id o,const char *s){return (id)send(o,s);}
static id m1(id o,const char *s,id a){return (id)send(o,s,a);}
static id ns(const char *s){return (id)s;}
static bool is_supported(void){return true;}
static void schedule_timer(void){}
static bool invoke(unsigned op,unsigned g,unsigned s,const TASInvManifest *m){(void)m;last_op=op;last_g=g;last_s=s;invocations++;return delivery;}
static bool tas_inv_host_request(unsigned);
static unsigned policy(void){return 33;}
static unsigned (*tas_diag_policy_word)(void)=policy;
static TASInvDonor evidence={
 "31.6.2","262872150334984303","34613ae5d1e03658876de5e4d1cec6a6",
 "890c6daabeeeb69be3308337ef61d63deba489e396824d4774c1a8ebd84576f5",
 "be274a2347cc3f5a9e988474553df5a8","9f5bc675604dfc430ef729bf1b875e5bdf6a9f327576b63987eca424d8cce02a",
 "20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458",98,28682408};
static uint64_t now_ms(void){return time_ms;}
static bool sha(const void *p,size_t n,unsigned char out[32]){
 assert(n==sizeof(tas_inv_manifest_bytes) && !memcmp(p,tas_inv_manifest_bytes,n));
 memcpy(out,tas_inv_manifest_sha256,32);return true;
}
long app_state=2,thermal=0;
static void run_main(void){assert(block);struct Block *b=block;block=NULL;b->invoke(b);}
static void ack_stop(void){assert(last_op==3);assert(tas_inv_ack(last_g,last_s,3,true));}
static void arm(void){assert(tas_inv_host_request(1));assert(tas_inv_ack(last_g,last_s,1,true));assert(tas_inv_status().state==TAS_INV_ARMED);}
'''
        main=r'''
int main(void){
 assert(tas_inv_initialize(sha));assert(tas_inv_admit(&evidence,7,7));
 assert(!tas_inv_host_request(1)); // Protection not initialized; no UI page exists.
 install_resource_observers();assert(subscriptions==5);
 assert(!tas_inv_host_request(1) && tas_inv_status().reason==TAS_INV_BACKGROUND);
 app_state=0;thermal=2;assert(!tas_inv_host_request(1) && tas_inv_status().reason==TAS_INV_THERMAL);
 thermal=0;on_main=false;assert(!tas_inv_host_request(1));on_main=true;
 assert(tas_inv_host_request(1));unsigned old_g=last_g,old_s=last_s;
 for(unsigned i=0;i<100;i++)memory_warning(nil,0,nil);
 assert(queued==1);run_main();
 assert(tas_inv_status().state==TAS_INV_STOPPING && last_op==3);
 assert(!tas_inv_ack(old_g,old_s,1,true)); // Stale Arm cannot restart after warning.
 unsigned sent=invocations;resource_stop(TAS_INV_MEMORY);assert(invocations==sent);
 ack_stop();assert(tas_inv_status().state==TAS_INV_DORMANT && tas_inv_status().reason==TAS_INV_MEMORY);
 resource_changed(nil,0,nil);run_main();assert(tas_inv_status().state==TAS_INV_DORMANT);
 arm();time_ms+=4000;assert(tas_inv_host_request(2));
 const char *packet="[4,0,0,[[0,1,0,0,0,0,0,0,0]]]";
 assert(tas_inv_report_accept(last_g,last_s,packet,strlen(packet),time_ms));
 thermal=2;resource_changed(nil,0,nil);run_main();
 assert(tas_inv_report_available() && tas_inv_status().state==TAS_INV_STOPPING);
 ack_stop();char out[65536];assert(tas_inv_report_format(out,sizeof(out))>0);
 assert(strstr(out,"interrupted=1") && strstr(out,"stop-reason=8"));
 thermal=0;arm();app_state=2;resource_changed(nil,0,nil);run_main();ack_stop();
 app_state=0;resource_changed(nil,0,nil);run_main();assert(tas_inv_status().state==TAS_INV_DORMANT);
 arm();delivery=false;memory_warning(nil,0,nil);run_main();
 assert(tas_inv_status().state==TAS_INV_UNSUPPORTED); // Failed teardown is never success.
 assert(tas_inv_report_available());
}
'''
        execute(prelude+selected+main,["src/TASInvestigation.c","src/TASInvestigationReport.c"],True)

    def test_export_request_worker_main_handoff_and_real_registry_footer(self):
        source=(ROOT/"src/TASInvestigationUI.c").read_text()
        selected="\n".join(function(source,n) for n in ["footer","export_finish","export_worker","export_report"])
        prelude=r'''
#include "TASInvestigation.h"
#include "TASInvestigationReport.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef void *id;typedef const char *SEL;typedef unsigned char BOOL;
#define YES 1
#define nil ((id)0)
typedef struct {double x,y,width,height;} Rect;
static struct {id page,table,path;bool copy;size_t length;}export_job;
static char export_buffer[65536],ns_buffer[65536];
static bool on_main=true;static unsigned background_jobs,clipboard,notices,refs;
static void (*worker)(void *);static void *worker_context,*block;
void *_NSConcreteGlobalBlock[32];
struct Block {void *isa;int flags,reserved;void(*invoke)(void *);};
static SEL sel_registerName(const char *s){return s;}
static id objc_getClass(const char *s){return (id)s;}
static id objc_retain(id p){assert(on_main);if(p)refs++;return p;}
static void objc_release(id p){assert(on_main && p && refs);refs--;}
static uintptr_t send(id o,SEL s,...){
 (void)o;va_list a;va_start(a,s);uintptr_t result=1;
 if(!strcmp(s,"addOperationWithBlock:")) {assert(!on_main && !block);block=va_arg(a,id);}
 else if(!strcmp(s,"setString:")){assert(on_main);clipboard++;(void)va_arg(a,id);}
 else assert(on_main || !strcmp(s,"mainQueue"));
 va_end(a);return result;
}
static uintptr_t (*objc_msgSend)(id,SEL,...)=send;
static id m0(id o,const char *s){return (id)send(o,s);}
static id m1(id o,const char *s,id a){return (id)send(o,s,a);}
static id ns(const char *s){assert(on_main);snprintf(ns_buffer,sizeof(ns_buffer),"%s",s);return ns_buffer;}
static void notice(id p,const char *s){(void)p;(void)s;assert(on_main);notices++;}
static void *dispatch_get_global_queue(long q,unsigned long f){(void)q;(void)f;return NULL;}
static void dispatch_async_f(void *q,void *c,void(*fn)(void*)){(void)q;assert(on_main);background_jobs++;worker=fn;worker_context=c;}
bool tas_inv_configuration(TASInvManifest *m,char digest[65],unsigned *source){
 memset(m,0,sizeof(*m));m->version=5;strcpy(m->description,"The compiled investigation description");
 memset(digest,'a',64);digest[64]=0;*source=0;return true;
}
'''
        main=r'''
int main(void){
 const char *p="[4,0,1,[[0,1,0,0,0,0,0,0,0]]]";
 assert(tas_inv_report_accept(2,2,p,strlen(p),100));
 footer(nil,0,nil,0);assert(strstr(ns_buffer,"revision 5") && strstr(ns_buffer,"compiled investigation description"));
 export_report((id)1,(id)2,(id)3,true);
 assert(background_jobs==1 && clipboard==0 && refs==3);
 export_report((id)1,(id)2,(id)3,true);assert(background_jobs==1 && notices==1);
 assert(tas_inv_report_accept(3,3,p,strlen(p),200)); // Ingress does not wait for worker.
 on_main=false;worker(worker_context);assert(clipboard==0 && block);
 on_main=true;struct Block *b=block;block=NULL;b->invoke(b);
 assert(clipboard==1 && refs==0 && strstr(ns_buffer,"generation=2 sequence=2"));
 export_report((id)1,(id)2,(id)3,true);assert(background_jobs==2);
 on_main=false;worker(worker_context);on_main=true;
 tas_inv_report_export_cancel();b=block;block=NULL;b->invoke(b);
 assert(clipboard==1 && refs==0 && tas_inv_report_available());
}
'''
        execute(prelude+selected+main,["src/TASInvestigationReport.c"],True)
