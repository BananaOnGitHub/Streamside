"""Synthetic component admission tests. Never donor or iOS runtime validation."""
import json
from pathlib import Path
import plistlib
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/native_frontend")]
from components import FRAMEWORK, FILES, MODES, LOAD, framework_info, sha, verify
from identity import source_identity
from apple_inputs import build_inputs
from probes import generate_header


class ComponentAdmission(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.revision = "a" * 40
        proof = source_identity()
        command = struct.pack("<6I", 0xD, (24 + len(LOAD) + 8) & ~7, 24, 0, 0, 0)
        command += LOAD.encode() + b"\0"
        command += bytes((-len(command)) % 8)
        binary = struct.pack("<8I", 0xfeedfacf, 0x100000c, 0, 6, 1, len(command), 0, 0) + command
        self.manifest = dict(schema=1, validated=True, source_revision=self.revision, proof_id=proof,
                             plan_sha256=sha((ROOT / "native/twitch32.json").read_bytes()), files={})
        for mode in MODES:
            directory = self.directory / mode
            directory.mkdir()
            for name in FILES:
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / "native/assets" / path.name).read_bytes() if path.suffix == ".png" else b"synthetic-owned-fixture")
            generate_header(json.loads((ROOT / "native/twitch32.json").read_text()), proof, self.revision, directory / "SSNBuild.h")
            config = json.loads(build_inputs(ROOT, directory / "SSNBuild.h", mode, proof, self.revision)["config.json"])
            pin = config["toolchain"]
            compiler = dict(source_revision=self.revision, proof_id=proof, mode=mode, transferred_inputs=config["inputs"],
                            xcode="Xcode " + pin["xcode_version"] + "\nBuild version " + pin["xcode_build"], sdk_version=pin["iphoneos_sdk"],
                            model_tests="PASS: synthetic fixture",
                            uikit_ownership_tests=dict(quicklook_receipt=dict(passed=True,failures=[],source_target=True,hold_cancellation=True,unblocked_return=True,dismiss_before_handoff=True,single_handoff=True,teardown=True,all_tags_wrap=True,lifecycle_cancellation=True,consent_before_preview=True),controls_ui_receipt=dict(passed=True,tests=5,styles=['glass','plain'],motion_frames=True,motion_sampling_scale=3,motion_pixels=True,motion_synchronized=True,motion_all_regions=True,motion_shared_travel=True,thumbnail_coordinates=True,preview_panel=True,source_anchored_preview=True,source_animation=True,hold_feedback=True,swipe_dismissal=True,verification_settings=True,real_video_clipping=True,marked_content=True) if mode=='native' else None,launch_receipt=[dict(stage=i,passed=True,native=i!=1,pending=i==0,origin=2 if i==1 else 1) for i in range(3)],playback_receipt={k:True for k in ['passed','background_resume','account_stop','cancellation','teardown','source_encoding','playing_observed','local_pause_resume','stream_only_mute','control_intent_retained','preview_muted_before_load','preview_mixes_audio','theatre_audio_promotion','preview_cold_audio','async_retirement','audio_preparation_cancellation','audio_retirement_ordering','vaft_lifetime']},title_interaction_receipt=dict(title_measurement=True,haptic_pattern=True),clock_receipt=dict(passed=True,ticking=True,paused=True,resumed=True),result="PASS",receipt=dict(passed=True,native=mode=="native",blocked=2 if mode=="native" else 0,failures=0)), codesign="ad-hoc; IPA still requires device-authorized re-signing")
            compiler["marked_content_tests"]=dict(passed=True,consent=True,preferences=True,cancellation=True,native_request=True)
            compiler["adblock_tests"]={k:True for k in ["passed","default_enabled","disabled_passthrough","baseline_untouched","native_tokens","clean_alternate","fallback_segments","stream_isolation","cancellation","account_change","preference_restoration"]}
            (directory / "compiler.json").write_text(json.dumps(compiler))
            (directory / (FRAMEWORK + ".framework") / "Info.plist").write_bytes(plistlib.dumps(framework_info(mode, proof, self.revision)))
            (directory / (FRAMEWORK + ".framework") / FRAMEWORK).write_bytes(binary)
        self.record()

    def record(self):
        for mode in MODES:
            for name in FILES:
                data = (self.directory / mode / name).read_bytes()
                self.manifest["files"][mode + "/" + name] = dict(bytes=len(data), sha256=sha(data))
        (self.directory / "components.json").write_text(json.dumps(self.manifest))

    def test_complete_source_matched_components(self):
        verify(self.directory, self.revision)

    def test_missing_launch_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests'].pop('launch_receipt')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'Three-process launch'):verify(self.directory,self.revision)

    def test_missing_player_coordinate_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests'].pop('controls_ui_receipt')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'coordinate interaction'):verify(self.directory,self.revision)

    def test_missing_motion_frame_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests']['controls_ui_receipt'].pop('motion_frames')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'coordinate interaction'):verify(self.directory,self.revision)

    def test_missing_synchronized_motion_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text())
        for key in ['motion_synchronized','motion_all_regions','motion_shared_travel','preview_panel','source_anchored_preview','source_animation','hold_feedback','swipe_dismissal','verification_settings','real_video_clipping']:
            with self.subTest(key=key):
                changed=json.loads(json.dumps(compiler));changed['uikit_ownership_tests']['controls_ui_receipt'].pop(key)
                path.write_text(json.dumps(changed));self.record()
                with self.assertRaisesRegex(ValueError,'coordinate interaction'):verify(self.directory,self.revision)

    def test_missing_marked_content_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler.pop('marked_content_tests')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'Marked-content'):verify(self.directory,self.revision)

    def test_missing_vaft_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text())
        for key in list(compiler['adblock_tests']):
            changed=json.loads(json.dumps(compiler));changed['adblock_tests'].pop(key)
            path.write_text(json.dumps(changed));self.record()
            with self.assertRaisesRegex(ValueError,'VAFT transport'):verify(self.directory,self.revision)

    def test_missing_playback_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests'].pop('playback_receipt')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'playback lifecycle'):verify(self.directory,self.revision)

    def test_missing_preview_audio_policy_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        original=json.loads(path.read_text())
        for key in ['preview_mixes_audio','theatre_audio_promotion','preview_cold_audio','async_retirement','audio_preparation_cancellation','audio_retirement_ordering','vaft_lifetime']:
            with self.subTest(key=key):
                changed=json.loads(json.dumps(original));changed['uikit_ownership_tests']['playback_receipt'].pop(key)
                path.write_text(json.dumps(changed));self.record()
                with self.assertRaisesRegex(ValueError,'playback lifecycle'):verify(self.directory,self.revision)

    def test_missing_hold_cancellation_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests']['quicklook_receipt'].pop('hold_cancellation')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'Quick Look'):verify(self.directory,self.revision)

    def test_missing_unblocked_return_validation_is_rejected(self):
        path=self.directory/'native/compiler.json'
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests']['quicklook_receipt'].pop('unblocked_return')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError,'Quick Look'):verify(self.directory,self.revision)

    def test_badge_assets_match_provenance_and_dimensions(self):
        manifest=json.loads((ROOT/'native/assets/verification.json').read_text())
        self.assertEqual(set(manifest),{'twitch-verified.png','verifiedbtw.png'})
        for name,record in manifest.items():
            data=(ROOT/'native/assets'/name).read_bytes()
            self.assertEqual(sha(data),record['sha256'])
            self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II',data[16:24]),(record['pixels'],record['pixels']))
            self.assertLess(len(data),32768)

    def test_changed_badge_resource_is_rejected_even_with_updated_manifest(self):
        path=self.directory/'native'/ (FRAMEWORK+'.framework')/'twitch-verified.png'
        path.write_bytes(b'changed-artwork');self.record()
        with self.assertRaisesRegex(ValueError,'artwork differs'):verify(self.directory,self.revision)

    def test_changed_binary_is_rejected(self):
        (self.directory / "native" / (FRAMEWORK + ".framework") / FRAMEWORK).write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify(self.directory, self.revision)

    def test_extra_archive_or_symlink_is_rejected(self):
        extra = self.directory / "donor.ipa"
        extra.write_bytes(b"synthetic unexpected archive")
        with self.assertRaisesRegex(ValueError, "Unexpected component files"):
            verify(self.directory, self.revision)
        extra.unlink()
        extra.symlink_to(self.directory / "components.json")
        with self.assertRaisesRegex(ValueError, "Unexpected component files"):
            verify(self.directory, self.revision)

    def test_missing_quicklook_receipt_is_rejected(self):
        path=self.directory / "native/compiler.json"
        compiler=json.loads(path.read_text());compiler['uikit_ownership_tests'].pop('quicklook_receipt')
        path.write_text(json.dumps(compiler));self.record()
        with self.assertRaisesRegex(ValueError, "Quick Look"):
            verify(self.directory, self.revision)

    def test_wrong_revision_or_proof_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "revision/proof"):
            verify(self.directory, "b" * 40)
        self.manifest["proof_id"] = "0" * 64
        self.record()
        with self.assertRaisesRegex(ValueError, "revision/proof"):
            verify(self.directory, self.revision)

    def test_missing_validation_is_rejected(self):
        self.manifest["validated"] = False
        self.record()
        with self.assertRaisesRegex(ValueError, "successful component validation"):
            verify(self.directory, self.revision)

    def test_regenerated_admission_header_must_match(self):
        (self.directory / "native/SSNBuild.h").write_text("wrong admission data")
        self.record()
        with self.assertRaisesRegex(ValueError, "admission header mismatch"):
            verify(self.directory, self.revision)

    def test_failed_model_or_toolchain_validation_is_rejected(self):
        path = self.directory / "native/compiler.json"
        compiler = json.loads(path.read_text())
        for key, value in [("model_tests", "FAILED"), ("xcode", "different"), ("uikit_ownership_tests", {})]:
            with self.subTest(key=key):
                changed = dict(compiler, **{key: value})
                path.write_text(json.dumps(changed))
                self.record()
                with self.assertRaises(ValueError):
                    verify(self.directory, self.revision)

    def test_unknown_component_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "checked-out history"):
            verify(self.directory)

    def test_normal_packaging_requires_explicit_components_without_ssh(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/native_frontend/build.py"),
                                 "--donor", "missing-donor.ipa"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--components from Actions", result.stderr)
