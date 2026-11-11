"""Build on configured macOS via SSH; keep donor, Git and packaging on Ubuntu.

Uses SSH's existing configuration. Never opens, copies or changes key files.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile


def compile_apple(root,directory,mode,proof,revision,host):
    if not re.fullmatch(r'[A-Za-z0-9_.@-]+',host):raise ValueError('Invalid SSH host alias')
    inputs={}
    names=['native/'+name for name in ['SSNCore.c','SSNCore.h','SSNIntegration.c','SSNIntegration.h',
           'SSNAccount.c','SSNSwiftABI.h','SSNObjC.h','SSNNativeBridge.h','SSNNativeBridge.m']]
    names += [str(p.relative_to(root)) for p in sorted((root/'native/swift').glob('*.swift'))]
    names += ['tools/native_frontend/apple_worker.py','tests/native_frontend/abi_calls.c',
              'tests/native_frontend/swift/ModelsTests.swift']
    for name in names:inputs[name]=(root/name).read_bytes()
    inputs['generated/SSNBuild.h']=(directory/'SSNBuild.h').read_bytes()
    config=dict(mode=mode,proof_id=proof,source_revision=revision,
                inputs={n:hashlib.sha256(b).hexdigest() for n,b in inputs.items()})
    inputs['config.json']=(json.dumps(config,indent=2)+'\n').encode()
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
        for name,data in inputs.items():
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o644
            tar.addfile(entry,io.BytesIO(data))
    remote=subprocess.check_output(['ssh',host,'mktemp -d /tmp/streamside-native.XXXXXX'],text=True).strip()
    if not re.fullmatch(r'/tmp/streamside-native\.[A-Za-z0-9]+',remote):raise ValueError('Unexpected remote workspace')
    print('Apple compile workspace: '+remote,flush=True)
    subprocess.run(['ssh',host,'tar -xzf - -C '+shlex.quote(remote)],input=buffer.getvalue(),check=True)
    result=subprocess.run(['ssh',host,'python3 '+shlex.quote(remote+'/tools/native_frontend/apple_worker.py')+' '+shlex.quote(remote)],
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # Preserve compiler output even on failure, and retain failed remote workspace.
    (directory/'remote-command.log').write_bytes(result.stdout)
    payload=subprocess.check_output(['ssh',host,"tar -czf - --exclude='*.c.o' --exclude='*.m.o' --exclude='SwiftFrontend.o' --exclude='models-tests' -C "+shlex.quote(remote)+' output'])
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as tar:
        for item in tar.getmembers():
            name=Path(item.name)
            if item.isfile() and len(name.parts)==2 and name.parts[0]=='output':
                (directory/name.name).write_bytes(tar.extractfile(item).read())
    if result.returncode:
        raise RuntimeError('Apple compilation failed; evidence in '+str(directory)+'; remote workspace retained at '+remote)
    subprocess.run(['ssh',host,'rm -rf '+shlex.quote(remote)],check=True)
    return json.loads((directory/'compiler.json').read_text())
