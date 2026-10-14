"""Required host-Hermes gate for CHAT_TRACE_DIAGNOSTIC=1; never silently skips.

The real C graft/collector and compiled observer execute here. React, stores,
native measurements and Objective-C boxing are host adapters, not iOS evidence.
"""
import argparse
import ctypes
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
import tempfile
from validate_rn_snapshot import ROOT, RUNTIME_COMMIT, DONOR_SHA, fingerprints as base_fingerprints, patch_chain, test_entry, compile_js
INPUTS=['src/rn/ChatTrace.js','src/TASChatTrace.c','src/TASChatTrace.h','src/TASChatTraceBridge.h',
        'tools/validate_chat_trace.py','tests/test_chat_trace.py','tests/fixtures/chat_trace_exercise.js',
        'packaging/StreamsideFramework-Info.plist','tests/fixtures/chat_trace_limits.js','tests/fixtures/chat_trace_refusal.js']
def fingerprints():
    return dict(base_fingerprints(),**{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS})
def check_gate(path):
    value=json.loads(path.read_text())
    if not value.get('passed') or value.get('inputs')!=fingerprints() or value.get('runtime_commit')!=RUNTIME_COMMIT or value.get('donor_sha256')!=DONOR_SHA or value.get('factory_executed') is not True:
        raise ValueError('Chat trace compiled validation missing/failed/stale; rerun make test-chat-trace')
    print('Compiled chat trace gate passed (host Hermes; no device rendering claim).')
def graft(zig,body,tmp):
    path=tmp/'chat_patch.c';path.write_text('#include "TASRNChatTracePatch.h"\nvoid *patch(const void *p,size_t n,TASRNSHA1 s,size_t *out){return tas_rn_chat_trace_patch(p,n,s,out);}\nvoid dispose(void *p){free(p);}\n')
    libpath=tmp/'chat_patch.so'
    subprocess.run([str(zig),'cc','-shared','-fPIC','-I',str(ROOT/'src'),str(path),'-o',str(libpath)],check=True)
    lib=ctypes.CDLL(str(libpath)); SHA=ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p)
    @SHA
    def sha(data,n,out):ctypes.memmove(out,hashlib.sha1(ctypes.string_at(data,n)).digest(),20);return out
    lib.patch.argtypes=[ctypes.c_void_p,ctypes.c_size_t,SHA,ctypes.POINTER(ctypes.c_size_t)];lib.patch.restype=ctypes.c_void_p;lib.dispose.argtypes=[ctypes.c_void_p]
    def apply(data):
        buf=ctypes.create_string_buffer(data);before=buf.raw;length=ctypes.c_size_t(99)
        p=lib.patch(buf,len(data),sha,ctypes.byref(length));assert buf.raw==before,'Input mutated'
        if not p:assert length.value==0;return None
        try:return ctypes.string_at(p,length.value)
        finally:lib.dispose(p)
    out=apply(body);assert out,'Chat graft refused'
    assert apply(body)==out,'Non-deterministic graft'
    assert apply(body[:-1]) is None and apply(out) is None,'Wrong predecessor admitted'
    corrupt=bytearray(body);corrupt[-1]^=1;assert apply(bytes(corrupt)) is None,'Invalid digest admitted'
    from rn_graft import read
    before,after=read(body),read(out)
    count=int(re.search(r'TAS_RN_CHAT_FUNCTIONS (\d+)U',(ROOT/'src/TASRNChatTracePayload.h').read_text()).group(1))
    assert after.header.functionCount==before.header.functionCount+count
    for i,f in enumerate(before.function_headers):
        other=after.function_headers[i]
        a=body[f.offset:f.offset+f.bytecodeSizeInBytes];b=out[other.offset:other.offset+other.bytecodeSizeInBytes]
        if i!=4900:assert a==b,('Unrelated function changed',i)
        else:
            assert other.frameSize==33 and b[:0x116]==a[:0x116] and b[0x127:]==a[0x116:]
            exc=after.function_id_to_exc_handlers[i];assert len(exc)==1 and (exc[0].start,exc[0].end,exc[0].target)==(0x116,0x120,0x125)
            damaged=bytearray(body) # Corrupt join, keeping the footer valid.
            damaged[f.offset+0x116]=0;damaged[-20:]=hashlib.sha1(damaged[:-20]).digest();assert apply(bytes(damaged)) is None
    delta=count*12;table_end=128+before.header.functionCount*12
    expected=bytearray(body[table_end:-20])
    for i,f in enumerate(before.function_headers):
        small=body[128+i*12:140+i*12]
        if small[11]&32:
            info=(struct.unpack_from('<I',small)[0]&0xffffff)|((struct.unpack_from('<I',small,4)[0]>>14)<<24)
            struct.pack_into('<I',expected,info-table_end,f.offset+delta)
    assert out[table_end+delta:len(body)-20+delta]==expected,'Literal buffers/debug data or original metadata changed'
    assert before.strings==after.strings and before.string_kinds==after.string_kinds
    assert after.header.debugInfoOffset==before.header.debugInfoOffset+delta
    assert hashlib.sha1(out[:-20]).digest()==out[-20:]
    return out
