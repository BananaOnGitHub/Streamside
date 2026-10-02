from __future__ import annotations

import json
import plistlib
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from macho_fixture import refresh, segment_command, string_command, synthetic_dylib
import test_tools as fixtures
from tools.artifact_guard import (BINARY_NAME, FRAMEWORK_NAME, checked_artifact,
                                 compare_packaged, receipt_path)
from tools.macho import (LC_ID_DYLIB, LC_LOAD_WEAK_DYLIB, code_signature,
                        header, inject_load_dylib, load_commands)
from tools.patch_ipa import LOAD_PATH, patch_ipa
from tools.package_release import checked_zip
from tools.verify_ipa import verify_archive
from tools.verify_macho import FRAMEWORK_IDENTITY, verify_bytes
from tools.align_macho_segments import align_segments
from tools.shrink_adhoc_signature import shrink


def validate(data: bytes) -> dict:
    return verify_bytes(data, FRAMEWORK_IDENTITY, 0, True, True, BINARY_NAME)


class LayoutContractTests(unittest.TestCase):
    def test_normalization_restores_ranges_and_then_is_byte_identical(self):
        original = synthetic_dylib()
        data = bytearray(original)
        at = segment_command(data, "__DATA_CONST")
        struct.pack_into("<Q", data, at + 32, 40)
        struct.pack_into("<Q", data, at + 48, 40)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / BINARY_NAME
            path.write_bytes(data)
            align_segments(path)
            shrink(path)
            self.assertEqual(path.read_bytes(), original)
            validate(path.read_bytes())
            align_segments(path)
            shrink(path)
            self.assertEqual(path.read_bytes(), original)

    def test_normalized_fixture_and_compact_signature_pass(self):
        result = validate(synthetic_dylib())
        self.assertEqual(result["signature"]["directories"][0]["exec_limit"], 0x4000)

    def test_every_segment_offset_and_size_is_checked(self):
        for name in ("__TEXT", "__DATA_CONST", "__DATA", "__LINKEDIT"):
            for field in (24, 32, 40, 48):
                with self.subTest(name=name, field=field):
                    data = bytearray(synthetic_dylib())
                    at = segment_command(data, name) + field
                    value = struct.unpack_from("<Q", data, at)[0]
                    struct.pack_into("<Q", data, at, value + 1)
                    with self.assertRaises(ValueError):
                        validate(refresh(data))

    def test_16k_gap_or_overlap_is_not_accepted(self):
        for delta in (-0x4000, 0x4000):
            data = bytearray(synthetic_dylib())
            at = segment_command(data, "__DATA")
            struct.pack_into("<Q", data, at + 32, 0x8000 + delta)
            with self.assertRaisesRegex(ValueError, "aligned segment range"):
                validate(refresh(data))

    def test_recreates_unrounded_release_regression(self):
        data = bytearray(synthetic_dylib())
        at = segment_command(data, "__DATA_CONST")
        struct.pack_into("<Q", data, at + 32, 40)
        struct.pack_into("<Q", data, at + 48, 40)
        with self.assertRaisesRegex(ValueError, "16 KiB"):
            validate(refresh(data))

    def test_wrong_install_name_and_duplicate_identity_fail(self):
        data = bytearray(synthetic_dylib())
        data[data.index(b"@rpath/Streamside")] = ord("!")
        with self.assertRaisesRegex(ValueError, "LC_ID_DYLIB"):
            validate(refresh(data))
        data = bytearray(synthetic_dylib())
        info = header(data)
        command = string_command(LC_ID_DYLIB, FRAMEWORK_IDENTITY)
        data[32 + info.command_size:32 + info.command_size + len(command)] = command
        struct.pack_into("<II", data, 16, info.command_count + 1, info.command_size + len(command))
        with self.assertRaisesRegex(ValueError, "LC_ID_DYLIB"):
            validate(refresh(data))

    def test_signature_must_be_aligned_inside_linkedit_and_end_at_eof(self):
        original = synthetic_dylib()
        item = next(c for c in load_commands(original) if c.command == 0x1D)
        offset, size = code_signature(original)
        for changed_offset, changed_size in ((offset + 1, size), (offset, size - 16),
                                             (0x8000, size), (offset, 1)):
            data = bytearray(original)
            struct.pack_into("<II", data, item.offset + 8, changed_offset, changed_size)
            with self.assertRaises(ValueError):
                validate(bytes(data))

    def test_signature_padding_and_bounds_and_slot_count(self):
        offset, size = code_signature(synthetic_dylib())
        for relative, value in ((4, size + 1), (8, 0xFFFFFFFF), (16, size + 1)):
            data = bytearray(synthetic_dylib())
            struct.pack_into(">I", data, offset + relative, value)
            with self.assertRaises(ValueError):
                validate(bytes(data))
        data = bytearray(synthetic_dylib())
        data[-1] = 1
        with self.assertRaisesRegex(ValueError, "padding"):
            validate(bytes(data))

    def test_signature_cannot_overlap_linkedit_table(self):
        data = bytearray(synthetic_dylib())
        info = header(data)
        signature_offset = code_signature(data)[0]
        command = struct.pack("<4I", 0x26, 16, signature_offset - 8, 16)
        data[32 + info.command_size:32 + info.command_size + len(command)] = command
        struct.pack_into("<II", data, 16, info.command_count + 1, info.command_size + len(command))
        with self.assertRaisesRegex(ValueError, "overlaps the signature"):
            validate(refresh(data))

    def test_stale_exec_range_identifier_and_code_hash_fail(self):
        for field, fmt, value in ((72, ">Q", 0x3FF0), (32, ">I", 1)):
            data = bytearray(synthetic_dylib())
            directory = code_signature(data)[0] + 20
            struct.pack_into(fmt, data, directory + field, value)
            with self.assertRaises(ValueError):
                validate(bytes(data))
        data = bytearray(synthetic_dylib())
        directory = code_signature(data)[0] + 20
        data[directory + 88] = ord("!")
        with self.assertRaisesRegex(ValueError, "signing identifier"):
            validate(bytes(data))
        data = bytearray(synthetic_dylib())
        data[0x1000] ^= 1
        with self.assertRaisesRegex(ValueError, "code-page hash"):
            validate(bytes(data))

    def test_even_a_valid_resigned_binary_cannot_replace_build_bytes(self):
        original = synthetic_dylib()
        data = bytearray(original)
        data[0x1000] = 1
        replacement = refresh(data)
        validate(replacement)
        with self.assertRaisesRegex(ValueError, "differs from"):
            compare_packaged(replacement, original)


