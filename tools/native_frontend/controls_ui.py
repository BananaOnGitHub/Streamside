"""Donor-free coordinate tests for the production SwiftUI player controls."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import zipfile

SOURCES = ['native/swift/AnchoredPreviewController.swift', 'native/swift/ContextPreviewSession.swift', 'native/swift/QuickLookController.swift', 'tests/native_frontend/swift/ContextPreviewFixture.swift', 'native/swift/QuickLookPanel.swift', 'native/swift/StreamTags.swift', 'native/swift/ThumbnailActions.swift', 'native/swift/PlayerControls.swift', 'native/swift/PlayerCanvas.swift', 'native/swift/PlayerControlMotion.swift',
           'native/swift/NativeModels.swift', 'native/swift/StreamClock.swift',
           'tests/native_frontend/swift/PlayerInputApp.swift',
           'tests/native_frontend/swift/PlayerInputTests.swift']
EXPECTED = dict(passed=True, tests=4, styles=['glass', 'plain'], motion_frames=True,motion_sampling_scale=3,motion_pixels=True,motion_synchronized=True,motion_all_regions=True,motion_shared_travel=True,thumbnail_coordinates=True,preview_panel=True,source_anchored_preview=True,source_animation=True,hold_feedback=True,real_video_clipping=True)


def project(root, stage):
    """Generate an SDK-only fixture project outside the source checkout."""
    stage.mkdir()
    folder=stage/'PlayerInput.xcodeproj';folder.mkdir()
    objects={};counter=0
    def obj(isa, **values):
        nonlocal counter
        counter+=1;key=f'{counter:024X}';objects[key]=dict(isa=isa,**values);return key
    app_product=obj('PBXFileReference',explicitFileType='wrapper.application',path='InputTest.app',sourceTree='BUILT_PRODUCTS_DIR')
    ui_product=obj('PBXFileReference',explicitFileType='wrapper.cfbundle',path='PlayerInputTests.xctest',sourceTree='BUILT_PRODUCTS_DIR')
    app_files=[];ui_files=[];refs=[]
    for name in SOURCES:
        ref=obj('PBXFileReference',lastKnownFileType='sourcecode.swift',path=os.path.relpath(root/name,stage),sourceTree='<group>');refs.append(ref)
        build=obj('PBXBuildFile',fileRef=ref)
        (ui_files if name.endswith('PlayerInputTests.swift') else app_files).append(build)
    products=obj('PBXGroup',children=[app_product,ui_product],name='Products',sourceTree='<group>')
    group=obj('PBXGroup',children=refs+[products],sourceTree='<group>')
    common=dict(SDKROOT='iphonesimulator',IPHONEOS_DEPLOYMENT_TARGET='16.4',SWIFT_VERSION='5.0',
                SWIFT_TREAT_WARNINGS_AS_ERRORS='YES',CODE_SIGNING_ALLOWED='NO',TARGETED_DEVICE_FAMILY='1',GENERATE_INFOPLIST_FILE='YES')
    def configs(extra):
        return obj('XCConfigurationList',buildConfigurations=[obj('XCBuildConfiguration',name='Debug',buildSettings={**common,**extra})],defaultConfigurationIsVisible=0,defaultConfigurationName='Debug')
    project_configs=configs({})
    app_configs=configs(dict(PRODUCT_BUNDLE_IDENTIFIER='dev.streamside.playerinput',PRODUCT_NAME='InputTest',
        INFOPLIST_KEY_UILaunchScreen_Generation='YES'))
    ui_configs=configs(dict(PRODUCT_BUNDLE_IDENTIFIER='dev.streamside.playerinput.tests',PRODUCT_NAME='PlayerInputTests',TEST_TARGET_NAME='InputTest'))
    def phases(files):
        return [obj('PBXSourcesBuildPhase',buildActionMask=2147483647,files=files,runOnlyForDeploymentPostprocessing=0),
                obj('PBXFrameworksBuildPhase',buildActionMask=2147483647,files=[],runOnlyForDeploymentPostprocessing=0)]
    app=obj('PBXNativeTarget',name='InputTest',productName='InputTest',productReference=app_product,
        productType='com.apple.product-type.application',buildConfigurationList=app_configs,buildPhases=phases(app_files),buildRules=[],dependencies=[])
    # Container proxy points back to the eventual PBXProject object.
    proxy=obj('PBXContainerItemProxy',containerPortal='',proxyType=1,remoteGlobalIDString=app,remoteInfo='InputTest')
    dependency=obj('PBXTargetDependency',target=app,targetProxy=proxy)
    ui=obj('PBXNativeTarget',name='PlayerInputTests',productName='PlayerInputTests',productReference=ui_product,
        productType='com.apple.product-type.bundle.ui-testing',buildConfigurationList=ui_configs,buildPhases=phases(ui_files),buildRules=[],dependencies=[dependency])
    root_id=obj('PBXProject',attributes=dict(LastUpgradeCheck='2660',TargetAttributes={ui:dict(TestTargetID=app)}),
        buildConfigurationList=project_configs,compatibilityVersion='Xcode 14.0',developmentRegion='en',knownRegions=['en','Base'],
        mainGroup=group,productRefGroup=products,projectDirPath='',projectRoot='',targets=[app,ui])
    objects[proxy]['containerPortal']=root_id
    (folder/'project.pbxproj').write_bytes(plistlib.dumps(dict(archiveVersion='1',classes={},objectVersion='56',objects=objects,rootObject=root_id)))
    schemes=folder/'xcshareddata/xcschemes';schemes.mkdir(parents=True)
    def ref(target,name):
        return f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{target}" BuildableName="{name}" BlueprintName="{name.split(".")[0]}" ReferencedContainer="container:PlayerInput.xcodeproj"/>'
    app_ref=ref(app,'InputTest.app');ui_ref=ref(ui,'PlayerInputTests.xctest')
    (schemes/'PlayerInput.xcscheme').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="2660" version="1.3">
<BuildAction parallelizeBuildables="NO" buildImplicitDependencies="YES"><BuildActionEntries>
<BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="NO" buildForArchiving="NO" buildForAnalyzing="YES">{app_ref}</BuildActionEntry>
<BuildActionEntry buildForTesting="YES" buildForRunning="NO" buildForProfiling="NO" buildForArchiving="NO" buildForAnalyzing="YES">{ui_ref}</BuildActionEntry>
</BuildActionEntries></BuildAction>
<TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES" language="en" region="US">
<MacroExpansion>{app_ref}</MacroExpansion><Testables><TestableReference skipped="NO" parallelizable="NO">{ui_ref}</TestableReference></Testables>
</TestAction></Scheme>''')
    return folder


def preserve_failure_images(exported, archive):
    """Publish only bounded owned-fixture PNGs, never the entire result bundle."""
    files = {}; total = 0
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(exported.rglob('*.png')):
            if path.is_symlink() or not path.is_file():
                continue
            size = path.stat().st_size
            if len(files) >= 8 or size > 2 * 1024 * 1024 or total + size > 16 * 1024 * 1024:
                continue
            data = path.read_bytes()
            if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                continue
            name = str(path.relative_to(exported))
            bundle.writestr(name, data); total += len(data)
            files[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        bundle.writestr('manifest.json', json.dumps(dict(scope='donor-free simulator fixture failures only', files=files), indent=2))


def run_controls_ui(root, stage, device, run):
    folder=project(root,stage/'player-input-ui')
    base=['xcodebuild','-project',str(folder),'-scheme','PlayerInput','-configuration','Debug',
          '-destination','id='+device,'-derivedDataPath',str(folder.parent/'DerivedData'),
          '-parallel-testing-enabled','NO','CODE_SIGNING_ALLOWED=NO']
    run(base+['build-for-testing'], label='Build player controls coordinate-test app')
    result_bundle=folder.parent/'PlayerInput.xcresult'
    try:
        observed=run(base+['test-without-building', '-resultBundlePath', str(result_bundle)], timeout=900,
                     label='Test player controls, source-anchored preview, decoded video, gestures and lifecycle')
    except Exception:
        # Result bundles and recordings stay temporary. Preserve up to eight
        # owned-fixture stills alongside the existing failure logs before cleanup.
        exported=folder.parent/'failure-attachments'
        try:
            run(['xcrun','xcresulttool','export','attachments','--path',str(result_bundle),'--output-path',str(exported)],
                timeout=45, label='Export owned simulator failure screenshots')
            preserve_failure_images(exported, root/'output/player-input-failure.zip')
        except Exception as evidence_error:
            print('Failure screenshot export unavailable: '+str(evidence_error), flush=True)
        raise
    for name in ['testGlassControls','testPlainControls','testThumbnailHoldAndTap','testPreviewPanelLayoutAndActions']:
        if not re.search(r"Test Case .*"+name+r".* passed",observed):
            raise ValueError('Player coordinate test did not pass: '+name)
    if not re.search(r'Executed 4 tests?, with 0 failures',observed):
        raise ValueError('Four actual player/thumbnail/preview coordinate tests were not observed')
    if observed.count('PLAYER_MOTION_CHECKS PASS:') != 2:
        raise ValueError('Both rendered-motion fixture checks must pass')
    if observed.count('PLAYER_OPACITY_PIXELS PASS:') != 2:
        raise ValueError('Both rendered opacity pixel checks must pass')
    if 'THUMBNAIL_COORDINATES PASS:' not in observed:
        raise ValueError('Actual thumbnail hold/tap/scroll checks must pass')
    if 'THUMBNAIL_LIFT PASS:' not in observed:
        raise ValueError('Rendered thumbnail enlargement before preview admission must pass')
    if 'PREVIEW_PANEL PASS:' not in observed:
        raise ValueError('Actual interactive preview sizing/menu/scroll checks must pass')
    if 'CONTEXT_VIDEO PASS:' not in observed:
        raise ValueError('Actual changing decoded video and clipping checks must pass')
    return dict(EXPECTED)