def adapter(zig,tmp):
    source=r'''
#include <assert.h>
#include <string.h>
#include <stdbool.h>
static double test_clock=1;
#define TAS_CHAT_TRACE_NOW() test_clock
#include "TASChatTrace.c"
typedef void *SEL;typedef bool BOOL;typedef struct Fake *id;
struct Fake {const char *text;unsigned type;};
#define YES true
#define nil ((id)0)
typedef struct {const char *jsName,*objcName;BOOL sync;} TASRNMethodInfo;
static bool kind(id o,const char *s){return o && o->type==78 && !strcmp(s,"NSString");}
static const char *text(id o){return o?o->text:0;}
static id box(int n){static struct Fake result;result.type=77;result.text=n?"1":"0";return &result;}
#define TAS_CHAT_TRACE_BOX(n) box(n)
#include "TASChatTraceBridge.h"
double ss_observe(double e,double s,const char *packet,double a,double b){
 (void)s;(void)b;if(e==61){test_clock=a;return 1;}assert(e==60);
 const TASRNMethodInfo *info=rn_chat_trace_export(nil,0);
 assert(info->sync && !strcmp(info->jsName,"trace") && !strcmp(info->objcName,"trace:(NSString *)packet"));
 struct Fake arg={packet,78};id result=rn_chat_trace(nil,0,packet?&arg:nil);return result->text[0]=='1';
}
const char *ss_report(void){static char buffer[32768];tas_chat_trace_status(buffer,sizeof(buffer));return buffer;}
'''
    path=tmp/'chat_native.c';path.write_text(source);out=tmp/'chat_native.so'
    subprocess.run([str(zig),'cc','-shared','-fPIC','-DTAS_CHAT_TRACE_DIAGNOSTIC=1','-I',str(ROOT/'src'),str(path),'-pthread','-lm','-o',str(out)],check=True)
    return out
