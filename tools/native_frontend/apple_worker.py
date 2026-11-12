"""Compile only transferred sources on macOS. No donor or Git database required."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root=Path(sys.argv[1]).resolve()
    config=json.loads((root/'config.json').read_text())
    for name,digest in config['inputs'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Transferred build input mismatch: '+name)
    output=root/'output';output.mkdir(exist_ok=True)
    def run(args):
        result=subprocess.run(args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with (output/'build.log').open('a') as log:log.write(str(args)+'\n'+result.stdout+'\n')
        if result.returncode:raise RuntimeError(result.stdout)
        return result.stdout.strip()
    sdk=run(['xcrun','--sdk','iphoneos','--show-sdk-path'])
    info={'xcode':run(['xcodebuild','-version']),'swift':run(['swift','--version']),
          'sdk_path':sdk,'sdk_version':run(['xcrun','--sdk','iphoneos','--show-sdk-version']),
          'macos':run(['sw_vers']),'target':'arm64-apple-ios16.4','mode':config['mode'],
          'proof_id':config['proof_id'],'source_revision':config['source_revision'],
          'transferred_inputs':config['inputs']}
    expected=config['toolchain']
    if info['xcode'] != 'Xcode '+expected['xcode_version']+'\nBuild version '+expected['xcode_build']:
        raise ValueError('Selected Xcode does not match native/apple-toolchain.json: '+info['xcode'])
    if info['sdk_version'] != expected['iphoneos_sdk']:
        raise ValueError('Selected iPhoneOS SDK does not match the pinned toolchain')
    info['runner_image']=dict(version=os.environ.get('ImageVersion'),name=os.environ.get('ImageOS'))
    info['github_run']=dict(id=os.environ.get('GITHUB_RUN_ID'),attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                            repository=os.environ.get('GITHUB_REPOSITORY'))
    (output/'compiler.json').write_text(json.dumps(info,indent=2)+'\n')
    common=['-target','arm64-apple-ios16.4','-isysroot',sdk,'-Os','-fblocks','-Wall','-Wextra','-Werror',
            '-fvisibility=hidden','-Inative','-Igenerated','-Ioutput','-DSSN_NATIVE='+str(int(config['mode']=='native'))]
    swift=['native/swift/'+p.name for p in sorted((root/'native/swift').glob('*.swift'))]
    run(['xcrun','swiftc','-target','arm64-apple-ios16.4','-sdk',sdk,'-O','-swift-version','5','-warnings-as-errors',
         '-module-name','StreamsideNativeProof','-import-objc-header','native/SSNNativeBridge.h',
         '-emit-objc-header-path','output/SSNSwiftUI-Swift.h','-emit-object','-whole-module-optimization',
         '-o','output/SwiftFrontend.o']+swift)
    objects=['output/SwiftFrontend.o']
    for name in ['SSNCore.c','SSNIntegration.c','SSNAccount.c','SSNNativeBridge.m']:
        obj='output/'+name+'.o'
        run(['xcrun','clang']+common+['-c','native/'+name,'-o',obj])
        objects.append(obj)
    # Compile the existing ABI caller fixture with the Apple compiler as well;
    # Ubuntu emulates its argument registers against the existing ABI tests.
    run(['xcrun','clang']+common+['-c','tests/native_frontend/abi_calls.c','-o','output/apple-abi.o'])
    binary='output/StreamsideNativeProof'
    run(['xcrun','swiftc','-target','arm64-apple-ios16.4','-sdk',sdk,'-emit-library','-o',binary]+objects+
        ['-framework','SwiftUI','-framework','UIKit','-framework','Foundation','-framework','Combine',
         '-Xlinker','-install_name','-Xlinker','@rpath/StreamsideNativeProof.framework/StreamsideNativeProof',
         '-Xlinker','-rpath','-Xlinker','/usr/lib/swift','-Xlinker','-dead_strip'])
    run(['codesign','--force','--sign','-','--timestamp=none',binary])
    run(['codesign','--verify','--strict',binary])
    run(['xcrun','swiftc','-O','native/swift/NativeModels.swift','tests/native_frontend/swift/ModelsTests.swift','-o','output/models-tests'])
    info['model_tests']=run([str(output/'models-tests')])
    info['codesign']='ad-hoc; IPA still requires device-authorized re-signing'
    (output/'compiler.json').write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__':main()
