"""Compile only transferred sources on macOS. No donor or Git database required."""
import hashlib
import json
import os
import platform
import plistlib
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
        result=subprocess.run(args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
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
            '-fvisibility=hidden','-DSSN_SWIFTUI=1','-Inative','-Igenerated','-Ioutput','-DSSN_NATIVE='+str(int(config['mode']=='native'))]
    swift=['native/swift/'+p.name for p in sorted((root/'native/swift').glob('*.swift'))]
    run(['xcrun','swiftc','-target','arm64-apple-ios16.4','-sdk',sdk,'-O','-swift-version','5','-warnings-as-errors',
         '-module-name','StreamsideNativeProof','-import-objc-header','native/SSNNativeBridge.h',
         '-emit-objc-header-path','output/SSNSwiftUI-Swift.h','-emit-object','-whole-module-optimization',
         '-o','output/SwiftFrontend.o']+swift)
    objects=['output/SwiftFrontend.o']
    for name in ['SSNCore.c','SSNIntegration.c','SSNAccount.c','SSNFeed.c','SSNPlaybackRequest.c','SSNPlayback.m','SSNNativeBridge.m','SSNWindowOwnership.m']:
        obj='output/'+name+'.o'
        run(['xcrun','clang']+common+(['-fobjc-arc'] if name=='SSNWindowOwnership.m' else [])+['-c','native/'+name,'-o',obj])
        objects.append(obj)
    # Compile the existing ABI caller fixture with the Apple compiler as well;
    # Ubuntu emulates its argument registers against the existing ABI tests.
    run(['xcrun','clang']+common+['-c','tests/native_frontend/abi_calls.c','-o','output/apple-abi.o'])
    binary='output/StreamsideNativeProof'
    run(['xcrun','swiftc','-target','arm64-apple-ios16.4','-sdk',sdk,'-emit-library','-o',binary]+objects+
        ['-framework','SwiftUI','-framework','UIKit','-framework','Foundation','-framework','Combine','-framework','ImageIO','-framework','CoreHaptics','-framework','AVFAudio',
         '-Xlinker','-install_name','-Xlinker','@rpath/StreamsideNativeProof.framework/StreamsideNativeProof',
         '-Xlinker','-rpath','-Xlinker','/usr/lib/swift','-Xlinker','-dead_strip'])
    run(['codesign','--force','--sign','-','--timestamp=none',binary])
    run(['codesign','--verify','--strict',binary])
    run(['xcrun','swiftc','-O','native/swift/NativeModels.swift','tests/native_frontend/swift/ModelsTests.swift','-o','output/models-tests'])
    info['model_tests']=run([str(output/'models-tests')])
    info['uikit_ownership_tests']=test_window_ownership(root, output, config, run)
    info['codesign']='ad-hoc; IPA still requires device-authorized re-signing'
    (output/'compiler.json').write_text(json.dumps(info,indent=2)+'\n')