def validate(a):
    from rn_graft import generate,read
    assert subprocess.check_output(['git','-C',str(a.runtime_source),'rev-parse','HEAD'],text=True).strip()==RUNTIME_COMMIT
    assert hashlib.sha256(a.donor.read_bytes()).hexdigest()==DONOR_SHA
    # Admit writable leaves through actual Metro registrations, not mock IDs.
    from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
    h=read(a.donor.read_bytes());instructions=list(parse_hbc_bytecode(h.function_headers[0],h))
    for module,factory in ((4896,4900),(4782,4786),(3500,3504)):
        registrations=[i for i,x in enumerate(instructions) if x.inst.name=='CreateClosure' and x.arg3==factory]
        assert len(registrations)==1
        i=registrations[0];assert instructions[i-2].inst.name=='LoadConstInt' and instructions[i-2].arg2==module
    for fid,property_name in ((4900,'ChatMessageList'),(4786,'ChatLine'),(3504,'LibraryTmiClient'),(27213,'reportError')):
        assert any(x.inst.name.startswith(('GetById','PutById')) and h.strings[x.arg4]==property_name for x in parse_hbc_bytecode(h.function_headers[fid],h)),('Changed donor binding',fid,property_name)
    stamp=json.loads(a.runner.with_suffix('.build.json').read_text())
    assert stamp['runtime_commit']==RUNTIME_COMMIT and stamp['runner_source_sha256']==hashlib.sha256((ROOT/'tests/native/hermes_snapshot_runner.cpp').read_bytes()).hexdigest() and stamp['runner_sha256']==hashlib.sha256(a.runner.read_bytes()).hexdigest()
    a.record.parent.mkdir(parents=True,exist_ok=True);a.record.unlink(missing_ok=True)
    subprocess.run(['python3','-m','unittest','discover','-s','tests','-p','test_chat_trace.py','-v'],cwd=ROOT,check=True)
    with tempfile.TemporaryDirectory() as folder:
        tmp=Path(folder)
        generate(a.donor,a.hermesc,ROOT/'src/rn/ChatTrace.js',tmp/'payload.h',prefix='CHAT',factory_id=4900,function_base=49127)
        assert (tmp/'payload.h').read_bytes()==(ROOT/'src/TASRNChatTracePayload.h').read_bytes(),'Stale chat payload'
        body=graft(a.zig,patch_chain(a.zig,a.donor.read_bytes(),tmp),tmp);native=adapter(a.zig,tmp)
        # Both the owned installer and actual donor factory/export join execute.
        for entry in (49127,4900):
            (tmp/'grafted.hbc').write_bytes(test_entry(body,a.hermesc,tmp,entry_id=entry))
            fixture=(ROOT/'tests/fixtures/chat_trace_exercise.js').read_text()
            if entry==4900:fixture='var _chatFactory=true;\n'+fixture
            (tmp/'fixture.js').write_text(fixture);compile_js(a.hermesc,tmp/'fixture.js',tmp/'fixture.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'grafted.hbc'),str(tmp/'fixture.hbc')],check=True,text=True,capture_output=True)
            assert 's1 m1' in result.stdout and 's2 m1' in result.stdout and 'private' not in result.stdout and 'hooks=2/2' in result.stdout
            print('Compiled chat entry',entry,'passed: scoped flow, callbacks, errors, geometry, privacy, teardown.')
            limits=fixture.split('var original=')[0]+(ROOT/'tests/fixtures/chat_trace_limits.js').read_text()
            (tmp/'limits.js').write_text(limits);compile_js(a.hermesc,tmp/'limits.js',tmp/'limits.hbc')
            result=subprocess.run([str(a.runner),str(native),str(tmp/'grafted.hbc'),str(tmp/'limits.hbc')],check=True,text=True,capture_output=True)
            assert 'rolling' in result.stdout and 'secret' not in result.stdout and 'm3001' in result.stdout
            print('Compiled chat entry',entry,'passed: rolling capture, late labels, long runs and store eviction.')
        (tmp/'refusal.js').write_bytes((ROOT/'tests/fixtures/chat_trace_refusal.js').read_bytes())
        compile_js(a.hermesc,tmp/'refusal.js',tmp/'refusal.hbc')
        result=subprocess.run([str(a.runner),str(native),str(tmp/'grafted.hbc'),str(tmp/'refusal.hbc')],check=True,text=True,capture_output=True)
        assert 'lifetime accepted/schema-refused/rate-limited: 0/0/0' in result.stdout
        print('Actual donor factory fallback passed: absent bridge and throwing installer; original export/styles retained.')
    a.record.write_text(json.dumps({'passed':True,'factory_executed':True,'runtime_commit':RUNTIME_COMMIT,'donor_sha256':DONOR_SHA,
        'compiler_sha256':hashlib.sha256(a.hermesc.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(a.runner.read_bytes()).hexdigest(),
        'grafted_body_sha256':hashlib.sha256(body).hexdigest(),'grafted_body_bytes':len(body),'inputs':fingerprints()},indent=2)+'\n')
    check_gate(a.record)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',type=Path);p.add_argument('--record',type=Path,default=ROOT/'build/chat-trace-validation.json')
    for flag in ('donor','zig','hermesc','runner','runtime-source'):p.add_argument('--'+flag,type=Path)
    a=p.parse_args()
    if a.check:check_gate(a.check)
    else:
        if not all((a.donor,a.zig,a.hermesc,a.runner,a.runtime_source)):p.error('All donor/tool/runtime inputs required; cannot skip')
        validate(a)
