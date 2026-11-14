#!/usr/bin/env python3
"""Build and verify donor-free SwiftUI components; never assemble an IPA here."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from workspace_paths import ARTIFACTS_DIR
from macho import dylib_id, header, loaded_dylibs, MH_DYLIB
from apple_inputs import build_inputs
from build_progress import run_logged
from identity import source_identity
from probes import generate_header

FRAMEWORK = "StreamsideNativeProof"
LOAD = f"@rpath/{FRAMEWORK}.framework/{FRAMEWORK}"
MODES = ("baseline", "native")
FILES = {"SSNBuild.h", "SSNSwiftUI-Swift.h", "apple-abi.o", "compiler.json", "build.log",
         f"{FRAMEWORK}.framework/{FRAMEWORK}", f"{FRAMEWORK}.framework/Info.plist"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def external(path):
    path = path.resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError("Output must be outside the repository")
    return path


def framework_info(mode, proof, revision):
    return dict(CFBundleExecutable=FRAMEWORK, CFBundleIdentifier="dev.streamside.nativeproof",
                CFBundleName=FRAMEWORK, CFBundlePackageType="FMWK", CFBundleVersion="3",
                CFBundleShortVersionString="0.3", MinimumOSVersion="16.4", SSNProofID=proof,
                SSNSourceRevision=revision, SSNMode=mode, SSNFrontend="swiftui")


def check_binary(binary):
    data = binary.read_bytes()
    if header(data).file_type != MH_DYLIB or dylib_id(data) != LOAD:
        raise ValueError("Invalid arm64 framework or install name")
    for dependency in loaded_dylibs(data):
        if dependency in {"/usr/lib/libSystem.B.dylib", "/usr/lib/libobjc.A.dylib"}:
            continue
        if dependency.startswith("/System/Library/Frameworks/"):
            continue
        if dependency.startswith(("/usr/lib/swift/libswift", "@rpath/libswift")) and dependency.endswith(".dylib"):
            continue
        raise ValueError("Unexpected framework dependency: " + dependency)


def verify(directory, revision=None):
    """Check current source compatibility, all outputs, and successful validation."""
    directory = directory.resolve()
    manifest = json.loads((directory / "components.json").read_text())
    if manifest.get("schema") != 1 or manifest.get("validated") is not True:
        raise ValueError("Missing successful component validation")
    expected_revision = revision or manifest.get("source_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_revision):
        raise ValueError("Invalid component source revision")
    if revision is None:
        ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", expected_revision, "HEAD"],
                                  cwd=ROOT, capture_output=True)
        if ancestor.returncode:
            raise ValueError("Component source revision is not in the checked-out history")
    if manifest.get("source_revision") != expected_revision or manifest.get("proof_id") != source_identity():
        raise ValueError("Components do not match the checked-out source revision/proof")
    if manifest.get("plan_sha256") != sha((ROOT / "native/twitch32.json").read_bytes()):
        raise ValueError("Component donor-admission plan mismatch")
    required = {mode + "/" + name for mode in MODES for name in FILES}
    if set(manifest.get("files", {})) != required:
        raise ValueError("Unexpected or incomplete component file manifest")
    actual = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if actual != required | {"components.json"} or any(p.is_symlink() for p in directory.rglob("*")):
        raise ValueError("Unexpected component files or symlinks")
    for name, identity in manifest["files"].items():
        data = (directory / name).read_bytes()
        if identity != dict(bytes=len(data), sha256=sha(data)):
            raise ValueError("Component hash mismatch: " + name)
    for mode in MODES:
        local = directory / mode
        with tempfile.TemporaryDirectory() as temporary:
            expected_header = Path(temporary) / "SSNBuild.h"
            generate_header(json.loads((ROOT / "native/twitch32.json").read_text()),
                            manifest["proof_id"], expected_revision, expected_header)
            if expected_header.read_bytes() != (local / "SSNBuild.h").read_bytes():
                raise ValueError("Generated admission header mismatch")
            inputs = json.loads(build_inputs(ROOT, expected_header, mode, manifest["proof_id"], expected_revision)["config.json"])
        compiler = json.loads((local / "compiler.json").read_text())
        pin = inputs["toolchain"]
        if (compiler.get("source_revision"), compiler.get("proof_id"), compiler.get("mode"), compiler.get("transferred_inputs")) != (
                expected_revision, manifest["proof_id"], mode, inputs["inputs"]):
            raise ValueError("Compiler input identity mismatch")
        if compiler.get("xcode") != "Xcode " + pin["xcode_version"] + "\nBuild version " + pin["xcode_build"] or compiler.get("sdk_version") != pin["iphoneos_sdk"]:
            raise ValueError("Component toolchain mismatch")
        if not compiler.get("model_tests", "").startswith("PASS:") or compiler.get("codesign") != "ad-hoc; IPA still requires device-authorized re-signing":
            raise ValueError("Apple model/signature validation missing")
        uikit = compiler.get("uikit_ownership_tests", {})
        if uikit.get("result") != "PASS" or uikit.get("receipt") != dict(passed=True, native=mode=="native", blocked=2 if mode=="native" else 0, failures=0):
            raise ValueError("UIKit ownership simulator validation missing or failed")
        if uikit.get("clock_receipt") != dict(passed=True, ticking=True, paused=True, resumed=True):
            raise ValueError("UIKit lifecycle clock validation missing or failed")
        if uikit.get("title_interaction_receipt") != dict(title_measurement=True, haptic_pattern=True):
            raise ValueError("UIKit title measurement/haptic pattern validation missing or failed")
        if uikit.get("launch_receipt") != [dict(stage=i,passed=True,native=i!=1,pending=i==0,origin=2 if i==1 else 1) for i in range(3)]:
            raise ValueError("Three-process launch selection validation missing or failed")
        expected_ui=dict(passed=True,tests=2,styles=['glass','plain'],motion_frames=True,motion_sampling_scale=3) if mode=='native' else None
        if uikit.get("controls_ui_receipt") != expected_ui:
            raise ValueError("Player coordinate interaction validation missing or failed")
        if uikit.get("playback_receipt") != {k:True for k in ['passed','background_resume','account_stop','cancellation','teardown','source_encoding','playing_observed','local_pause_resume','stream_only_mute','control_intent_retained']}:
            raise ValueError("Synthetic UIKit playback lifecycle validation missing or failed")
        framework = local / (FRAMEWORK + ".framework")
        if plistlib.loads((framework / "Info.plist").read_bytes()) != framework_info(mode, manifest["proof_id"], expected_revision):
            raise ValueError("Framework metadata mismatch")
        check_binary(framework / FRAMEWORK)
    return manifest


def build(output):
    output = external(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Build output must be empty; preserve prior component identities")
    output.mkdir(parents=True, exist_ok=True)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("Component distribution requires a clean source checkout")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    proof = source_identity()
    manifest = dict(schema=1, source_revision=revision, proof_id=proof,
                    plan_sha256=sha((ROOT / "native/twitch32.json").read_bytes()), validated=False,
                    validation_scope="Apple compile/link/ad-hoc signature, host models and synthetic UIKit lifecycle tests; no donor execution or device playback",
                    files={})
    # Validate native input first; preserve the independent control component too.
    for mode in ("native", "baseline"):
        local = output / mode
        local.mkdir()
        generate_header(json.loads((ROOT / "native/twitch32.json").read_text()), proof, revision, local / "SSNBuild.h")
        with tempfile.TemporaryDirectory(prefix="streamside-apple-", dir=output.parent) as temporary:
            stage = Path(temporary)
            for name, data in build_inputs(ROOT, local / "SSNBuild.h", mode, proof, revision).items():
                destination = stage / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            run_logged([sys.executable, "-u", str(stage / "tools/native_frontend/apple_worker.py"), str(stage)],
                       cwd=ROOT, log_path=local / "build.log", timeout=1500,
                       label="Build and validate " + mode + " component", group=False, heartbeat=False, summary=True)
            framework = local / (FRAMEWORK + ".framework")
            framework.mkdir()
            for name in FILES - {"SSNBuild.h", "build.log", f"{FRAMEWORK}.framework/Info.plist", f"{FRAMEWORK}.framework/{FRAMEWORK}"}:
                shutil.copy2(stage / "output" / name, local / name)
            shutil.copy2(stage / "output" / FRAMEWORK, framework / FRAMEWORK)
            (framework / "Info.plist").write_bytes(plistlib.dumps(framework_info(mode, proof, revision)))
        print("Verify " + mode + " framework dependencies and artifact hashes", flush=True)
        check_binary(framework / FRAMEWORK)
        for name in sorted(FILES):
            data = (local / name).read_bytes()
            manifest["files"][mode + "/" + name] = dict(bytes=len(data), sha256=sha(data))
    manifest["validated"] = True
    (output / "components.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Final validation: source, toolchain, required test receipts and every component hash", flush=True)
    verify(output, revision)
    print("Validated donor-free SwiftUI components: " + str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--output", type=Path, default=ARTIFACTS_DIR / "swiftui-components")
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args.output)
        else:
            verify(args.output)
            print("Component source, toolchain, validation and hashes match")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        if args.command == "build":
            output = external(args.output)
            output.mkdir(parents=True, exist_ok=True)
            if not (output / "components.json").exists():
                (output / "failure.json").write_text(json.dumps(dict(validated=False, error=str(error)), indent=2) + "\n")
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
