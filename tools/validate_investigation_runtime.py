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
from rn_graft import read,parse_hbc_bytecode,generate
from validate_rn_snapshot import ROOT,RUNTIME_COMMIT,DONOR_SHA,patch_chain,test_entry,compile_js

INPUTS=['src/rn/Investigation.js','src/TASRNInvestigationPatch.h','src/TASRNInvestigationLayout.h','src/TASRNInvestigationOriginalPayload.h','src/TASRNInvestigationFunctionalPayload.h','tools/generate_investigation_payload.py','tools/validate_investigation_runtime.py','tests/fixtures/investigation_bootstrap.js']
def fingerprints():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in INPUTS}
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
    path=tmp/'adapter.c';path.write_text('double ss_observe(double a,double b,const char *c,double d,double e){(void)a;(void)b;(void)c;(void)d;(void)e;return 1;}\nconst char *ss_report(void){return "Compiled dormant bootstrap passed\\n";}\n')
    out=tmp/'adapter.so';subprocess.run(['cc','-shared','-fPIC',str(path),'-o',str(out)],check=True);return out
def validate(a):
    assert subprocess.check_output(['git','-C',str(a.runtime_source),'rev-parse','HEAD'],text=True).strip()==RUNTIME_COMMIT
    stamp=json.loads(a.runner.with_suffix('.build.json').read_text());assert stamp['runtime_commit']==RUNTIME_COMMIT and stamp['runner_sha256']==hashlib.sha256(a.runner.read_bytes()).hexdigest()
    assert hashlib.sha256(a.donor.read_bytes()).hexdigest()==DONOR_SHA
    a.record.parent.mkdir(parents=True,exist_ok=True);a.record.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        tmp=Path(directory);original=a.donor.read_bytes();functional=patch_chain(a.zig,original,tmp);native=adapter(tmp)
        fixture=(ROOT/'tests/fixtures/investigation_bootstrap.js').read_text();outputs=[]
        for label,body in [('Original',original),('Functional',functional)]:
            base=read(body).header.functionCount;generated=tmp/'generated.h'
            generate(a.donor,a.hermesc,ROOT/'src/rn/Investigation.js',generated,prefix='INV_'+label.upper(),factory_id=4900,function_base=base)
            assert generated.read_bytes()==(ROOT/('src/TASRNInvestigation'+label+'Payload.h')).read_bytes(),'Stale payload'
            patched=graft(body,tmp);structure(body,patched)
            (tmp/'entry.hbc').write_bytes(test_entry(patched,a.hermesc,tmp,base))
            (tmp/'exercise.js').write_text(fixture+'\nexerciseBootstrap(buildLocalEcho());\n');compile_js(a.hermesc,tmp/'exercise.js',tmp/'exercise.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'entry.hbc'),str(tmp/'exercise.hbc')],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            print(label+': owned bootstrap, late callable command, original ref/cleanup/error, no dormant work passed')
            # Execute the unchanged actual factory export and all its original
            # style initialization after the guarded additional installer.
            (tmp/'factory.hbc').write_bytes(test_entry(patched,a.hermesc,tmp,4900))
            factory=fixture+'\nvar exports={};buildLocalEcho(global,__r,null,null,{},exports,[1,17,72,5,245]);check(typeof exports.ChatMessageList==="function","donor memo export retained");registered.StreamsideInvestigation().command(0,0,0,null);check(calls[calls.length-1][4]===true,"factory-installed callable command");\n'
            (tmp/'factory.js').write_text(factory);compile_js(a.hermesc,tmp/'factory.js',tmp/'factory-exercise.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'factory.hbc'),str(tmp/'factory-exercise.hbc')],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            outputs.append({'profile':label,'bytes':len(patched),'sha256':hashlib.sha256(patched).hexdigest()})
            print(label+': actual donor factory, memo export and guarded installer passed')
    a.record.write_text(json.dumps({'passed':True,'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA,'inputs':fingerprints(),'profiles':outputs,'live_rct_delivery_verified':False},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['donor','hermesc','runner','runtime-source','zig']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--record',type=Path,default=ROOT/'build/investigation-validation.json');validate(p.parse_args())
