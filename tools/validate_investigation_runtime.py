"""Exact predecessor/graft and compiled Hermes bootstrap acceptance gate.

Native UIKit/RCT scheduling is not executed on Linux. The donor native audit,
startup round-trip and device verification are distinct evidence boundaries.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parent.parent
RUNTIME_COMMIT="40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c"
DONOR_SHA="20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458"
import sys
if '--check' not in sys.argv:
    from rn_graft import read,parse_hbc_bytecode,generate
    from validate_investigation_getters import run_getter_gate,run_seam_gate
    from validate_rn_snapshot import patch_chain,test_entry,compile_js

INPUTS=['src/rn/Investigation.js','src/TASRNInvestigationPatch.h','src/TASRNInvestigationLayout.h','src/TASRNInvestigationOriginalPayload.h','src/TASRNInvestigationFunctionalPayload.h','tools/generate_investigation_payload.py','tools/validate_investigation_runtime.py','tests/fixtures/investigation_bootstrap.js','tests/fixtures/investigation_recorder.js','src/TASInvestigationHost.c','src/TASInvestigationReport.c','src/TASInvestigationReport.h','tools/validate_investigation_getters.py','tests/fixtures/investigation_getters.js','src/TASInvestigationUI.c','src/TASInvestigationUI.h','src/TASInvestigation.c','src/TASInvestigation.h','src/TASInvestigationRegistry.h','src/TASInvestigationHost.h','src/TASEmotes.c','src/TASDiagnostics.c','tests/test_investigation_startup.py','tests/fixtures/investigation_startup.js']
def fingerprints():
    names=set(INPUTS)
    for pattern in ['src/TASRN*Patch.h','src/TASRN*Payload.h','src/TASRN*Layout.h']:
        names.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    names.update(['tools/rn_graft.py','tools/validate_rn_snapshot.py','tools/generate_investigation_registry.py','diagnostics/investigations/rn-chat-gaps/2.json','tests/native/hermes_snapshot_runner.cpp'])
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)}
def graft(body,tmp):
    source=tmp/'inv_patch.c';source.write_text('#include "TASRNInvestigationPatch.h"\nvoid *patch(const void *p,size_t n,TASRNSHA1 s,TASInvSHA256 h,size_t *out){return tas_rn_investigation_patch(p,n,s,h,out);}\nvoid dispose(void *p){free(p);}\n')
    libpath=tmp/'inv_patch.so';subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-I',str(ROOT/'src'),str(source),'-o',str(libpath)],check=True)
    lib=ctypes.CDLL(str(libpath));SHA1=ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p);SHA256=ctypes.CFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p)
    @SHA1
    def sha1(data,n,out):ctypes.memmove(out,hashlib.sha1(ctypes.string_at(data,n)).digest(),20);return out
    @SHA256
    def sha256(data,n,out):ctypes.memmove(out,hashlib.sha256(ctypes.string_at(data,n)).digest(),32);return True
    lib.patch.argtypes=[ctypes.c_void_p,ctypes.c_size_t,SHA1,SHA256,ctypes.POINTER(ctypes.c_size_t)];lib.patch.restype=ctypes.c_void_p;lib.dispose.argtypes=[ctypes.c_void_p]
    def apply(data):
        source=ctypes.create_string_buffer(data);n=ctypes.c_size_t(99);p=lib.patch(source,len(data),sha1,sha256,ctypes.byref(n));assert source.raw[:-1]==data,'Input mutated'
        if not p:assert n.value==0;return None
        try:return ctypes.string_at(p,n.value)
        finally:lib.dispose(p)
    result=apply(body);assert result,'Production investigation patch refused'
    changed=bytearray(body);changed[40]^=1;assert apply(bytes(changed)) is None
    changed=bytearray(body);changed[200]^=1;changed[-20:]=hashlib.sha1(changed[:-20]).digest();assert apply(bytes(changed)) is None
    assert apply(result) is None,'Duplicate patch admitted'
    return result
def structure(before,after):
    old=read(before);new=read(after)
    assert hashlib.sha1(after[:-20]).digest()==after[-20:] and len(after)==new.header.fileLength
    assert old.strings==new.strings and old.literal_values==new.literal_values
    for i,f in enumerate(old.function_headers):
        g=new.function_headers[i]
        if i not in [4900,22318]:
            assert before[f.offset:f.offset+f.bytecodeSizeInBytes]==after[g.offset:g.offset+g.bytecodeSizeInBytes],('Unrelated function changed',i)
            assert f.frameSize==g.frameSize and f.paramCount==g.paramCount
    factory=list(parse_hbc_bytecode(new.function_headers[4900],new));assert factory[0].inst.name=='CreateFunctionEnvironment' and factory[0].arg2==20
    assert new.function_headers[4900].frameSize==33 and new.function_headers[22318].frameSize==91
    for fid in [4900,22318]+list(range(old.header.functionCount,new.header.functionCount)):
        f=new.function_headers[fid];ops=list(parse_hbc_bytecode(f,new));boundaries={x.original_pos for x in ops}|{f.bytecodeSizeInBytes}
        for x in ops:
            for i,o in enumerate(x.inst.operands):
                if o.operand_type.name.startswith('Addr'):assert x.original_pos+getattr(x,'arg'+str(i+1)) in boundaries,(fid,x)
                if o.operand_meaning and o.operand_meaning.name=='function_id':assert 0<=getattr(x,'arg'+str(i+1))<new.header.functionCount
        for handler in new.function_id_to_exc_handlers.get(fid,[]):assert handler.start in boundaries and handler.end in boundaries and handler.target in boundaries
    assert len(new.function_id_to_exc_handlers[4900])==1
    return old.header.functionCount
def adapter(tmp):
    path=tmp/'adapter.c';path.write_text('#include "TASInvestigationReport.h"\n#include <stdint.h>\ndouble ss_observe(double g,double s,const char *p,double t,double unused){(void)unused;return tas_inv_report_accept((uint32_t)g,(uint32_t)s,p,__builtin_strlen(p),(uint64_t)t)?1:0;}\nconst char *ss_report(void){static char out[65536];tas_inv_report_format(out,sizeof(out));return out;}\n')
    out=tmp/'adapter.so';subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'src'),str(ROOT/'src/TASInvestigationReport.c'),str(path),'-o',str(out)],check=True);return out
def validate(a):
    assert subprocess.check_output(['git','-C',str(a.runtime_source),'rev-parse','HEAD'],text=True).strip()==RUNTIME_COMMIT
    stamp=json.loads(a.runner.with_suffix('.build.json').read_text());assert stamp['runtime_commit']==RUNTIME_COMMIT and stamp['runner_source_sha256']==hashlib.sha256((ROOT/'tests/native/hermes_snapshot_runner.cpp').read_bytes()).hexdigest() and stamp['runner_sha256']==hashlib.sha256(a.runner.read_bytes()).hexdigest()
    assert hashlib.sha256(a.donor.read_bytes()).hexdigest()==DONOR_SHA
    a.record.parent.mkdir(parents=True,exist_ok=True);a.record.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        tmp=Path(directory);original=a.donor.read_bytes();functional=patch_chain(a.zig,original,tmp);native=adapter(tmp)
        fixture=(ROOT/'tests/fixtures/investigation_bootstrap.js').read_text();outputs=[]
        getter_facts=run_getter_gate(original,a.hermesc,a.runner,native,tmp)
        for label,body in [('Original',original),('Functional',functional)]:
            base=read(body).header.functionCount;generated=tmp/'generated.h'
            generate(a.donor,a.hermesc,ROOT/'src/rn/Investigation.js',generated,prefix='INV_'+label.upper(),factory_id=4900,function_base=base)
            assert generated.read_bytes()==(ROOT/('src/TASRNInvestigation'+label+'Payload.h')).read_bytes(),'Stale payload'
            patched=graft(body,tmp);structure(body,patched)
            run_seam_gate(patched,a.hermesc,a.runner,native,tmp)
            (tmp/'entry.hbc').write_bytes(test_entry(patched,a.hermesc,tmp,base))
            (tmp/'startup.js').write_text(fixture+'\n'+(ROOT/'tests/fixtures/investigation_startup.js').read_text()+'\nexerciseStartup(buildLocalEcho);\n');compile_js(a.hermesc,tmp/'startup.js',tmp/'startup.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'entry.hbc'),str(tmp/'startup.hbc')],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            print(label+': missing APIs and bootstrap exceptions fail closed with numeric startup evidence')
            (tmp/'exercise.js').write_text(fixture+'\nexerciseBootstrap(buildLocalEcho());\n');compile_js(a.hermesc,tmp/'exercise.js',tmp/'exercise.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'entry.hbc'),str(tmp/'exercise.hbc')],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            print(label+': owned bootstrap, late callable command, original ref/cleanup/error, no dormant work passed')
            (tmp/'recorder.js').write_text(fixture+'\n'+(ROOT/'tests/fixtures/investigation_recorder.js').read_text()+'\nexerciseRecorder(buildLocalEcho());\n');compile_js(a.hermesc,tmp/'recorder.js',tmp/'recorder.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'entry.hbc'),str(tmp/'recorder.hbc')],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            print(label+': bounded recorder, long arm, priority admission, privacy, partial snapshots and teardown passed')
            # Execute the unchanged actual factory export and all its original
            # style initialization after the guarded additional installer.
            (tmp/'factory.hbc').write_bytes(test_entry(patched,a.hermesc,tmp,4900))
            factory=fixture+'\nvar exports={};buildLocalEcho(globalThis,__r,null,null,{},exports,[1,17,72,5,245]);check(typeof exports.ChatMessageList==="function","donor memo export retained");registered.StreamsideInvestigation().command(0,0,0,null);check(calls[calls.length-1][4]===true,"factory-installed callable command");\n'
            (tmp/'factory.js').write_text(factory);compile_js(a.hermesc,tmp/'factory.js',tmp/'factory-exercise.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'factory.hbc'),str(tmp/'factory-exercise.hbc')],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            outputs.append({'profile':label,'bytes':len(patched),'sha256':hashlib.sha256(patched).hexdigest()})
            print(label+': actual donor factory, memo export and guarded installer passed')
    a.record.write_text(json.dumps({'passed':True,'runtime_commit':RUNTIME_COMMIT,'runner_sha256':hashlib.sha256(a.runner.read_bytes()).hexdigest(),'donor_sha256':DONOR_SHA,'inputs':fingerprints(),'profiles':outputs,'donor_getters':getter_facts,'live_rct_delivery_verified':False},indent=2)+'\n')
def check_record(path):
    try:record=json.loads(path.read_text())
    except (OSError,ValueError) as error:raise SystemExit('Investigation validation receipt is missing/invalid; run the pinned Hermes gate: '+str(error))
    if record.get('passed') is not True or record.get('runtime_commit')!=RUNTIME_COMMIT or record.get('donor_sha256')!=DONOR_SHA or record.get('inputs')!=fingerprints() or set(record.get('donor_getters',{}))!={'38870','22334','22335','22458','46258'} or {p.get('profile') for p in record.get('profiles',[])}!={'Original','Functional'} or len(record.get('runner_sha256',''))!=64:
        raise SystemExit('Stale investigation validation receipt; rerun the compiled Hermes gate')
    print('Investigation compiled runtime validation is current')
if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='--check':check_record(Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'diagnostics/validation/hermes-v1.json');raise SystemExit(0)
    p=argparse.ArgumentParser()
    for name in ['donor','hermesc','runner','runtime-source','zig']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--record',type=Path,default=ROOT/'diagnostics/validation/hermes-v1.json');validate(p.parse_args())
