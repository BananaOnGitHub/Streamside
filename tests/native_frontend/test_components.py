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
                path.write_bytes(b"synthetic-owned-fixture")
            generate_header(json.loads((ROOT / "native/twitch32.json").read_text()), proof, self.revision, directory / "SSNBuild.h")
            config = json.loads(build_inputs(ROOT, directory / "SSNBuild.h", mode, proof, self.revision)["config.json"])
            pin = config["toolchain"]
            compiler = dict(source_revision=self.revision, proof_id=proof, mode=mode, transferred_inputs=config["inputs"],
                            xcode="Xcode " + pin["xcode_version"] + "\nBuild version " + pin["xcode_build"], sdk_version=pin["iphoneos_sdk"],
                            model_tests="PASS: synthetic fixture",
                            uikit_ownership_tests=dict(result="PASS",receipt=dict(passed=True,native=mode=="native",blocked=2 if mode=="native" else 0,failures=0)), codesign="ad-hoc; IPA still requires device-authorized re-signing")
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
        for key, value in [("model_tests", "FAILED"), ("xcode", "different")]:
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
