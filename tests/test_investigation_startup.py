"""Production native startup accepts either dependency arrival order."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
def function(source,name):
 match=re.search(r'^static [^\n]*\b'+name+r'\([^;]*?\)\s*\{',source,re.M)
 assert match,name
 start=match.start();brace=source.index('{',match.start());depth=1;end=brace+1
 while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]+'\n'
class StartupTests(unittest.TestCase):
 def test_dependency_orders_rejections_and_stale_queued_probe(self):
  source=(ROOT/'src/TASInvestigationHost.c').read_text()
  selected='\n'.join(function(source,n) for n in ['get_flag','flag','inc_flag','is_supported','callable_slot','get_callable','bound_epoch','set_callable','maybe_probe','probe','ready','ack'])
  prelude=r'''#include "TASInvestigation.h"
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <pthread.h>
typedef struct Fake *id;typedef void *Class;typedef const char *SEL;
struct Fake{Class klass;id callable;unsigned bound;};
#define nil ((id)0)
#define TAS_INV_HOST_CAPABILITIES 7U
static pthread_mutex_t host_lock=PTHREAD_MUTEX_INITIALIZER;
static ptrdiff_t callable_offset=offsetof(struct Fake,callable);
static id module_weak;static unsigned source_epoch,ready_caps,ready_calls,ready_result;
static bool supported,pong,probe_scheduled;static uint64_t probe_deadline;
static char module_epoch_key;static TASInvDonor evidence;
static unsigned queued,invocations,admissions,timers,invalidated;static uint64_t time_ms=100;
static void (*queued_fn)(void *);static void *queued_context;
static id objc_loadWeakRetained(id *p){return *p;}
static id objc_storeWeak(id *p,id v){*p=v;return v;}
static void objc_release(id o){(void)o;}
static Class objc_getClass(const char *n){assert(!strcmp(n,"RCTCallableJSModules"));return (Class)1;}
static Class object_getClass(id o){return o->klass;}
static id objc_getAssociatedObject(id o,const void *k){(void)k;return (id)(uintptr_t)o->bound;}
static void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t p){(void)k;(void)p;o->bound=(unsigned)(uintptr_t)v;}
static bool integer(id o,unsigned *out){*out=(unsigned)(uintptr_t)o;return true;}
static id box(unsigned n){return (id)(uintptr_t)n;}
static uint64_t now_ms(void){return time_ms;}
static void *dispatch_get_global_queue(long q,unsigned long f){(void)q;(void)f;return 0;}
static void dispatch_async_f(void *q,void *context,void (*fn)(void *)){(void)q;queued++;queued_fn=fn;queued_context=context;}
static void schedule_timer(void){timers++;}
static bool invoke(unsigned op,unsigned g,unsigned seq,const TASInvManifest *m){(void)m;assert(!op && !g && !seq);invocations++;return true;}
void tas_inv_invalidate(unsigned reason){(void)reason;invalidated++;}
bool tas_inv_admit(const TASInvDonor *d,uint32_t caps,uint32_t epoch){(void)d;assert(caps==7 && epoch==source_epoch);admissions++;return true;}
bool tas_inv_ack(uint32_t g,uint32_t s,unsigned op,bool ok){(void)g;(void)s;(void)op;(void)ok;return false;}
bool tas_inv_expire(uint64_t now){(void)now;return false;}
static bool tas_inv_report_complete(unsigned g,unsigned s){(void)g;(void)s;return false;}
static void emergency_stop(void){assert(0);}
static void maybe_probe(void);static void probe(void *);
'''
  main=r'''
static void reset(struct Fake *m){memset(m,0,sizeof(*m));source_epoch=7;supported=true;module_weak=nil;pong=false;probe_scheduled=false;probe_deadline=0;queued=invocations=admissions=timers=invalidated=ready_calls=ready_result=0;queued_fn=0;time_ms=100;}
static void acknowledge(id m){ack(m,0,box(7),box(0),box(0),box(0),box(1));assert(admissions==1 && pong);}
int main(void){
 struct Fake module,callable={.klass=(Class)1},foreign={.klass=(Class)3};
 reset(&module);
 // Ready first must retain its epoch while awaiting injected callable.
 assert(ready(&module,0,box(1),box(7))==box(7));assert(!queued && !admissions && probe_deadline==2100 && timers>0);
 ack(&module,0,box(7),box(0),box(0),box(0),box(1));assert(!admissions && !pong);
 set_callable(&module,0,&foreign);assert(!queued && !module.callable);
 set_callable(&module,0,&callable);assert(queued==1 && !admissions);
 queued_fn(queued_context);assert(invocations==1);acknowledge(&module);
 set_callable(&module,0,&callable);assert(queued==1);assert(ready(&module,0,box(1),box(7))==box(0));
 // Callable first: one probe, still no admission before its acknowledgment.
 reset(&module);set_callable(&module,0,&callable);assert(!queued);
 assert(ready(&module,0,box(1),box(7))==box(7));assert(queued==1 && !admissions);queued_fn(queued_context);acknowledge(&module);
 // Availability and source gates are unchanged; no fabricated readiness.
 reset(&module);supported=false;assert(ready(&module,0,box(1),box(7))==box(0));assert(!queued);
 reset(&module);assert(ready(&module,0,box(2),box(7))==box(0));assert(ready(&module,0,box(1),box(8))==box(0));assert(!queued);
 reset(&module);source_epoch=0;assert(ready(&module,0,box(1),box(7))==box(0));
 reset(&module);set_callable(&module,0,&callable);assert(ready(&module,0,box(1),box(7))==box(7));source_epoch=8;queued_fn(queued_context);assert(!invocations && !admissions);
 reset(&module);set_callable(&module,0,&callable);assert(ready(&module,0,box(1),box(7))==box(7));probe_deadline=0;queued_fn(queued_context);assert(!invocations && !admissions);
 reset(&module);set_callable(&module,0,&callable);assert(ready(&module,0,box(1),box(7))==box(7));time_ms=2101;queued_fn(queued_context);assert(!invocations && !admissions);
}
'''
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'startup.c';path.write_text(prelude+selected+main);exe=Path(tmp)/'startup'
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'src'),str(path),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
