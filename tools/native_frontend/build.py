#!/usr/bin/env python3
"""Build a native development IPA; independent control packaging is explicit."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from workspace_paths import NATIVE_ARTIFACTS_DIR
from macho import inject_load_dylib, loaded_dylibs, encryption_ids
from probes import patch, generate_header
from validate import validate_abi
from identity import source_identity

FRAMEWORK = 'StreamsideNativeProof'
LOAD = f'@rpath/{FRAMEWORK}.framework/{FRAMEWORK}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


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


def compile_framework(mode, output, proof, revision, apple_host=None, components=None):
    from components import check_binary, framework_info, verify
    directory = output / mode
    framework = directory / (FRAMEWORK+'.framework')
    framework.mkdir(parents=True, exist_ok=True)
    plan = json.loads((ROOT/'native/twitch32.json').read_text())
    generate_header(plan, proof, revision, directory/'SSNBuild.h')
    if components:
        identity=verify(components)
        if (identity['proof_id'],identity['source_revision'])!=(proof,revision):
            raise ValueError('Component compilation and packaging identity mismatch')
        shutil.copytree(components/mode/(FRAMEWORK+'.framework'),framework,dirs_exist_ok=True)
        for name in ['SSNSwiftUI-Swift.h','apple-abi.o','compiler.json','build.log']:
            shutil.copy2(components/mode/name,directory/name)
    else:
        if not apple_host: raise ValueError('Use --components from a successful Native SwiftUI Actions run; --apple-build-host is optional fallback')
        from apple_build import compile_apple
        compile_apple(ROOT,directory,mode,proof,revision,apple_host)
        shutil.copyfile(directory/FRAMEWORK,framework/FRAMEWORK)
        for asset in (ROOT/'native/assets').glob('*.png'):
            shutil.copy2(asset,framework/asset.name)
    check_binary(framework/FRAMEWORK)
    (framework/'Info.plist').write_bytes(plistlib.dumps(framework_info(mode,proof,revision)))
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
    parser.add_argument('--frontend',choices=['swiftui'],default='swiftui')
    compilation=parser.add_mutually_exclusive_group()
    compilation.add_argument('--components',type=Path,help='Downloaded Native SwiftUI Actions component directory (normal build path)')
    compilation.add_argument('--apple-build-host',help='Optional fallback SSH alias; no host is assumed available')
    parser.add_argument('--output',type=Path,help='Output directory outside the repository; defaults under ../artifacts/native-frontend')
    parser.add_argument('--mode',choices=['baseline','native','both'],default='native')
    args=parser.parse_args()
    if not args.components and not args.apple_build_host:
        parser.error('SwiftUI requires --components from Actions, or an explicit --apple-build-host fallback')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='feat/native-frontend': raise ValueError('Build only on feat/native-frontend')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,text=True).strip(): revision+='-dirty'
    packaging_revision=revision
    proof=source_identity();plan=json.loads((ROOT/'native/twitch32.json').read_text())
    component_manifest=None
    if args.components:
        from components import verify
        args.components=args.components.resolve()
        component_manifest=verify(args.components)
        revision=component_manifest['source_revision']
    if args.output is None: args.output=NATIVE_ARTIFACTS_DIR/(revision[:12]+'-'+proof[:12])
    args.output=args.output.resolve()
    if args.output==ROOT or ROOT in args.output.parents: parser.error('--output must be outside the repository')
    if args.output.exists() and any(args.output.iterdir()): parser.error('Output must be empty; choose a new artifact directory')
    images=donor(args.donor,plan);args.output.mkdir(parents=True,exist_ok=True)
    manifest=dict(schema=1,proof_id=proof,source_revision=revision,packaging_revision=packaging_revision,donor_sha256=plan['donor_sha256'],
                  frontend='swiftui',zig=None,inspection=dict(abi_entries=len(plan['abi']),probe_entries=len(plan['probes']),
                  all_retained_donor_entries_verified=True,original_hbc_unchanged=True),
                  device_validation='not performed',artifacts={})
    if component_manifest: manifest['component_manifest_sha256']=sha((args.components/'components.json').read_bytes())
    for mode in (['baseline','native'] if args.mode=='both' else [args.mode]):
        framework=compile_framework(mode,args.output,proof,revision,args.apple_build_host,args.components)
        manifest['artifacts'][mode]=package(args.donor,images,framework,plan,proof,mode,args.output)
        manifest['artifacts'][mode]['apple_compilation']=json.loads((args.output/mode/'compiler.json').read_text())
    (args.output/'artifacts.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__': main()
