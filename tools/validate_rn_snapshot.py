"""Execute the shipped graft in matching Hermes, through the production RN handler.

Only the test bundle's global bootstrap is substituted. All owned function bodies,
including snapshot preparation, serialization and bridge calls, come from the
production C patch chain. React/RN state and Objective-C boxing are host adapters.
The Foundation/Fabric/RCTMethod iOS runtime is not simulated or claimed validated.
"""
import argparse
import ast
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parent.parent
RUNTIME_COMMIT='40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c'
DONOR_SHA='422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b'
INPUTS=['src/rn/ProviderEmoteStrip.js','src/TASRNStripPayload.h','src/TASDemandRNBridge.h',
        'src/TASImageDemand.c','src/TASImageDemand.h','src/TASEmotes.c',
        'tests/native/hermes_snapshot_runner.cpp','tests/fixtures/snapshot_exercise.js',
        'tests/test_image_demand.py','tests/test_rn_library.py','tools/validate_rn_snapshot.py',
        'tools/rn_graft.py','tools/build_snapshot_runtime.py','tests/test_rn_snapshot_runtime.py','src/TASDiagnostics.c','build.sh']
INPUTS += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'src').glob('TASRN*Patch.h'))]
INPUTS += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'src').glob('TASRN*Payload.h')) if str(p.relative_to(ROOT)) not in INPUTS]
def fingerprints():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS}
def check_gate(path):
    data=json.loads(path.read_text())
    if data.get('runtime_commit')!=RUNTIME_COMMIT or data.get('donor_sha256')!=DONOR_SHA or data.get('accepted_snapshots',0)<1 or not data.get('passed') or data.get('inputs')!=fingerprints():
        raise ValueError('Snapshot runtime validation is missing, failed or stale; no diagnostic build/device scrolling test is allowed')
    print('Compiled snapshot pipeline gate passed (host Hermes + production native handler).')
def constant_script(path,name):
    tree=ast.parse(path.read_text())
    return next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
def compile_js(compiler,source,out):
    subprocess.run([str(compiler),'-O','-fno-inline','-g0','-emit-binary','-out',str(out),str(source)],check=True)
def patch_chain(zig,donor,tmp):
    (tmp/'patch.c').write_text('''#include "TASRNStripPatch.h"
void *patch(const void *p,size_t n,TASRNSHA1 s,size_t *out,unsigned step){
 if(step==0)return tas_rn_width_patch(p,n,s,out);
 if(step==1)return tas_rn_local_patch(p,n,s,out);
 if(step==2)return tas_rn_composer_patch(p,n,s,out);
 if(step==3)return tas_rn_popup_patch(p,n,s,out);
 return tas_rn_strip_patch(p,n,s,out);}
void dispose(void *p){free(p);}
''')
    libpath=tmp/'patch.so'
    subprocess.run([str(zig),'cc','-shared','-fPIC','-I',str(ROOT/'src'),str(tmp/'patch.c'),'-o',str(libpath)],check=True)
    lib=ctypes.CDLL(str(libpath)); SHA=ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p)
    @SHA
    def sha(data,n,out):ctypes.memmove(out,hashlib.sha1(ctypes.string_at(data,n)).digest(),20);return out
    lib.patch.argtypes=[ctypes.c_void_p,ctypes.c_size_t,SHA,ctypes.POINTER(ctypes.c_size_t),ctypes.c_uint];lib.patch.restype=ctypes.c_void_p
    lib.dispose.argtypes=[ctypes.c_void_p]
    for step in range(5):
        n=ctypes.c_size_t();buf=ctypes.create_string_buffer(donor);p=lib.patch(buf,len(donor),sha,ctypes.byref(n),step)
        assert p,('Production patch refused',step)
        try:donor=ctypes.string_at(p,n.value)
        finally:lib.dispose(p)
    return donor

def test_entry(body,compiler,tmp):
    from rn_graft import read, assemble
    h=read(body);ids={s:i for i,s in reversed(list(enumerate(h.strings)))}
    (tmp/'entry.js').write_text('function buildLocalEcho() {}')
    compile_js(compiler,tmp/'entry.js',tmp/'entry.hbc')
    stub=read((tmp/'entry.hbc').read_bytes());f=stub.function_headers[0]
    code,exc=assemble(stub,0,ids,47321);assert not exc
    # Function 1 -> actual owned installer 47322; only global bootstrap changes.
    out=bytearray(body[:-20]);start=len(out);out.extend(code)
    while len(out)%4:out.append(0)
    info=len(out);out.extend(struct.pack('<8I',start,f.paramCount,f.loopDepth,len(code),ids[''],f.numberRegCount,f.nonPtrRegCount,f.frameSize))
    flags=f.prohibitInvoke|(int(f.strictMode)<<2)|(f.kind<<6)
    out.extend(bytes((f.readCacheSize,f.writeCacheSize,f.privateNameCacheSize,0,flags,0,0,0)))
    out[128:140]=struct.pack('<III',info&0xffffff,(info>>24)<<14,32<<24)
    struct.pack_into('<I',out,type(h.header).globalCodeIndex.offset,0)
    struct.pack_into('<I',out,type(h.header).fileLength.offset,len(out)+20)
    out.extend(hashlib.sha1(out).digest());return bytes(out)

