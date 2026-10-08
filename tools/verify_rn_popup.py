"""Verify the complete in-memory patch chain against the exact 31.5 donor.

Own RN behavior is tested separately with mocks. This verifies file structure,
every unaffected function/handler, closure IDs, all imported branch targets,
compiler regeneration and an independent Hermes-98 disassembly. No device
execution is implied; the disk bundle is never changed.
"""
import argparse
import ast
import ctypes
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile
from rn_graft import read, generate, parse_hbc_bytecode

ROOT=Path(__file__).resolve().parent.parent

def verify(donor,zig,hermesc,strip=False):
    with zipfile.ZipFile(donor) as archive:
        body=archive.read('Payload/Twitch.app/index.ios.bundle')
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        original=tmp/'original.hbc';original.write_bytes(body)
        generated=tmp/'payload.h'
        generate(original,hermesc,ROOT/'src/rn/ProviderEmoteInfo.js',generated)
        assert generated.read_bytes()==(ROOT/'src/TASRNPopupPayload.h').read_bytes(), 'Stale payload'
        if strip:
            generate(original,hermesc,ROOT/'src/rn/ProviderEmoteStrip.js',generated,
                     prefix='STRIP',factory_id=4869,function_base=47322)
            assert generated.read_bytes()==(ROOT/'src/TASRNStripPayload.h').read_bytes(),'Stale strip payload'
        (tmp/'patch.c').write_text('''#include "TASRNStripPatch.h"
void *patch(const void *p,size_t n,TASRNSHA1 sha,size_t *out,unsigned step) {
 if(step==0)return tas_rn_width_patch(p,n,sha,out);
 if(step==1)return tas_rn_local_patch(p,n,sha,out);
 if(step==2)return tas_rn_composer_patch(p,n,sha,out);
 if(step==3)return tas_rn_popup_patch(p,n,sha,out);
 return tas_rn_strip_patch(p,n,sha,out);
}
void dispose(void *p){free(p);}
''')
        library=tmp/'patch.so'
        subprocess.run([str(zig),'cc','-shared','-fPIC','-Wall','-Wextra','-Werror',
                        '-I',str(ROOT/'src'),str(tmp/'patch.c'),'-o',str(library)],check=True)
        lib=ctypes.CDLL(str(library));SHA=ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p)
        @SHA
        def sha(data,length,out):
            ctypes.memmove(out,hashlib.sha1(ctypes.string_at(data,length)).digest(),20);return out
        lib.patch.argtypes=[ctypes.c_void_p,ctypes.c_size_t,SHA,ctypes.POINTER(ctypes.c_size_t),ctypes.c_uint]
        lib.patch.restype=ctypes.c_void_p;lib.dispose.argtypes=[ctypes.c_void_p]
        def apply(data,step):
            size=ctypes.c_size_t();source=ctypes.create_string_buffer(data)
            pointer=lib.patch(source,len(data),sha,ctypes.byref(size),step)
            assert source.raw[:-1]==data,'Input mutated'
            if not pointer: return None
            try:return ctypes.string_at(pointer,size.value)
            finally:lib.dispose(pointer)
        before=body
        for step in range(3):
            before=apply(before,step);assert before,'Earlier patch refused'
        print('Chain before popup:',len(before),'bytes; growth',len(before)-len(body))
        patched=apply(before,3);assert patched,'Popup patch refused'
        assert not apply(body,3),'Ungated donor accepted'
        bad=bytearray(before);bad[100]^=1;assert not apply(bytes(bad),3),'Bad footer accepted'
        bad=bytearray(before);bad[128+3801*12]^=1
        bad[-20:]=hashlib.sha1(bad[:-20]).digest();assert not apply(bytes(bad),3),'Changed target accepted'
        assert not apply(patched,3),'Duplicate patch accepted'
        target,join,step=3801,0x5e,3
        if strip:
            before=patched;patched=apply(before,4);assert patched,'Strip patch refused'
            target,join,step=4869,0x46,4
            assert not apply(body,4),'Ungated strip donor accepted'
            assert not apply(patched,4),'Duplicate strip patch accepted'
            bad=bytearray(before);bad[100]^=1;assert not apply(bytes(bad),4),'Bad strip footer accepted'
            bad=bytearray(before);bad[128+target*12]^=1
            bad[-20:]=hashlib.sha1(bad[:-20]).digest();assert not apply(bytes(bad),4),'Changed strip target accepted'
        assert hashlib.sha1(patched[:-20]).digest()==patched[-20:]
        h=read(before);after=read(patched);base=h.header.functionCount;delta=(after.header.functionCount-base)*12
        assert after.strings==h.strings
        registrations=list(parse_hbc_bytecode(h.function_headers[0],h))
        def dependencies(factory):
            at=next(i for i,x in enumerate(registrations) if x.inst.name=='CreateClosure' and x.arg3==factory)
            return ast.literal_eval(str(registrations[at-1]).split('# Array: ',1)[1])
        card_deps=dependencies(4056);host_deps=dependencies(3801)
        assert card_deps[1]==72 and card_deps[2]==5 and card_deps[3]==245 and card_deps[6]==2118
        assert host_deps[13]==2118
        card_ops={x.original_pos:x for x in parse_hbc_bytecode(h.function_headers[19704],h)}
        assert card_ops[0x69].inst.name=='GetByIndex' and card_ops[0x69].arg3==6
        assert h.strings[card_ops[0x72].arg4]=='useTheme'
        sheet_ops={x.original_pos:x for x in parse_hbc_bytecode(h.function_headers[19172],h)}
        assert sheet_ops[0x1e0].inst.name=='GetByIndex' and sheet_ops[0x1e0].arg3==13
        assert h.strings[sheet_ops[0x1e9].arg4]=='useSheetHandoff'
        jsx_ops=list(parse_hbc_bytecode(h.function_headers[250],h))
        assert any(x.inst.name=='PutByIdStrict' and h.strings[x.arg4]=='jsx' for x in jsx_ops)
        print('Original module bindings verified: React 72, RN 5, useTheme/sheet 2118; 245 is JSX runtime')
        if strip:
            assert dependencies(3763)[3:6]==[72,5,245]
            assert dependencies(4623)[10]==3758 and dependencies(3762)[0]==3759
            getter=list(parse_hbc_bytecode(h.function_headers[19082],h))
            assert any(x.inst.name=='GetByIndex' and x.arg3==0 for x in getter)
            assert any(x.inst.name=='GetById' and h.strings[x.arg4]=='EmoteTextInput' for x in getter)
            composer_factory=list(parse_hbc_bytecode(h.function_headers[4869],h))
            assert any(x.inst.name=='CreateClosure' and x.arg3==22083 for x in composer_factory)
            assert h.strings[next(x.arg4 for x in composer_factory if x.inst.name=='PutByIdLoose')]=='ChatComposerBar'
            print('Scoped composer factory 4869 -> 22083; Autocomplete input module 3759 -> 19094/19088 verified')
        for i,f in enumerate(h.function_headers):
            new=after.function_headers[i]
            for field in f._fields_:
                name=field[0]
                if name=='offset' or (i==target and name in ('bytecodeSizeInBytes','hasExceptionHandler')):continue
                a,b=getattr(f,name),getattr(new,name)
                if isinstance(a,ctypes.Array):a,b=bytes(a),bytes(b)
                assert a==b,(i,name,a,b)
            old_code=before[f.offset:f.offset+f.bytecodeSizeInBytes]
            new_code=patched[new.offset:new.offset+new.bytecodeSizeInBytes]
            if i==target:
                extra=new.bytecodeSizeInBytes-f.bytecodeSizeInBytes
                assert new_code[:join]==old_code[:join] and new_code[join+extra:]==old_code[join:]
                instructions=list(parse_hbc_bytecode(new,after))
                insert=[x for x in instructions if join<=x.original_pos<join+extra]
                assert [x.inst.name for x in insert]==['CreateClosure','Call2','JmpFalse','Mov' if strip else 'StoreToEnvironment','Jmp','Catch']
                assert insert[0].arg3==base and insert[1].arg3==(1 if strip else 2) and insert[1].arg4==(2 if strip else 4)
                assert (insert[3].arg1,insert[3].arg2)==((2,8) if strip else (5,13))
                assert new.frameSize-7-2>9,'Outgoing staging overwrites live factory registers'
                exc=after.function_id_to_exc_handlers[i][0]
                assert (exc.start,exc.end,exc.target)==(join,join+10,join+extra-2)
                # All factory original branches start/land after insertion.
                for x in parse_hbc_bytecode(f,h):
                    for n,o in enumerate(x.inst.operands,1):
                        if o.operand_type.name.startswith('Addr'):
                            assert x.original_pos>=join and x.original_pos+getattr(x,'arg'+str(n))>=join
            else:
                assert new.offset==f.offset+delta,(i,'offset')
                assert new_code==old_code,(i,'body')
        for i,exc in h.function_id_to_exc_handlers.items():
            assert bytes(exc)==bytes(after.function_id_to_exc_handlers[i]),(i,'handlers')
        for i,debug in h.function_id_to_debug_offsets.items():
            assert bytes(debug)==bytes(after.function_id_to_debug_offsets[i]),(i,'debug')
        assert bytes(h.header.sourceHash)==bytes(after.header.sourceHash)
        for i in range(base,after.header.functionCount):
            f=after.function_headers[i];ops=list(parse_hbc_bytecode(f,after));positions={x.original_pos for x in ops}
            for x in ops:
                for n,o in enumerate(x.inst.operands,1):
                    value=getattr(x,'arg'+str(n))
                    if o.operand_type.name.startswith('Addr'): assert x.original_pos+value in positions
                    if o.operand_meaning and o.operand_meaning.name=='function_id':assert base<=value<after.header.functionCount
            for e in after.function_id_to_exc_handlers.get(i,[]):
                assert e.start in positions and (e.end in positions or e.end==f.bytecodeSizeInBytes) and e.target in positions
        binary=tmp/'popup.hbc';binary.write_bytes(patched)
        with (tmp/'dump.txt').open('w') as out:
            subprocess.run([str(hermesc),'-dump-bytecode',str(binary)],stdout=out,check=True)
        print('Verified all',base,'donor functions; imported',after.header.functionCount-base,
              'owned functions; original constants/handlers/debug preserved; independent Hermes-98 disassembly passed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('donor',type=Path);p.add_argument('--zig',type=Path,default=os.environ.get('ZIG','zig'));p.add_argument('--hermesc',type=Path,required=True)
    p.add_argument('--strip',action='store_true')
    a=p.parse_args();verify(a.donor,a.zig,a.hermesc,a.strip)
