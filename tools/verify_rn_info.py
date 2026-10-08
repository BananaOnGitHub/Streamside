"""Verify diagnostic RN info prefixes against the exact donor and Hermes 98.

Run verify_rn_width.py --local --composer separately for the production chain.
This check then proves the diagnostic step preserves that complete chain and
every original branch/body, including the already working incoming width.
It does not establish device execution or popup presentation.
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
from verify_rn_width import ROOT, DONOR_SHA256, BODY_SHA256

TARGETS = {19127: 41, 43823: 24, 19174: 28, 19172: 46, 19704: 95}


def verify(donor, zig, hermesc):
    from hermes_dec.parsers.hbc_file_parser import HBCReader as Reader
    from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
    class HBCReader(Reader):
        def get_large_func_header_reader(self):
            reader = super().get_large_func_header_reader()
            fields = list(reader._fields_)
            at = next(i for i, f in enumerate(fields) if f[0] == 'prohibitInvoke')
            fields.insert(at, ('_cache_padding', ctypes.c_uint8))
            fields.append(('_tail_padding', ctypes.c_uint8 * 3))
            return type('Hermes98FullHeader', (ctypes.LittleEndianStructure,),
                        {'_pack_': 1, '_fields_': fields})
    with donor.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != DONOR_SHA256:
            raise ValueError('Unexpected donor')
    with zipfile.ZipFile(donor) as archive:
        body = archive.read('Payload/Twitch.app/index.ios.bundle')
    if hashlib.sha256(body).hexdigest() != BODY_SHA256:
        raise ValueError('Unexpected donor bundle')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / 'info.c'
        source.write_text('''#include "TASRNInfoPatch.h"
void *width(const void*p,size_t n,TASRNSHA1 s,size_t*out){return tas_rn_width_patch(p,n,s,out);}
void *local(const void*p,size_t n,TASRNSHA1 s,size_t*out){return tas_rn_local_patch(p,n,s,out);}
void *composer(const void*p,size_t n,TASRNSHA1 s,size_t*out){return tas_rn_composer_patch(p,n,s,out);}
void *info(const void*p,size_t n,TASRNSHA1 s,size_t*out){return tas_rn_info_patch(p,n,s,out);}
size_t code(unsigned char*p,unsigned seam){return tas_rn_info_code(p,seam);}
void dispose(void*p){free(p);}
''')
        libpath = root / 'info.so'
        subprocess.run([zig, 'cc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                        '-I', str(ROOT / 'src'), str(source), '-o', str(libpath)], check=True)
        lib = ctypes.CDLL(str(libpath))
        SHA = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)
        @SHA
        def sha(data, length, out):
            ctypes.memmove(out, hashlib.sha1(ctypes.string_at(data, length)).digest(), 20)
            return out
        lib.dispose.argtypes = [ctypes.c_void_p]
        def patch(name, value, expected=True):
            fn = getattr(lib, name)
            fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, SHA, ctypes.POINTER(ctypes.c_size_t)]
            fn.restype = ctypes.c_void_p
            size = ctypes.c_size_t(99)
            pointer = fn(ctypes.create_string_buffer(value), len(value), sha, ctypes.byref(size))
            if not expected:
                if pointer or size.value: raise ValueError('Refusal gate failed')
                return
            if not pointer: raise ValueError(f'{name} refused donor chain')
            try: return ctypes.string_at(pointer, size.value)
            finally: lib.dispose(pointer)
        before = body
        for name in ('width', 'local', 'composer'):
            before = patch(name, before)
        after = patch('info', before)
        patch('info', body, False)
        patch('info', after, False)
        for index in TARGETS:
            damaged = bytearray(before)
            damaged[128 + index * 12] ^= 1
            damaged[-20:] = hashlib.sha1(damaged[:-20]).digest()
            patch('info', bytes(damaged), False)
        if hashlib.sha1(after[:-20]).digest() != after[-20:]:
            raise ValueError('Invalid footer')
        a, b = HBCReader(), HBCReader()
        a.read_whole_file(io.BytesIO(before)); b.read_whole_file(io.BytesIO(after))
        if a.strings != b.strings: raise ValueError('Pool changed')
        if len(a.function_headers) != len(b.function_headers): raise ValueError('Function table changed')
        allowed = set(range(32, 36))
        for index, frame in TARGETS.items():
            allowed.update(range(128 + index * 12, 140 + index * 12))
            old, new = a.function_headers[index], b.function_headers[index]
            prefix = new.bytecodeSizeInBytes - old.bytecodeSizeInBytes
            if new.frameSize != frame: raise ValueError('Unsafe frame size')
            if after[new.offset + prefix:new.offset + new.bytecodeSizeInBytes] != before[old.offset:old.offset + old.bytecodeSizeInBytes]:
                raise ValueError(f'Original body changed: {index}')
            instructions = list(parse_hbc_bytecode(new, b))
            boundaries = {x.original_pos for x in instructions}
            branches = 0
            for ins in instructions:
                for number, operand in enumerate(ins.inst.operands, 1):
                    if not operand.operand_type.name.startswith('Addr'): continue
                    target = ins.original_pos + getattr(ins, f'arg{number}')
                    if target not in boundaries: raise ValueError(f'Invalid branch {index}/{ins.original_pos}')
                    if ins.original_pos >= prefix and target < prefix:
                        raise ValueError('Original branch enters prefix')
                    branches += 1
            handlers = b.function_id_to_exc_handlers[index]
            if len(handlers) != 1: raise ValueError('Missing isolated handler')
            handler = handlers[0]
            if (handler.start, handler.end, handler.target) != (0, prefix-7, prefix-2):
                raise ValueError('Catch extent mismatch')
            print(f'{index}: prefix={prefix}, frame={frame}, {branches} branch destinations valid; original body intact')
        for index, (old, new) in enumerate(zip(a.function_headers, b.function_headers)):
            for field in old._fields_:
                name = field[0]
                if index in TARGETS and name in ('offset', 'bytecodeSizeInBytes', 'frameSize', 'hasExceptionHandler'): continue
                x, y = getattr(old, name), getattr(new, name)
                if isinstance(x, ctypes.Array): x, y = bytes(x), bytes(y)
                if x != y: raise ValueError(f'Unexpected header {index}/{name}')
        for index, handlers in a.function_id_to_exc_handlers.items():
            if bytes(handlers) != bytes(b.function_id_to_exc_handlers[index]):
                raise ValueError('Existing exception handler changed')
        for index, offsets in a.function_id_to_debug_offsets.items():
            if bytes(offsets) != bytes(b.function_id_to_debug_offsets[index]):
                raise ValueError('Debug metadata changed')
        changed = {i for i, (x, y) in enumerate(zip(before[:-20], after)) if x != y}
        if not changed.issubset(allowed): raise ValueError('Unexpected existing-container mutation')
        path = root / 'info.hbc'; path.write_bytes(after)
        with (root / 'info.dump').open('wb') as output:
            subprocess.run([hermesc, '-b', '-dump-bytecode', str(path)], stdout=output, check=True)
        identity = -1; observed = {}
        for line in (root / 'info.dump').read_text().splitlines():
            if line.startswith(('Function<', 'NCFunction<')): identity += 1
            if identity in TARGETS: observed.setdefault(identity, []).append(line)
        for index, frame in TARGETS.items():
            text = '\n'.join(observed[index])
            if not all(value in text for value in (f'{frame} registers', 'Catch', 'Exception Handlers:', 'trace')):
                raise ValueError('Independent disassembler mismatch')
        print('All five seams recognized by independent Hermes-98 disassembler; exact donor validation passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('donor', type=Path)
    parser.add_argument('--zig', default=os.environ.get('ZIG') or shutil.which('zig'))
    parser.add_argument('--hermesc', required=True)
    args = parser.parse_args()
    if not args.zig: parser.error('Zig required')
    verify(args.donor, args.zig, args.hermesc)
