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


def verify(donor, zig, hermesc=None, local=False, composer=False):
    from hermes_dec.parsers.hbc_file_parser import HBCReader as ProvisionalReader
    from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
    class HBCReader(ProvisionalReader):
        def get_large_func_header_reader(self):
            reader=super().get_large_func_header_reader()
            if self.header.version!=98:return reader
            # hermes-dec 0.1.7's DEVELOPMENT-98 schema places flags at 35.
            # Exact donor and Hermes-98 compiler instead put flags at 36,
            # with a 40-byte full header. Keep this correction analysis-only.
            fields=list(reader._fields_)
            at=next(i for i,f in enumerate(fields) if f[0]=='prohibitInvoke')
            fields.insert(at,('_cache_padding',ctypes.c_uint8))
            fields.append(('_tail_padding',ctypes.c_uint8*3))
            return type('Hermes98FullHeader',(ctypes.LittleEndianStructure,),
                        {'_pack_':True,'_layout_':'ms','_fields_':fields})
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
        source.write_text('''#include "TASRNComposerPatch.h"
void *patch(const void *p,size_t n,TASRNSHA1 sha,size_t *out) {
 return tas_rn_width_patch(p,n,sha,out);
}
void *local_patch(const void *p,size_t n,TASRNSHA1 sha,size_t *out) {
 return tas_rn_local_patch(p,n,sha,out);
}
size_t local_code(unsigned char *p){return tas_rn_local_code(p);}
void *composer_patch(const void *p,size_t n,TASRNSHA1 sha,size_t *out) {
 return tas_rn_composer_patch(p,n,sha,out);
}
size_t composer_code(unsigned char *p){return tas_rn_composer_code(p);}
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
            local_extra=lib.local_code(ctypes.create_string_buffer(256))
            pointer=lib.local_patch(ctypes.create_string_buffer(patched),len(patched),sha,ctypes.byref(size))
            if not pointer: raise ValueError('Local patch refused admitted width body')
            try: patched=ctypes.string_at(pointer,size.value)
            finally: lib.dispose(pointer)
        composer_base=len(patched)
        composer_extra=0
        if composer:
            lib.composer_patch.argtypes=lib.patch.argtypes
            lib.composer_patch.restype=ctypes.c_void_p
            lib.composer_code.argtypes=[ctypes.c_void_p]
            lib.composer_code.restype=ctypes.c_size_t
            composer_extra=lib.composer_code(ctypes.create_string_buffer(256))
            pointer=lib.composer_patch(ctypes.create_string_buffer(patched),len(patched),sha,ctypes.byref(size))
            if not pointer:raise ValueError('Composer patch refused admitted body')
            try:patched=ctypes.string_at(pointer,size.value)
            finally:lib.dispose(pointer)
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
            # Follow the class method binding, not merely a similar function body.
            methods=list(parse_hbc_bytecode(h.function_headers[3398],h))
            own=next(i for i,x in enumerate(methods) if x.inst.name=='CreateClosure' and x.arg3==34307)
            if "'key': 'onChatEvent'" not in str(methods[own-1]):
                raise ValueError('Ordinary-chat method binding mismatch')
            print('LibraryTmiClient factory 3398: function 34307 bound to onChatEvent')
            print('NativeModules module 16 / factory 20: proxy and classic config routes verified')
        index = 19127
        before, after = h.function_headers[index], changed.function_headers[index]
        for i,(a,b) in enumerate(zip(h.function_headers,changed.function_headers)):
            for field in a._fields_:
                name = field[0]
                targets={index}|({34307} if local else set())|({22083} if composer else set())
                if i in targets and name in ('offset','bytecodeSizeInBytes'): continue
                if local and i==34307 and name in ('frameSize','hasExceptionHandler'): continue
                if composer and i==22083 and name=='hasExceptionHandler':continue
                left,right=getattr(a,name),getattr(b,name)
                if isinstance(left,ctypes.Array):left,right=bytes(left),bytes(right)
                if left != right: raise ValueError(f'Unexpected function header {i}/{name}')
        if h.strings != changed.strings: raise ValueError('Constant pool changed')
        for identity,handlers in h.function_id_to_exc_handlers.items():
            if bytes(handlers)!=bytes(changed.function_id_to_exc_handlers[identity]):
                raise ValueError('Original exception table changed')
        for identity,offsets in h.function_id_to_debug_offsets.items():
            if bytes(offsets)!=bytes(changed.function_id_to_debug_offsets[identity]):
                raise ValueError('Original debug metadata changed')
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
            small=128+34307*12
            allowed.update(range(small,small+12))
            old_header,new_header=h.function_headers[34307],changed.function_headers[34307]
            instructions={x.original_pos:x for x in parse_hbc_bytecode(new_header,changed)}
            local_branches=0
            for ins in parse_hbc_bytecode(old_header,h):
                at=ins.original_pos+3*(ins.original_pos>=0x35)+local_extra*(ins.original_pos>=0x6a)
                current=instructions[at]
                old=body[old_header.offset+ins.original_pos:old_header.offset+ins.next_pos]
                new=patched[new_header.offset+at:new_header.offset+current.next_pos]
                if ins.original_pos==0x32:
                    if current.inst.name!='JmpFalseLong' or current.arg2!=4:
                        raise ValueError('Null gate must widen without changing its register')
                elif old!=new: raise ValueError('Unexpected local instruction change')
                for arg,operand in enumerate(ins.inst.operands,1):
                    if not operand.operand_type.name.startswith('Addr'): continue
                    target=ins.original_pos+getattr(ins,f'arg{arg}')
                    expected=target+3*(target>=0x35)+local_extra*(target>0x6a)
                    actual=current.original_pos+getattr(current,f'arg{arg}')
                    if actual!=expected or actual not in instructions: raise ValueError('Local branch target mismatch')
                    local_branches+=1
            if new_header.offset!=width_size-20 or new_header.bytecodeSizeInBytes!=121+3+local_extra:
                raise ValueError('Unexpected local function extent')
            if new_header.frameSize!=21 or not new_header.hasExceptionHandler:
                raise ValueError('Own-preview calls require safe frame and exception containment')
            handlers=changed.function_id_to_exc_handlers[34307]
            expected=(0x6d,0x6d+local_extra-7,0x6d+local_extra-2)
            if len(handlers)!=1 or (handlers[0].start,handlers[0].end,handlers[0].target)!=expected:
                raise ValueError('Own-preview exception interval mismatch')
            if instructions[expected[2]].inst.name!='Catch' or instructions[expected[1]].inst.name!='JmpLong':
                raise ValueError('Normal and exception joins must preserve original emission')
            # Hermes-98 writes this/args then seven metadata slots at frame end.
            # Every injected call source/live local must stay below those slots.
            for ins in instructions.values():
                if not 0x6d<=ins.original_pos<expected[1] or ins.inst.name not in ('Call2','Call4'):continue
                argc=2 if ins.inst.name=='Call2' else 4
                outgoing=new_header.frameSize-7-argc
                sources=[getattr(ins,f'arg{i}') for i in range(2,argc+3)]
                if min(outgoing,10)<=max(sources):
                    raise ValueError('Injected call overlaps its own outgoing frame')
            print('Frame 21: outgoing call writes isolated from r0..r9; one fail-open Catch verified')
            print(f'Library own-event function 34307: 121 -> {121+3+local_extra}; {local_branches} original branch targets verified')
        if composer:
            allowed.update(range(128+22083*12,140+22083*12))
            old_header,new_header=h.function_headers[22083],changed.function_headers[22083]
            instructions={x.original_pos:x for x in parse_hbc_bytecode(new_header,changed)}
            original_ops=list(parse_hbc_bytecode(old_header,h))
            if str(next(x for x in original_ops if x.original_pos==0xa1)).find("'emoteMap'")<0:
                raise ValueError('Composer preview-map join mismatch')
            branches=0
            for ins in original_ops:
                at=ins.original_pos+composer_extra*(ins.original_pos>=0xa7)
                current=instructions[at]
                old=body[old_header.offset+ins.original_pos:old_header.offset+ins.next_pos]
                new=patched[new_header.offset+at:new_header.offset+current.next_pos]
                if old!=new:raise ValueError('Original composer instruction changed')
                for arg,operand in enumerate(ins.inst.operands,1):
                    if not operand.operand_type.name.startswith('Addr'):continue
                    target=ins.original_pos+getattr(ins,f'arg{arg}')
                    actual=current.original_pos+getattr(current,f'arg{arg}')
                    if actual!=target+composer_extra*(target>=0xa7) or actual not in instructions:
                        raise ValueError('Composer branch relocation mismatch')
                    branches+=1
            if new_header.offset!=composer_base-20 or new_header.frameSize!=97:
                raise ValueError('Composer frame/extent changed')
            expected=(0xa7,0xa7+composer_extra-9,0xa7+composer_extra-4)
            handlers=changed.function_id_to_exc_handlers[22083]
            if len(handlers)!=1 or (handlers[0].start,handlers[0].end,handlers[0].target)!=expected:
                raise ValueError('Composer handler interval mismatch')
            if instructions[expected[2]].inst.name!='Catch' or instructions[expected[1]].inst.name!='JmpLong':
                raise ValueError('Composer exception containment mismatch')
            restore=instructions[0xa7+composer_extra-2]
            if restore.inst.name!='LoadConstUndefined' or restore.arg1!=2:
                raise ValueError('Composer original undefined must be restored')
            live={6,7,8,11,12,17,18,23,26,31,32,33,36,37,43,44,46,47,49,50,56,57,62,74,75,76}
            for ins in instructions.values():
                if not 0xa7<=ins.original_pos<expected[1] or ins.inst.name not in ('Call2','Call4'):continue
                argc=2 if ins.inst.name=='Call2' else 4
                staging=set(range(new_header.frameSize-7-argc,new_header.frameSize))
                sources={getattr(ins,f'arg{i}') for i in range(2,argc+3)}
                if staging&(live|sources):raise ValueError('Composer call clobbers live state')
            print(f'Scoped composer 22083: unchanged frame 97; {branches} original branch targets and fail-open Catch verified')
        modifications = [i for i,(a,b) in enumerate(zip(body[:-20],patched)) if a != b]
        if set(modifications)-allowed: raise ValueError('Unexpected original-body change')
        expected_length=len(body)+947+2*extra
        if local: expected_length=((expected_length-20+121+3+local_extra+3)&~3)+40+16+20
        if composer:expected_length=((expected_length-20+6240+composer_extra+3)&~3)+40+16+20
        if len(patched) != expected_length: raise ValueError('Unexpected patch extent')
        if hermesc:
            if local:
                # Confirm call-space accounting with the SAME Hermes-98
                # compiler, independently of the hand-written patch/model.
                probe=root/'frame.js'
                probe.write_text('''function preview(event) {
 var line=this.translate(event); if(!line)return;
 try {var m=global.__r(16).default.buildLocalEcho;
 var x=m.buildLocalEcho(line.body,line.channel,line.emotes);
 if(x)line.emotes=line.emotes.concat(x);}catch(e){}
 this.emitLine(line);
}''')
                binary=root/'frame.hbc'
                subprocess.run([hermesc,'-O','-emit-binary','-out',str(binary),str(probe)],check=True)
                compiled=HBCReader();compiled.read_whole_file(io.BytesIO(binary.read_bytes()))
                if compiled.header.version!=98:raise ValueError('Call-frame probe requires Hermes-98')
                header=compiled.function_headers[1]
                ops=list(parse_hbc_bytecode(header,compiled))
                highest=max(getattr(ins,f'arg{i}') for ins in ops
                            for i,operand in enumerate(ins.inst.operands,1)
                            if operand.operand_type.name.startswith('Reg'))
                if not any(ins.inst.name=='Call4' for ins in ops) or header.frameSize-highest-1!=11:
                    raise ValueError('Compiler disagrees with eleven-slot Call4 reservation')
                if not header.hasExceptionHandler:raise ValueError('Compiler exception probe missing handler')
                print('Independent Hermes-98 compiler probe confirms eleven outgoing Call4 slots')
            # Hermes' disassembler reads the rewritten container independently.
            fixture = root/'patched.hbc'; fixture.write_bytes(patched)
            with (root/'hermes.dump').open('wb') as output:
                subprocess.run([hermesc,'-b','-dump-bytecode',str(fixture)],stdout=output,check=True)
            if local:
                identity=-1;own=[]
                with (root/'hermes.dump').open(errors='replace') as output:
                    for line in output:
                        if line.startswith(('Function<','NCFunction<')):identity+=1
                        if identity==34307:own.append(line)
                        if identity>34307:break
                text=''.join(own)
                if not all(key in text for key in ('21 registers','Catch','Exception Handlers:','start =','target =')):
                    raise ValueError('Hermes-98 did not recognize own-preview frame and handler')
                print('Independent Hermes-98 disassembly recognizes frame 21 and own-preview Catch table')
            if composer:
                identity=-1;own=[]
                with (root/'hermes.dump').open(errors='replace') as output:
                    for line in output:
                        if line.startswith(('Function<','NCFunction<')):identity+=1
                        if identity==22083:own.append(line)
                        if identity>22083:break
                text=''.join(own)
                if not all(key in text for key in ('97 registers','Catch','Exception Handlers:','emoteMap')):
                    raise ValueError('Hermes-98 did not recognize composer frame/handler')
                print('Independent Hermes-98 disassembly recognizes composer preview map and Catch table')
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
    parser.add_argument('--composer',action='store_true',help='Also verify scoped text-box previews')
    args = parser.parse_args()
    if not args.zig: parser.error('Zig required')
    verify(args.donor,args.zig,args.hermesc,args.local,args.composer)