def native_adapter(zig,tmp):
    prelude=constant_script(ROOT/'tests/test_image_demand.py','prelude')
    source=(ROOT/'src/TASImageDemand.c').read_text().replace('#include <objc/runtime.h>','').replace('#include <objc/message.h>','')
    adapter=r'''
#define YES 1
static bool kind(id o,const char *s){return o && ((!strcmp(s,"NSNumber") && o->type==77) || (!strcmp(s,"NSString") && o->type==78));}
static const char *text(id o){return o?o->text:NULL;}
typedef struct {const char *jsName,*objcName;BOOL sync;} TASRNMethodInfo;
static id box(int n){static struct Fake value;value.type=77;value.text=n?"1":"0";return &value;}
#define TAS_DEMAND_RN_UINT(o) ((unsigned)strtod((o)->text,NULL))
#define TAS_DEMAND_RN_DOUBLE(o) strtod((o)->text,NULL)
#define TAS_DEMAND_RN_BOX(n) box(n)
#include "TASDemandRNBridge.h"
double ss_observe(double e,double s,const char *asset,double a,double b){
 char es[32],ss[32],as[32],bs[32];snprintf(es,sizeof(es),"%.17g",e);snprintf(ss,sizeof(ss),"%.17g",s);snprintf(as,sizeof(as),"%.17g",a);snprintf(bs,sizeof(bs),"%.17g",b);
 struct Fake event={.text=es,.type=77},scope={.text=ss,.type=77},value={.text=asset,.type=78},x={.text=as,.type=77},y={.text=bs,.type=77};
 const TASRNMethodInfo *metadata=rn_demand_export(nil,NULL);assert(metadata->sync && !strcmp(metadata->jsName,"observe") && strstr(metadata->objcName,"b:(NSNumber *)b"));
 id accepted=rn_demand_observe(nil,NULL,&event,&scope,asset?&value:nil,&x,&y);
 return accepted?strtod(accepted->text,NULL):NAN;
}
const char *ss_report(void){static char out[32768];tas_demand_status(out,sizeof(out));return out;}
'''
    path=tmp/'native.c';path.write_text(prelude+source+adapter);lib=tmp/'native.so'
    subprocess.run([str(zig),'cc','-shared','-fPIC','-DTAS_IMAGE_DEMAND_DIAGNOSTIC=1','-I',str(ROOT/'src'),str(path),'-pthread','-o',str(lib)],check=True)
    return lib

def validate(a):
    assert subprocess.check_output(['git','-C',str(a.runtime_source),'rev-parse','HEAD'],text=True).strip()==RUNTIME_COMMIT,'Wrong Hermes runtime revision'
    assert hashlib.sha256(a.donor.read_bytes()).hexdigest()==DONOR_SHA,'Wrong donor'
    stamp=json.loads(a.runner.with_suffix('.build.json').read_text())
    assert stamp['runtime_commit']==RUNTIME_COMMIT and stamp['runner_source_sha256']==hashlib.sha256((ROOT/'tests/native/hermes_snapshot_runner.cpp').read_bytes()).hexdigest() and stamp['runner_sha256']==hashlib.sha256(a.runner.read_bytes()).hexdigest(),'Runner missing/stale build evidence'
    a.record.parent.mkdir(parents=True,exist_ok=True)
    a.record.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        from rn_graft import generate
        tmp=Path(folder)
        generate(a.donor,a.hermesc,ROOT/'src/rn/ProviderEmoteStrip.js',tmp/'payload.h',prefix='STRIP',factory_id=4869,function_base=47322)
        assert (tmp/'payload.h').read_bytes()==(ROOT/'src/TASRNStripPayload.h').read_bytes(),'Stale production payload'
        native=native_adapter(a.zig,tmp)
        body=patch_chain(a.zig,a.donor.read_bytes(),tmp)
        (tmp/'grafted.hbc').write_bytes(test_entry(body,a.hermesc,tmp))
        # Reuse the host React facade; no source-level execution of owned logic.
        script=constant_script(ROOT/'tests/test_rn_library.py','script')
        prefix=script.split("vm.createContext(env);")[0].replace("const fs=require('fs'),vm=require('vm'),assert=require('assert');",'')
        prefix+='\n_runtimeGlobal.__r=env.__r;_runtimeGlobal.setInterval=env.setInterval;_runtimeGlobal.clearInterval=env.clearInterval;\n'
        (tmp/'exercise.js').write_text(prefix+(ROOT/'tests/fixtures/snapshot_exercise.js').read_text())
        compile_js(a.hermesc,tmp/'exercise.js',tmp/'exercise.hbc')
        result=subprocess.run([str(a.runner),str(native),str(tmp/'grafted.hbc'),str(tmp/'exercise.hbc')],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr or ('Hermes runtime validation failed, exit '+str(result.returncode)))
        assert 'calc list=1 transition=1' in result.stdout,result.stdout
        assert 'calc list=2 transition=16' in result.stdout,result.stdout
        assert 'PRIVATE-SENTINEL' not in result.stdout
        (a.record.parent/'snapshot-runtime-report.txt').write_text(result.stdout)
        a.record.write_text(json.dumps({'passed':True,'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA,'accepted_snapshots':32,'runner_sha256':stamp['runner_sha256'],'compiler_sha256':hashlib.sha256(a.hermesc.read_bytes()).hexdigest(),'inputs':fingerprints(),'evidence':'Host Hermes-98 graft + production RN handler/parser. No iOS Fabric/RCTMethod/device execution.'},indent=2)+'\n')
        print('Actual grafted Hermes snapshot generation and native acceptance passed; 32 bounded snapshots accepted.')
        check_gate(a.record)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',type=Path);p.add_argument('--record',type=Path,default=ROOT/'build/snapshot-validation.json');p.add_argument('--donor',type=Path);p.add_argument('--zig',type=Path);p.add_argument('--hermesc',type=Path);p.add_argument('--runner',type=Path);p.add_argument('--runtime-source',type=Path);a=p.parse_args()
    if a.check:check_gate(a.check)
    else:validate(a)
