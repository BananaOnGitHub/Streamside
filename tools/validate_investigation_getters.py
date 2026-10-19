"""Execute the exact donor getState/helper graph behind mutation traps.

Only the test entry wrapper is synthetic. Getter 38870, helpers 22334/22335/
22458, and position reader 46258 execute their original donor bodies.
"""
import hashlib
import struct
import subprocess
from pathlib import Path
from rn_graft import read,parse_hbc_bytecode
from generate_investigation_payload import encode
from validate_rn_snapshot import test_entry,compile_js
ROOT=Path(__file__).resolve().parent.parent
def run_getter_gate(body,compiler,runner,native,tmp):
 h=read(body)
 # Static call/write inventory: inset helper copies into a new object, never
 # writes the original. getScrollVelocity walks a history; capture admission
 # below uses the donor-bounded state fixture, with a runtime work deadline.
 facts={}
 for fid in [38870,22334,22335,22458,46258]:
  f=h.function_headers[fid];ops=list(parse_hbc_bytecode(f,h));facts[str(fid)]={'sha256':hashlib.sha256(body[f.offset:f.offset+f.bytecodeSizeInBytes]).hexdigest(),'bytes':f.bytecodeSizeInBytes}
  assert not any(x.inst.name.startswith(('StoreToEnv','StoreNPToEnv','PutById','PutByVal','PutNewOwn')) for x in ops),(fid,'Unexpected mutation opcode')
  assert not any(x.inst.name.startswith(('GetById','TryGetById')) and h.strings[x.arg4] in ['elementAtIndex','sizeAtIndex','set','delete'] for x in ops),(fid,'Mutating helper dependency')
 # Test-only wrapper establishes the *actual* environments expected by 38870.
 code=b''.join([encode('CreateTopLevelEnvironment',0,75),encode('LoadParam',2,1),encode('LoadParam',3,2),encode('LoadParam',5,3),encode('StoreToEnvironment',0,7,5),encode('CreateClosure',5,0,22334),encode('StoreToEnvironment',0,27,5),encode('CreateClosure',5,0,22335),encode('StoreToEnvironment',0,28,5),encode('CreateClosure',5,0,22458),encode('StoreToEnvironment',0,74,5),encode('CreateEnvironment',4,0,3),encode('StoreToEnvironment',4,0,2),encode('StoreToEnvironment',4,2,3),encode('CreateClosure',5,4,38870),encode('Ret',5)])
 output=bytearray(test_entry(body,compiler,tmp,1)[:-20]);start=len(output);output.extend(code)
 while len(output)%4:output.append(0)
 info=len(output);output.extend(struct.pack('<8I',start,4,0,len(code),h.strings.index(''),0,0,6));output.extend(bytes((0,0,0,0,2,0,0,0)));output[140:152]=struct.pack('<III',info&0xffffff,(info>>24)<<14,32<<24);struct.pack_into('<I',output,type(h.header).fileLength.offset,len(output)+20);output.extend(hashlib.sha1(output).digest());(tmp/'getters.hbc').write_bytes(output)
 compile_js(compiler,ROOT/'tests/fixtures/investigation_getters.js',tmp/'getters-fixture.hbc')
 result=subprocess.run([str(runner),str(native),str(tmp/'getters.hbc'),str(tmp/'getters-fixture.hbc')],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 print('Exact donor getState, content size/inset, velocity and positions passed deep mutation traps')
 return facts

def run_seam_gate(body,compiler,runner,native,tmp):
 h=read(body);ops=list(parse_hbc_bytecode(h.function_headers[22318],h))
 found=[x for x in ops if x.inst.name=='LoadFromEnvironment' and (x.arg1,x.arg2,x.arg3)==(36,16,19)];assert len(found)==1
 start=found[0].original_pos;f=h.function_headers[22318];extra=body[f.offset+start:f.offset+start+31]
 wanted=[('LoadFromEnvironment',36,16,19),('JmpFalseLong',21,36),('LoadFromEnvironment',37,41,0),('Call3',13,36,37,34,13),('JmpLong',11),('Call3',13,35,2,34,13)]
 at=ops.index(found[0]);assert [(x.inst.name,*[getattr(x,'arg'+str(i+1)) for i in range(len(x.inst.operands))]) for x in ops[at:at+6]]==wanted
 # Execute the actual patched seam bytes with r39 deliberately poisoned.
 code=b''.join([encode('CreateTopLevelEnvironment',16,20),encode('LoadParam',36,4),encode('StoreToEnvironment',16,19,36),encode('CreateTopLevelEnvironment',41,1),encode('LoadParam',37,1),encode('StoreToEnvironment',41,0,37),encode('LoadConstUndefined',39),encode('LoadConstUndefined',2),encode('LoadParam',34,2),encode('LoadParam',13,3),encode('LoadParam',35,5),extra,encode('Ret',13)])
 out=bytearray(test_entry(body,compiler,tmp,1)[:-20]);offset=len(out);out.extend(code)
 while len(out)%4:out.append(0)
 info=len(out);out.extend(struct.pack('<8I',offset,6,0,len(code),h.strings.index(''),0,0,91));out.extend(bytes((0,0,0,0,2,0,0,0)));out[140:152]=struct.pack('<III',info&0xffffff,(info>>24)<<14,32<<24);struct.pack_into('<I',out,type(h.header).fileLength.offset,len(out)+20);out.extend(hashlib.sha1(out).digest());(tmp/'seam.hbc').write_bytes(out)
 (tmp/'seam.js').write_text('var global=_runtimeGlobal,s={},t={},p={},calls=0;function jsx(a,b){calls++;if(a!==t || b!==p)throw new Error("props");return 73;}function hook(a,b){if(this!==s)throw new Error("store register reused");return jsx(a,b);}if(buildLocalEcho(s,t,p,hook,jsx)!==73 || calls!==1)throw new Error("hook call");if(buildLocalEcho(s,t,p,null,jsx)!==73 || calls!==2)throw new Error("fallback");')
 compile_js(compiler,tmp/'seam.js',tmp/'seam-test.hbc');result=subprocess.run([str(runner),str(native),str(tmp/'seam.hbc'),str(tmp/'seam-test.hbc')],capture_output=True,text=True);assert result.returncode==0,result.stderr
 print('Actual scoped JSX seam passed store environment binding and dormant fallback')