def test_window_ownership(root, output, config, run):
    """Run the production window hook with real UIKit; no donor or account."""
    simulator_sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path'])
    architecture='arm64' if platform.machine()=='arm64' else 'x86_64'
    stage=root/'ownership-simulator';stage.mkdir()
    # Isolate the production setter from the donor integration. This is the
    # exact owned Objective-C class selector used by the compiled Swift host.
    (stage/'SSNSwiftUI-Swift.h').write_text(
        '#import <UIKit/UIKit.h>\n@interface SSNSwiftUIHost : NSObject\n'
        '+ (void)retainAuthenticationRoot:(UIViewController *)root;\n@end\n')
    bundle=stage/'OwnershipTest.app';bundle.mkdir()
    bundle_id='dev.streamside.ownershiptest'
    (bundle/'Info.plist').write_bytes(plistlib.dumps(dict(
        CFBundleIdentifier=bundle_id,CFBundleExecutable='OwnershipTest',
        CFBundleName='OwnershipTest',CFBundlePackageType='APPL',CFBundleVersion='1',
        CFBundleShortVersionString='1.0',MinimumOSVersion='16.4',
        LSRequiresIPhoneOS=True,UIDeviceFamily=[1,2],UILaunchScreen={})))
    run(['xcrun','clang','-target',architecture+'-apple-ios16.4-simulator','-isysroot',simulator_sdk,
         '-fobjc-arc','-fblocks','-Wall','-Wextra','-Werror','-DSSN_NATIVE='+str(int(config['mode']=='native')),
         '-Inative','-Igenerated','-I'+str(stage),
         'native/SSNWindowOwnership.m','tests/native_frontend/ownership_test.m',
         '-framework','UIKit','-framework','Foundation','-o',str(bundle/'OwnershipTest')])
    run(['codesign','--force','--sign','-','--timestamp=none',str(bundle)])
    clock_bundle=stage/'ClockTest.app';clock_bundle.mkdir()
    clock_id='dev.streamside.clocktest'
    clock_plist=plistlib.loads((bundle/'Info.plist').read_bytes())
    clock_plist.update(CFBundleIdentifier=clock_id,CFBundleExecutable='ClockTest',CFBundleName='ClockTest')
    (clock_bundle/'Info.plist').write_bytes(plistlib.dumps(clock_plist))
    run(['xcrun','swiftc','-target',architecture+'-apple-ios16.4-simulator','-sdk',simulator_sdk,
         '-swift-version','5','-warnings-as-errors','-parse-as-library',
         'native/swift/StreamClock.swift','native/swift/MeasuredStreamTitle.swift','native/swift/TitleHaptics.swift',
         'tests/native_frontend/swift/ClockTests.swift','-framework','CoreHaptics','-framework','AVFAudio',
         '-o',str(clock_bundle/'ClockTest')])
    run(['codesign','--force','--sign','-','--timestamp=none',str(clock_bundle)])
    playback_bundle=stage/'PlaybackTest.app';playback_bundle.mkdir()
    playback_id='dev.streamside.playbacktest'
    (playback_bundle/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleExecutable='PlaybackTest',CFBundleIdentifier=playback_id,
        CFBundleName='PlaybackTest',CFBundleVersion='1',CFBundlePackageType='APPL',LSRequiresIPhoneOS=True,UILaunchScreen={})))
    run(['xcrun','clang','-target',architecture+'-apple-ios16.4-simulator','-isysroot',simulator_sdk,
         '-fblocks','-Wall','-Wextra','-Werror','-DSSN_NATIVE=1','-Inative','-Igenerated',
         'native/SSNPlayback.m','tests/native_frontend/playback_test.m','-framework','UIKit','-framework','Foundation',
         '-framework','AVFAudio','-o',str(playback_bundle/'PlaybackTest')])
    run(['codesign','--force','--sign','-','--timestamp=none',str(playback_bundle)])
    runtimes=json.loads(run(['xcrun','simctl','list','runtimes','--json']))['runtimes']
    runtime=next(r['identifier'] for r in runtimes if r.get('isAvailable') and r['identifier'].startswith('com.apple.CoreSimulator.SimRuntime.iOS-'))
    types=json.loads(run(['xcrun','simctl','list','devicetypes','--json']))['devicetypes']
    device_type=next(t['identifier'] for t in types if t['name'].startswith('iPhone 17 Pro'))
    device=run(['xcrun','simctl','create','Streamside ownership test',device_type,runtime])
    try:
        run(['xcrun','simctl','boot',device])
        run(['xcrun','simctl','bootstatus',device,'-b'])
        run(['xcrun','simctl','install',device,str(bundle)])
        run(['xcrun','simctl','launch','--console',device,bundle_id])
        container=Path(run(['xcrun','simctl','get_app_container',device,bundle_id,'data']))
        receipt=json.loads((container/'Documents/ownership-test.json').read_text())
        if receipt != dict(passed=True,native=config['mode']=='native',blocked=2 if config['mode']=='native' else 0,failures=0):
            raise ValueError('UIKit ownership test failed: '+str(receipt))
        run(['xcrun','simctl','install',device,str(clock_bundle)])
        run(['xcrun','simctl','launch','--console',device,clock_id])
        clock_container=Path(run(['xcrun','simctl','get_app_container',device,clock_id,'data']))
        observed=json.loads((clock_container/'Documents/clock-test.json').read_text())
        if observed != dict(passed=True,ticking=True,paused=True,resumed=True,title_measurement=True,haptic_pattern=True):
            raise ValueError('UIKit clock/title interaction test failed: '+str(observed))
        clock_receipt={k:observed[k] for k in ['passed','ticking','paused','resumed']}
        interactions={k:observed[k] for k in ['title_measurement','haptic_pattern']}
        run(['xcrun','simctl','install',device,str(playback_bundle)])
        run(['xcrun','simctl','launch','--console',device,playback_id])
        playback_container=Path(run(['xcrun','simctl','get_app_container',device,playback_id,'data']))
        playback=json.loads((playback_container/'Documents/playback-test.json').read_text())
        expected_playback={k:True for k in ['passed','background_resume','account_stop','cancellation','teardown','source_encoding','playing_observed']}
        if playback!=expected_playback:raise ValueError('Synthetic UIKit playback lifecycle failed: '+str(playback))
        return dict(playback_receipt=playback,title_interaction_receipt=interactions,clock_receipt=clock_receipt,result='PASS',environment='iOS Simulator; real UIKit, synthetic owned controllers, no donor',receipt=receipt)
    finally:
        run(['xcrun','simctl','shutdown',device])
        run(['xcrun','simctl','delete',device])


if __name__=='__main__':main()
