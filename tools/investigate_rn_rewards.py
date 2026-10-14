"""Reproduce reward render decisions in the exact 31.6 donor and build-8 HBC.

Optional investigation utility, separate from CI/build gates. Requires a private
donor and the pinned host Hermes runner. Runs the production patch chain into a
temporary test bundle; does not edit repository source or package an app.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from rn_graft import read
from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
from hermes_dec.parsers.serialized_literal_parser import unpack_slp_array
from validate_rn_snapshot import ROOT, DONOR_SHA, RUNTIME_COMMIT, compile_js, test_entry, patch_chain
from validate_chat_trace import adapter, graft

CANDIDATE_SHA='77117499e3f6116a4001866885ad2ebbe96493d2b0bd5ba7a5f2fc3f31d9799b'

def bundle(path):
    if path.suffix.lower()!='.ipa':
        return path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        names=[name for name in archive.namelist() if name.startswith('Payload/') and name.endswith('.app/index.ios.bundle')]
        if len(names)!=1:
            raise ValueError('Expected exactly one app Hermes bundle')
        return archive.read(names[0])

def validate(args):
    donor=bundle(args.donor)
    if hashlib.sha256(donor).hexdigest()!=DONOR_SHA:
        raise ValueError('Requires the recorded original Twitch 31.6 donor')
    revision=subprocess.check_output(['git','-C',str(args.runtime_source),'rev-parse','HEAD'],text=True).strip()
    stamp=json.loads(args.runner.with_suffix('.build.json').read_text())
    if revision!=RUNTIME_COMMIT or stamp['runtime_commit']!=RUNTIME_COMMIT or stamp['runner_sha256']!=hashlib.sha256(args.runner.read_bytes()).hexdigest() or stamp['runner_source_sha256']!=hashlib.sha256((ROOT/'tests/native/hermes_snapshot_runner.cpp').read_bytes()).hexdigest():
        raise ValueError('Requires the verified pinned Hermes runner')
    original=read(donor)
    instructions=list(parse_hbc_bytecode(original.function_headers[0],original))
    positions=[i for i,x in enumerate(instructions) if x.inst.name=='CreateClosure' and x.arg3==4794]
    if len(positions)!=1:
        raise ValueError('Reward factory registration missing or ambiguous')
    i=positions[0];module,deps=instructions[i-2:i]
    if module.inst.name!='LoadConstInt' or module.arg2!=4790 or not deps.inst.name.startswith('NewArrayWithBuffer'):
        raise ValueError('Unexpected reward factory registration')
    dependencies=[int(value) for value in unpack_slp_array(original.literal_values[deps.arg4:],deps.arg3,98).to_strings(original.strings)]
    with tempfile.TemporaryDirectory() as folder:
        tmp=Path(folder);native=adapter(args.zig,tmp)
        candidate=graft(args.zig,patch_chain(args.zig,donor,tmp),tmp)
        if hashlib.sha256(candidate).hexdigest()!=CANDIDATE_SHA:
            raise ValueError('Patch output differs from the recorded build-8 diagnostic HBC')
        patched=read(candidate)
        for fid in (4794,22060,22089,35389,38552,38553,45065):
            a,b=original.function_headers[fid],patched.function_headers[fid]
            if donor[a.offset:a.offset+a.bytecodeSizeInBytes]!=candidate[b.offset:b.offset+b.bytecodeSizeInBytes]:
                raise ValueError('Reward path body changed: '+str(fid))
        fixture='var _rewardDependencies='+json.dumps(dependencies)+';\n'+(ROOT/'tests/fixtures/rn_reward_render.js').read_text()
        (tmp/'fixture.js').write_text(fixture)
        compile_js(args.hermesc,tmp/'fixture.js',tmp/'fixture.hbc')
        for name,body in (('original',donor),('build-8',candidate)):
            (tmp/'entry.hbc').write_bytes(test_entry(body,args.hermesc,tmp,entry_id=4794))
            result=subprocess.run([str(args.runner),str(native),str(tmp/'entry.hbc'),str(tmp/'fixture.hbc')],text=True,capture_output=True)
            if result.returncode:
                raise RuntimeError(name+' renderer fixture failed: '+result.stderr)
            print(name+': eight reward renderer scenarios and catalog arrival/loss with retained memo cache passed in host Hermes')
    print('Seven inspected reward bodies unchanged. No live PubSub, catalog-fetch, list-layout or painted-pixel claim.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('donor','hermesc','runner','runtime-source','zig'):
        parser.add_argument('--'+flag,type=Path,required=True)
    validate(parser.parse_args())