class PackagingContractTests(unittest.TestCase):
    @staticmethod
    def make_source(root: Path) -> Path:
        source = root / "input.ipa"
        main, _added = inject_load_dylib(fixtures.synthetic_executable(), "@rpath/Tweach.framework/Tweach")
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("Payload/Twitch.app/Info.plist", plistlib.dumps({"CFBundleExecutable": "Twitch"}))
            archive.writestr("Payload/Twitch.app/Twitch", main)
            archive.writestr("Payload/Twitch.app/Assets.car", b"assets")
            archive.writestr("Payload/Twitch.app/Frameworks/Tweach.framework/Info.plist", b"old")
            archive.writestr("Payload/Twitch.app/Frameworks/Tweach.framework/Tweach", b"old")
        return source

    def test_migrates_full_legacy_framework_and_repatches_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework = fixtures.IPAPatcherTests.make_framework(root)
            source = self.make_source(root)
            output = root / "output.ipa"
            patch_ipa(source, framework, output)
            with zipfile.ZipFile(output) as archive:
                self.assertFalse(any("Tweach" in name for name in archive.namelist()))
                verify_archive(archive, synthetic_dylib(), (framework / "Info.plist").read_bytes())
            second = root / "second.ipa"
            patch_ipa(output, framework, second)
            with zipfile.ZipFile(output) as first, zipfile.ZipFile(second) as again:
                self.assertEqual({n: first.read(n) for n in first.namelist()},
                                 {n: again.read(n) for n in again.namelist()})

    def test_missing_receipt_wrong_hash_or_changed_info_fails_direct_patcher(self):
        for mode in ("missing", "hash", "info", "binary"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                framework = fixtures.IPAPatcherTests.make_framework(root)
                source = self.make_source(root)
                receipt = receipt_path(framework)
                if mode == "missing":
                    receipt.unlink()
                elif mode == "hash":
                    document = json.loads(receipt.read_text())
                    document["artifact"]["sha256"] = "0" * 64
                    receipt.write_text(json.dumps(document))
                elif mode == "info":
                    (framework / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Tweach"}))
                else:
                    data = bytearray(synthetic_dylib())
                    data[0x1000] = 1
                    (framework / BINARY_NAME).write_bytes(refresh(data))
                with self.assertRaises(ValueError):
                    patch_ipa(source, framework, root / "output.ipa")
                self.assertFalse((root / "output.ipa").exists())

    def test_packaging_corruption_fails_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework = fixtures.IPAPatcherTests.make_framework(root)
            source = self.make_source(root)
            output = root / "output.ipa"
            output.write_bytes(b"existing output")
            original_write = zipfile.ZipFile.writestr

            def corrupt(archive, item, data, *args, **kwargs):
                name = item.filename if isinstance(item, zipfile.ZipInfo) else item
                if name.endswith("/Streamside"):
                    changed = bytearray(data)
                    changed[0x1000] ^= 1
                    data = refresh(changed)
                return original_write(archive, item, data, *args, **kwargs)

            with patch.object(zipfile.ZipFile, "writestr", corrupt), self.assertRaises(ValueError):
                patch_ipa(source, framework, output, force=True)
            self.assertEqual(output.read_bytes(), b"existing output")
            self.assertFalse(list(root.glob("*.tmp")))

    def test_weak_or_duplicate_main_load_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework = fixtures.IPAPatcherTests.make_framework(root)
            for mode in ("weak", "duplicate"):
                output = root / f"{mode}.ipa"
                main, _ = inject_load_dylib(fixtures.synthetic_executable(), LOAD_PATH)
                data = bytearray(main)
                command = next(c for c in load_commands(data) if c.command == 0xC)
                if mode == "weak":
                    struct.pack_into("<I", data, command.offset, LC_LOAD_WEAK_DYLIB)
                else:
                    info = header(data)
                    raw = data[command.offset:command.offset + command.size]
                    data[32 + info.command_size:32 + info.command_size + len(raw)] = raw
                    struct.pack_into("<II", data, 16, info.command_count + 1, info.command_size + len(raw))
                with zipfile.ZipFile(output, "w") as archive:
                    archive.writestr("Payload/Twitch.app/Info.plist", plistlib.dumps({"CFBundleExecutable": "Twitch"}))
                    archive.writestr("Payload/Twitch.app/Twitch", data)
                    archive.writestr("Payload/Twitch.app/Assets.car", b"assets")
                    archive.writestr(f"Payload/Twitch.app/Frameworks/{FRAMEWORK_NAME}/{BINARY_NAME}", synthetic_dylib())
                    archive.writestr(f"Payload/Twitch.app/Frameworks/{FRAMEWORK_NAME}/Info.plist", (framework / "Info.plist").read_bytes())
                with zipfile.ZipFile(output) as archive, self.assertRaisesRegex(ValueError, "required Streamside"):
                    verify_archive(archive, synthetic_dylib(), (framework / "Info.plist").read_bytes())

    def test_distribution_zip_readback_enforces_build_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / BINARY_NAME
            original = synthetic_dylib()
            binary.write_bytes(original)
            output = root / "bundle.zip"
            checked_zip(output, [(binary, BINARY_NAME)], {BINARY_NAME: (original, True)})
            saved = output.read_bytes()
            changed = bytearray(original)
            changed[0x1000] ^= 1
            binary.write_bytes(refresh(changed))
            with self.assertRaisesRegex(ValueError, "differs from"):
                checked_zip(output, [(binary, BINARY_NAME)], {BINARY_NAME: (original, True)})
            self.assertEqual(output.read_bytes(), saved)
            self.assertFalse(list(root.glob("*.tmp")))


class VersionContractTests(unittest.TestCase):
    def test_streamside_app_name_is_the_distribution_contract(self):
        from tools.artifact_guard import APP_DISPLAY_NAME
        self.assertEqual(APP_DISPLAY_NAME, "Twitch Streamside")

    def test_version_metadata_is_synchronized(self):
        root = Path(__file__).resolve().parent.parent
        version = (root / "VERSION").read_text().strip()
        info = plistlib.loads((root / "packaging/StreamsideFramework-Info.plist").read_bytes())
        self.assertEqual(info["CFBundleShortVersionString"], version)
        self.assertTrue(info["CFBundleVersion"].startswith(version + "."))
        build = info["CFBundleVersion"][len(version) + 1:]
        self.assertTrue(build.isdecimal() and int(build) > 0)
        self.assertIn(f'#define TAS_REPORT_VERSION "{version}-build.{build}"', (root / "src/TASDiagnostics.c").read_text())


if __name__ == "__main__":
    unittest.main()
