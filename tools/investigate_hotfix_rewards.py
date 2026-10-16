"""Read-only reward-render regression for the three recorded 31.6 donors.

Private inputs are required. Only temporary test bootstraps are substituted;
the selected donor factory, renderer and child bodies remain unchanged. This
does not port Streamside, change admission, package an IPA, or simulate Fabric.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from rn_graft import read, parse_hbc_bytecode
from hermes_dec.parsers.serialized_literal_parser import unpack_slp_array
from validate_rn_snapshot import (
    ROOT, RUNTIME_COMMIT, compile_js, test_entry, native_adapter,
)

DONORS = {
    '31.6': ('262821841498166537',
             '36d85ac4a7f0979ca392415af697a43fe7eb019f7fbfdf84dce18b7a25249cea',
             '20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458',
             4794, 4790, 22089),
    '31.6.1': ('262862021310949730',
               '1ab5c92ba56c72684fc12e9b53c9e4391215fd8beeb7b0bd29807711b7f83364',
               '422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b',
               4725, 4721, 21638),
    '31.6.2': ('262872150334984303',
               '8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186',
               '20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458',
               4794, 4790, 22089),
}
BASE_DEPS = [1, 72, 5, 245, 3480, 4068, 519, 2071, 1846, 3478,
             4791, 3477, 3487, 2085, 4075]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_donor(path, version):
    import plistlib
    build, ipa_sha, body_sha, factory, module, renderer = DONORS[version]
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != ipa_sha:
            raise ValueError('Unrecorded IPA: ' + version)
    with zipfile.ZipFile(path) as archive:
        info = plistlib.loads(archive.read('Payload/Twitch.app/Info.plist'))
        body = archive.read('Payload/Twitch.app/index.ios.bundle')
    if (info['CFBundleShortVersionString'], info['CFBundleVersion']) != (version, build):
        raise ValueError('Version/build mismatch')
    if digest(body) != body_sha or hashlib.sha1(body[:-20]).digest() != body[-20:]:
        raise ValueError('Unrecorded or corrupt Hermes bundle')
    h = read(body)
    if h.header.version != 98:
        raise ValueError('Wrong bytecode format')
    ops = list(parse_hbc_bytecode(h.function_headers[0], h))
    indexes = [i for i, x in enumerate(ops)
               if x.inst.name == 'CreateClosure' and x.arg3 == factory]
    if len(indexes) != 1:
        raise ValueError('Missing/ambiguous factory registration')
    symbol, mod, deps, closure, call = ops[indexes[0]-3:indexes[0]+2]
    if (symbol.inst.name != 'TryGetById' or h.strings[symbol.arg4] != '__d'
            or mod.inst.name != 'LoadConstInt' or mod.arg2 != module
            or not deps.inst.name.startswith('NewArrayWithBuffer')
            or call.inst.name != 'Call4' or call.arg2 != symbol.arg1
            or call.arg4 != closure.arg1 or call.arg5 != mod.arg1
            or call.arg6 != deps.arg1):
        raise ValueError('Changed Metro registration ABI')
    dependencies = [int(s) for s in unpack_slp_array(
        h.literal_values[deps.arg4:], deps.arg3, 98).to_strings(h.strings)]
    if len(dependencies) != len(BASE_DEPS):
        raise ValueError('Changed reward dependency slots')
    factory_ops = list(parse_hbc_bytecode(h.function_headers[factory], h))
    if not any(x.inst.name == 'CreateClosure' and x.arg3 == renderer for x in factory_ops):
        raise ValueError('Changed renderer binding')
    if not any(x.inst.name == 'PutByIdLoose' and
               h.strings[x.arg4] == 'ChannelPointsRewardLine' for x in factory_ops):
        raise ValueError('Changed reward export')
    return body, dependencies


def admission_library(zig, tmp):
    source = tmp/'admission.c'
    source.write_text('''#include "TASRNStripPatch.h"
void *probe(const void *p,size_t n,TASRNSHA1 s,size_t *out,unsigned step){
 if(step==0)return tas_rn_width_patch(p,n,s,out);
 if(step==1)return tas_rn_local_patch(p,n,s,out);
 if(step==2)return tas_rn_composer_patch(p,n,s,out);
 if(step==3)return tas_rn_popup_patch(p,n,s,out);
 return tas_rn_strip_patch(p,n,s,out);}
void dispose(void *p){free(p);}
''')
    library = tmp/'admission.so'
    subprocess.run([str(zig), 'cc', '-shared', '-fPIC', '-Wall', '-Wextra',
                    '-Werror', '-I', str(ROOT/'src'), str(source), '-o', str(library)], check=True)
    lib = ctypes.CDLL(str(library))
    callback = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.c_uint32, ctypes.c_void_p)
    @callback
    def sha(data, size, out):
        ctypes.memmove(out, hashlib.sha1(ctypes.string_at(data, size)).digest(), 20)
        return out
    lib.probe.argtypes = [ctypes.c_void_p, ctypes.c_size_t, callback,
                         ctypes.POINTER(ctypes.c_size_t), ctypes.c_uint]
    lib.probe.restype = ctypes.c_void_p
    lib.dispose.argtypes = [ctypes.c_void_p]
    return lib, sha


def validate(args):
    revision = subprocess.check_output(
        ['git', '-C', str(args.runtime_source), 'rev-parse', 'HEAD'], text=True).strip()
    stamp = json.loads(args.runner.with_suffix('.build.json').read_text())
    if (revision != RUNTIME_COMMIT or stamp['runtime_commit'] != RUNTIME_COMMIT
            or stamp['runner_sha256'] != digest(args.runner.read_bytes())
            or stamp['runner_source_sha256'] != digest(
                (ROOT/'tests/native/hermes_snapshot_runner.cpp').read_bytes())):
        raise ValueError('Pinned Hermes runner/source evidence missing or stale')
    fixture = (ROOT/'tests/fixtures/rn_hotfix_reward_render.js').read_text()
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        native = native_adapter(args.zig, tmp)
        lib, sha = admission_library(args.zig, tmp)
        for version, path in zip(DONORS, (args.baseline, args.hotfix1, args.hotfix2)):
            body, dependencies = load_donor(path, version)
            factory = DONORS[version][3]
            (tmp/'fixture.js').write_text(
                'var _baselineDependencies=' + json.dumps(BASE_DEPS) + ';\n'
                'var _rewardDependencies=' + json.dumps(dependencies) + ';\n' + fixture)
            compile_js(args.hermesc, tmp/'fixture.js', tmp/'fixture.hbc')
            (tmp/'entry.hbc').write_bytes(test_entry(body, args.hermesc, tmp, factory))
            result = subprocess.run([str(args.runner), str(native), str(tmp/'entry.hbc'),
                                     str(tmp/'fixture.hbc')], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(version + ' reward fixture failed: ' + result.stderr)
            print(version + ': eight render cases + retained-cache catalog arrival/loss passed')
            current = body
            sizes = []
            for step in range(5):
                source = ctypes.create_string_buffer(current)
                size = ctypes.c_size_t(99)
                ptr = lib.probe(source, len(current), sha, ctypes.byref(size), step)
                if source.raw[:-1] != current:
                    raise ValueError('Probe mutated input')
                if not ptr:
                    if version != '31.6.1' or step != 0 or size.value != 0:
                        raise ValueError('Unexpected chain refusal')
                    break
                try:
                    current = ctypes.string_at(ptr, size.value)
                finally:
                    lib.dispose(ptr)
                if version == '31.6.1':
                    raise ValueError('Current production chain admitted the older bundle')
                if hashlib.sha1(current[:-20]).digest() != current[-20:]:
                    raise ValueError('Invalid output footer')
                sizes.append(len(current))
            print(version + ': production stages ' + (str(sizes) if sizes else
                  'width refused unchanged, result length zero; later stages not reached'))
    print('Host Hermes only. No live store, PubSub, UIKit/Fabric, pixels or IPA produced.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('baseline', 'hotfix1', 'hotfix2', 'hermesc', 'runner', 'runtime-source', 'zig'):
        parser.add_argument('--' + flag, type=Path, required=True)
    validate(parser.parse_args())
