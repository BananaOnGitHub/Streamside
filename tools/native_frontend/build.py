#!/usr/bin/env python3
"""Build the SwiftUI native shell (or preserved UIKit proof) and exact-donor IPA pair."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from macho import inject_load_dylib, loaded_dylibs, encryption_ids, dylib_id
from probes import patch, generate_header
from validate import validate_abi

FRAMEWORK = 'StreamsideNativeProof'
LOAD = f'@rpath/{FRAMEWORK}.framework/{FRAMEWORK}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_identity(frontend="swiftui"):
    h = hashlib.sha256(frontend.encode()+b"\0")
    for directory in ['native', 'tools/native_frontend']:
        for path in sorted((ROOT / directory).rglob('*')):
            if path.is_file() and path.suffix in {'.c', '.h', '.m', '.swift', '.json', '.py', '.tbd'}:
                h.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes())
    return h.hexdigest()


def donor(ipa, plan):
    if sha(ipa.read_bytes()) != plan['donor_sha256']:
        raise ValueError('IPA is not the exact inspected Twitch 32.0 donor')
    with zipfile.ZipFile(ipa) as z:
        if len(set(z.namelist())) != len(z.namelist()) or z.testzip():
            raise ValueError('Damaged or duplicate ZIP entries')
        info = plistlib.loads(z.read('Payload/Twitch.app/Info.plist'))
        if (info['CFBundleIdentifier'], info['CFBundleShortVersionString'], info['CFBundleVersion']) != ('tv.twitch','32.0','263110145453907615'):
            raise ValueError('Donor identity mismatch')
        images = {}
        for name, expected in plan['images'].items():
            entry = 'Payload/Twitch.app/' + ('Twitch' if name == 'Twitch' else f'Frameworks/{name}.framework/{name}')
            data = z.read(entry)
            if sha(data) != expected or any(encryption_ids(data)):
                raise ValueError('Donor image mismatch/encrypted: ' + name)
            images[name] = (entry, data)
        validate_abi(images,plan)
        return images


def compile_framework(mode, output, proof, revision, zig, frontend="swiftui", apple_host=None):
    directory = output / mode
    framework = directory / (FRAMEWORK+'.framework')
    framework.mkdir(parents=True, exist_ok=True)
    plan = json.loads((ROOT/'native/twitch32.json').read_text())
    generate_header(plan, proof, revision, directory/'SSNBuild.h')
    if frontend=='swiftui':
        if not apple_host: raise ValueError('--apple-build-host is required for SwiftUI compilation')
        from apple_build import compile_apple
        compile_apple(ROOT,directory,mode,proof,revision,apple_host)
        shutil.copyfile(directory/FRAMEWORK,framework/FRAMEWORK)
        binary=(framework/FRAMEWORK).read_bytes()
        for dependency in loaded_dylibs(binary):
            if dependency in {'/usr/lib/libSystem.B.dylib','/usr/lib/libobjc.A.dylib'}: continue
            if dependency.startswith('/System/Library/Frameworks/'): continue
            if dependency.startswith(('/usr/lib/swift/libswift','@rpath/libswift')) and dependency.endswith('.dylib'): continue
            raise ValueError('Unexpected SwiftUI framework dependency: '+dependency)
    else:
        zig = Path(zig).resolve(); ziglib = zig.parent/'lib'
        args = [str(zig), 'build-lib', '-target','aarch64-ios-none','-O','ReleaseSmall',
                '-dynamic','-fPIC','-fno-stack-protector','-isystem',str(ziglib/'libc/include/any-macos-any'),
                '-I'+str(directory), '-I'+str(ROOT/'native'), '-L'+str(ROOT/'native/stubs'),
                '-lSystem','-lobjc','-lFoundation','-lUIKit','-install_name',LOAD,'-dead_strip','-headerpad','4000',
                '--entitlements',str(ROOT/'entitlements.plist'),'--name',FRAMEWORK,'-femit-bin='+str(framework/FRAMEWORK),
                '-cflags','-Wall','-Wextra','-Werror','-fblocks','-fvisibility=hidden',
                '-DSSN_NATIVE='+('1' if mode=='native' else '0'),'--']
        args += [str(ROOT/'native'/f) for f in ['SSNCore.c','SSNIntegration.c','SSNAccount.c','SSNFrontend.c']]
        env = dict(os.environ, ZIG_LOCAL_CACHE_DIR=str(output/'cache'), ZIG_GLOBAL_CACHE_DIR=str(output/'global-cache'))
        subprocess.run(args, check=True, env=env)
        for tool in ['align_macho_segments.py','shrink_adhoc_signature.py']:
            subprocess.run([sys.executable,str(ROOT/'tools'/tool),str(framework/FRAMEWORK)],check=True)
        binary=(framework/FRAMEWORK).read_bytes()
        expected_loads={'/usr/lib/libSystem.B.dylib','/usr/lib/libobjc.A.dylib',
                        '/System/Library/Frameworks/Foundation.framework/Foundation',
                        '/System/Library/Frameworks/UIKit.framework/UIKit'}
        if set(loaded_dylibs(binary))!=expected_loads:
            raise ValueError('Unexpected runtime dependency in the native framework')
    if dylib_id((framework/FRAMEWORK).read_bytes()) != LOAD:
        raise ValueError('Unexpected framework install name')
    (framework/'Info.plist').write_bytes(plistlib.dumps(dict(
        CFBundleExecutable=FRAMEWORK,CFBundleIdentifier='dev.streamside.nativeproof',
        CFBundleName=FRAMEWORK,CFBundlePackageType='FMWK',CFBundleVersion='3' if frontend=='swiftui' else '2',
        CFBundleShortVersionString='0.3' if frontend=='swiftui' else '0.2',MinimumOSVersion='16.4',
        SSNProofID=proof,SSNSourceRevision=revision,SSNMode=mode,SSNFrontend=frontend)))
    return framework


def package(ipa, images, framework, plan, proof, mode, output):
    mutations = {}
    for name in plan['layout']:
        entry, data = images[name]
        patched = patch(data, plan, name, proof, mode=='native')
        patched, added = inject_load_dylib(patched, LOAD)
        if not added or loaded_dylibs(patched).count(LOAD)!=1:
            raise ValueError('Probe framework injection failed')
        mutations[entry] = patched
    destination = output / f'StreamsideNativeProof-Twitch32-{mode}.ipa'
    with zipfile.ZipFile(ipa) as src, zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
        for original in src.infolist():
            path=original.filename
            if '/_CodeSignature/' in path or path.endswith('/embedded.mobileprovision'):
                continue
            data=mutations.get(path)
            if data is None: data=src.read(path)
            if path=='Payload/Twitch.app/Info.plist':
                info=plistlib.loads(data);info['CFBundleDisplayName']='Streamside Native' if mode=='native' else 'Twitch Baseline'
                info['SSNMode']=mode;info['SSNProofID']=proof
                if mode=='native' and plistlib.loads((framework/'Info.plist').read_bytes()).get('SSNFrontend')=='swiftui':
                    info.pop('UIDesignRequiresCompatibility',None)
                data=plistlib.dumps(info)
            dst.writestr(original,data)
        for path in sorted(framework.rglob('*')):
            if not path.is_file(): continue
            entry='Payload/Twitch.app/Frameworks/'+framework.name+'/'+str(path.relative_to(framework))
            info=zipfile.ZipInfo(entry,(2026,11,11,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if path.name==FRAMEWORK else 0o100644)<<16
            dst.writestr(info,path.read_bytes())
    with zipfile.ZipFile(destination) as z:
        if z.testzip(): raise ValueError('Output ZIP verification failed')
        # Verify every retained donor entry, including the original HBC and backend images.
        with zipfile.ZipFile(ipa) as original:
            for entry in original.namelist():
                if entry in mutations or entry.endswith('/Info.plist') and entry=='Payload/Twitch.app/Info.plist' or '/_CodeSignature/' in entry or entry.endswith('/embedded.mobileprovision'): continue
                if z.read(entry)!=original.read(entry): raise ValueError('Unexpected donor mutation: '+entry)
        for entry,data in mutations.items():
            if z.read(entry)!=data: raise ValueError('Packaged probe image mismatch')
    return dict(path=str(destination),bytes=destination.stat().st_size,sha256=sha(destination.read_bytes()),
                framework_sha256=sha((framework/FRAMEWORK).read_bytes()),
                modified_images={entry:sha(data) for entry,data in mutations.items()},
                signing='Requires device-authorized re-signing with the same application/keychain identity; no distribution profile is available here.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor',type=Path,required=True)
    parser.add_argument('--zig',default=os.environ.get('ZIG'))
    parser.add_argument('--frontend',choices=['swiftui','uikit'],default='swiftui')
    parser.add_argument('--apple-build-host',help='Existing SSH alias for the macOS Xcode builder')
    parser.add_argument('--output',type=Path,default=ROOT/'build/native-frontend')
    parser.add_argument('--mode',choices=['baseline','native','both'],default='both')
    args=parser.parse_args()
    if args.frontend=='uikit':
        if not args.zig: parser.error('--zig or ZIG is required (0.14.0) for the UIKit checkpoint')
        if subprocess.check_output([args.zig,'version'],text=True).strip()!='0.14.0': raise ValueError('Zig 0.14.0 required')
    elif not args.apple_build_host: parser.error('--apple-build-host is required for SwiftUI')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='feat/native-frontend': raise ValueError('Build only on feat/native-frontend')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,text=True).strip(): revision+='-dirty'
    proof=source_identity(args.frontend);plan=json.loads((ROOT/'native/twitch32.json').read_text())
    images=donor(args.donor,plan);args.output.mkdir(parents=True,exist_ok=True)
    manifest=dict(schema=1,proof_id=proof,source_revision=revision,donor_sha256=plan['donor_sha256'],
                  frontend=args.frontend,zig='0.14.0' if args.frontend=='uikit' else None,inspection=dict(abi_entries=len(plan['abi']),probe_entries=len(plan['probes']),
                  all_retained_donor_entries_verified=True,original_hbc_unchanged=True),
                  device_validation='not performed',artifacts={})
    for mode in (['baseline','native'] if args.mode=='both' else [args.mode]):
        framework=compile_framework(mode,args.output,proof,revision,args.zig,args.frontend,args.apple_build_host)
        manifest['artifacts'][mode]=package(args.donor,images,framework,plan,proof,mode,args.output)
        if args.frontend=='swiftui': manifest['artifacts'][mode]['apple_compilation']=json.loads((args.output/mode/'compiler.json').read_text())
    (args.output/'artifacts.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__': main()
