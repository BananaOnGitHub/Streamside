"""Read-only verification of the exact Twitch 31.5 in-memory width patch.

Requires Zig 0.14 and hermes-dec 0.1.7 (analysis only, not build dependencies).
Optionally pass Hermes-98 hermesc for an independent disassembler check.
No donor code or modified bundle is saved to the repository or output IPA.
Does not execute Twitch or prove live device layout/animation.
"""
import argparse
import ctypes
import hashlib
import io
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DONOR_SHA256 = '718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641'
BODY_SHA256 = '422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b'


def verify(donor, zig, hermesc=None, local=False):
    from hermes_dec.parsers.hbc_file_parser import HBCReader
    from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
    with donor.open('rb') as handle:
        if hashlib.file_digest(handle,'sha256').hexdigest() != DONOR_SHA256:
            raise ValueError('Not the verified Twitch 31.5 donor')
    with zipfile.ZipFile(donor) as archive:
        body = archive.read('Payload/Twitch.app/index.ios.bundle')
    if hashlib.sha256(body).hexdigest() != BODY_SHA256:
        raise ValueError('Unexpected embedded body')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'patch.c'
        source.write_text('''#include "TASRNLocalEchoPatch.h"
void *patch(const void *p,size_t n,TASRNSHA1 sha,size_t *out) {
 return tas_rn_width_patch(p,n,sha,out);
}
void *local_patch(const void *p,size_t n,TASRNSHA1 sha,size_t *out) {
 return tas_rn_local_patch(p,n,sha,out);
}
size_t local_code(unsigned char *p){return tas_rn_local_code(p);}
void dispose(void *p){free(p);}
size_t code(unsigned char *p,unsigned style){return tas_rn_width_code(p,style);}
''')
        library = root/'patch.so'
        subprocess.run([zig,'cc','-shared','-fPIC','-Wall','-Wextra','-Werror',
            '-I',str(ROOT/'src'),str(source),'-o',str(library)],check=True)
        lib = ctypes.CDLL(str(library))
        SHA = ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p)
        @SHA
        def sha(data,length,out):
            ctypes.memmove(out,hashlib.sha1(ctypes.string_at(data,length)).digest(),20)
            return out
        lib.patch.argtypes = [ctypes.c_void_p,ctypes.c_size_t,SHA,ctypes.POINTER(ctypes.c_size_t)]
        lib.patch.restype = ctypes.c_void_p
        lib.dispose.argtypes = [ctypes.c_void_p]
        lib.code.argtypes = [ctypes.c_void_p,ctypes.c_uint]
        lib.code.restype = ctypes.c_size_t
        original = ctypes.create_string_buffer(body)
        size = ctypes.c_size_t()
        pointer = lib.patch(original,len(body),sha,ctypes.byref(size))
        if not pointer: raise ValueError('Production patch refused exact donor')
        try: patched = ctypes.string_at(pointer,size.value)
        finally: lib.dispose(pointer)
        width_size=len(patched)
        local_extra=0
        if local:
            lib.local_patch.argtypes=lib.patch.argtypes
            lib.local_patch.restype=ctypes.c_void_p
            lib.local_code.argtypes=[ctypes.c_void_p]
            lib.local_code.restype=ctypes.c_size_t
            local_extra=lib.local_code(ctypes.create_string_buffer(96))
            pointer=lib.local_patch(ctypes.create_string_buffer(patched),len(patched),sha,ctypes.byref(size))
            if not pointer: raise ValueError('Local patch refused admitted width body')
            try: patched=ctypes.string_at(pointer,size.value)
            finally: lib.dispose(pointer)
        if original.raw[:-1] != body: raise ValueError('Original body mutated')
        if hashlib.sha1(patched[:-20]).digest() != patched[-20:]: raise ValueError('Bad patched footer')
        h, changed = HBCReader(), HBCReader()
        h.read_whole_file(io.BytesIO(body)); changed.read_whole_file(io.BytesIO(patched))
        if local:
            # Exact Metro registration: NativeModules factory 20 is module 16.
            # Verify the donor lookup instead of assuming a bridge global exists.
            registration=list(parse_hbc_bytecode(h.function_headers[0],h))
            at=next(i for i,x in enumerate(registration)
                    if x.inst.name=='CreateClosure' and x.arg3==20)
            identity=registration[at-2]
            if identity.inst.name!='LoadConstUInt8' or identity.arg1!=6 or identity.arg2!=16:
                raise ValueError('NativeModules Metro identity mismatch')
            call=registration[at+1]
            if call.inst.name!='Call4' or call.arg4!=4 or call.arg5!=6:
                raise ValueError('NativeModules Metro registration mismatch')
            factory=list(parse_hbc_bytecode(h.function_headers[20],h))
            keys={x.arg4 for x in factory if x.inst.name in ('GetById','TryGetById')}
            if not {51393,55620}.issubset(keys):
                raise ValueError('NativeModules proxy/config routes not present')
            for identity,value in [(18843,'__r'),(110,'default'),(20058,'buildLocalEcho')]:
                if h.strings[identity]!=value: raise ValueError('Local lookup constant mismatch')
            print('NativeModules module 16 / factory 20: proxy and classic config routes verified')
        index = 19127
        before, after = h.function_headers[index], changed.function_headers[index]
        for i,(a,b) in enumerate(zip(h.function_headers,changed.function_headers)):
            for field in a._fields_:
                name = field[0]
                if i in ({index,34222} if local else {index}) and name in ('offset','bytecodeSizeInBytes'): continue
                if getattr(a,name) != getattr(b,name): raise ValueError(f'Unexpected function header {i}/{name}')
        if h.strings != changed.strings: raise ValueError('Constant pool changed')
        segment = ctypes.create_string_buffer(192)
        extra = lib.code(segment,13)
        def instruction_position(pos):
            return pos + extra*(pos >= 0xd0) + extra*(pos >= 0x238)
        def target_position(pos):
            return pos + extra*(pos > 0xd0) + extra*(pos > 0x238)
        new_instructions = {x.original_pos:x for x in parse_hbc_bytecode(after,changed)}
        branches = 0
        for ins in parse_hbc_bytecode(before,h):
            at = instruction_position(ins.original_pos)
            current = new_instructions[at]
            old = body[before.offset+ins.original_pos:before.offset+ins.next_pos]
            new = patched[after.offset+at:after.offset+current.next_pos]
            if old != new: raise ValueError(f'Original instruction changed at {ins.original_pos:x}')
            for arg,operand in enumerate(ins.inst.operands,1):
                if not operand.operand_type.name.startswith('Addr'): continue
                target = ins.original_pos+getattr(ins,f'arg{arg}')
                actual = current.original_pos+getattr(current,f'arg{arg}')
                if actual != target_position(target): raise ValueError(f'Branch relocation needed at {ins.original_pos:x}')
                if actual not in new_instructions: raise ValueError('Branch misses instruction boundary')
                branches += 1
        allowed = {32,33,34,35}
        large = 26954740
        allowed.update(range(large,large+4)); allowed.update(range(large+12,large+16))
        if local:
            small=128+34222*12
            allowed.update(range(small,small+6))
            old_header,new_header=h.function_headers[34222],changed.function_headers[34222]
            instructions={x.original_pos:x for x in parse_hbc_bytecode(new_header,changed)}
            local_branches=0
            for ins in parse_hbc_bytecode(old_header,h):
                at=ins.original_pos+local_extra*(ins.original_pos>=0x2a6)
                current=instructions[at]
                old=body[old_header.offset+ins.original_pos:old_header.offset+ins.next_pos]
                new=patched[new_header.offset+at:new_header.offset+current.next_pos]
                if ins.original_pos in (8,0x13):
                    expected=bytearray(old)
                    struct.pack_into('<i',expected,1,struct.unpack_from('<i',old,1)[0]+local_extra)
                    if bytes(expected)!=new: raise ValueError('Incorrect null-return branch relocation')
                elif old!=new: raise ValueError('Unexpected local instruction change')
                for arg,operand in enumerate(ins.inst.operands,1):
                    if not operand.operand_type.name.startswith('Addr'): continue
                    target=ins.original_pos+getattr(ins,f'arg{arg}')
                    expected=target+local_extra*(target>=0x2a6)
                    actual=current.original_pos+getattr(current,f'arg{arg}')
                    if actual!=expected or actual not in instructions: raise ValueError('Local branch target mismatch')
                    local_branches+=1
            if new_header.offset!=width_size-20 or new_header.bytecodeSizeInBytes!=684+local_extra:
                raise ValueError('Unexpected local function extent')
            print(f'Local preview function 34222: 684 -> {684+local_extra}; {local_branches} original branch targets verified')
        modifications = [i for i,(a,b) in enumerate(zip(body[:-20],patched)) if a != b]
        if set(modifications)-allowed: raise ValueError('Unexpected original-body change')
        if len(patched) != len(body)+947+2*extra+(684+local_extra if local else 0): raise ValueError('Unexpected patch extent')
        if hermesc:
            # Hermes' disassembler reads the rewritten container independently.
            fixture = root/'patched.hbc'; fixture.write_bytes(patched)
            with (root/'hermes.dump').open('wb') as output:
                subprocess.run([hermesc,'-b','-dump-bytecode',str(fixture)],stdout=output,check=True)
        print(f'Exact donor admitted; function {index}: {before.bytecodeSizeInBytes} -> {after.bytecodeSizeInBytes} bytes')
        print(f'{branches} original branch targets and all other function headers preserved')
        print(f'{len(modifications)} original-body bytes changed, solely in length and target header; footer valid')
        print('Static donor validation passed; new local-preview device execution remains pending' if local else
              'Wrapper/image overrides verified before layout')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('donor',type=Path)
    parser.add_argument('--zig',default=os.environ.get('ZIG') or shutil.which('zig'))
    parser.add_argument('--hermesc')
    parser.add_argument('--local',action='store_true',help='Also verify the own-preview patch')
    args = parser.parse_args()
    if not args.zig: parser.error('Zig required')
    verify(args.donor,args.zig,args.hermesc,args.local)
