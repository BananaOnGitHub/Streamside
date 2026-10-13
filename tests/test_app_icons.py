"""Sideload icon metadata, bytes, readback, and native-resource preservation."""
import copy
from pathlib import Path
import plistlib
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from tools.app_icons import (ICON_DIRECTORY, ICON_SIZES, IPAD_BASES, PHONE_BASES,
                             apply_icon_info, check_png, load_icons)
from tools.patch_ipa import patch_ipa, update_app_info
from tools.verify_ipa import verify_archive
import test_tools as fixtures


class AppIconTests(unittest.TestCase):
    def info(self):
        return {
            "CFBundleExecutable": "Twitch", "CFBundleIdentifier": "tv.twitch",
            "CFBundleShortVersionString": "31.5", "CFBundleVersion": "262752111271985979",
            "MinimumOSVersion": "16.4", "UIDesignRequiresCompatibility": True,
            "UIPrerenderedIcon": True, "CFBundleIconName": "TwitchAppIcon",
            "CFBundleIconFile": "old.png", "CFBundleIconFiles": ["old"],
            "CFBundleIconName~ipad": "TwitchAppIcon",
            "CFBundleIcons": {"CFBundlePrimaryIcon": {
                "CFBundleIconName": "TwitchAppIcon", "CFBundleIconFiles": ["TwitchAppIcon60x60"],
                "NSAppIconActionTintColorName": "PreservedTint"},
                "CFBundleAlternateIcons": {"NativeAlternative": {"CFBundleIconName": "NativeAlternative"}}},
            "CFBundleIcons~ipad": {"CFBundlePrimaryIcon": {
                "CFBundleIconName": "TwitchAppIcon", "CFBundleIconFiles": ["TwitchAppIcon76x76"]}},
        }

    def source(self, root):
        source = root / "input.ipa"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("Payload/Twitch.app/Info.plist", plistlib.dumps(self.info()))
            archive.writestr("Payload/Twitch.app/Twitch", fixtures.synthetic_executable())
            archive.writestr("Payload/Twitch.app/Assets.car", b"donor asset catalog")
            archive.writestr("Payload/Twitch.app/TwitchAppIcon60x60@2x.png", b"native icon retained")
            archive.writestr("Payload/Twitch.app/PlugIns/Example.appex/Info.plist", b"extension unchanged")
        return source

    def test_primary_selectors_are_changed_but_native_metadata_is_not(self):
        original = self.info()
        saved = copy.deepcopy(original)
        result = apply_icon_info(original)
        self.assertEqual(original, saved)
        for key, bases in (("CFBundleIcons", PHONE_BASES), ("CFBundleIcons~ipad", IPAD_BASES)):
            primary = result[key]["CFBundlePrimaryIcon"]
            self.assertNotIn("CFBundleIconName", primary)
            self.assertEqual(primary["CFBundleIconFiles"], bases)
            self.assertIs(primary["UIPrerenderedIcon"], False)
        for key in ("CFBundleIconName", "CFBundleIconFile", "CFBundleIconFiles", "CFBundleIconName~ipad"):
            self.assertNotIn(key, result)
        for key in ("CFBundleExecutable", "CFBundleIdentifier", "CFBundleShortVersionString",
                    "CFBundleVersion", "MinimumOSVersion", "UIDesignRequiresCompatibility"):
            self.assertEqual(result[key], original[key])
        self.assertEqual(result["CFBundleIcons"]["CFBundleAlternateIcons"], original["CFBundleIcons"]["CFBundleAlternateIcons"])
        self.assertEqual(result["CFBundleIcons"]["CFBundlePrimaryIcon"]["NSAppIconActionTintColorName"], "PreservedTint")
        self.assertEqual(apply_icon_info(result), result)

    def test_partial_metadata_and_no_icons_are_supported(self):
        for data in ({}, {"CFBundleIcons": {}}, {"CFBundleIcons~ipad": {}}):
            result = plistlib.loads(update_app_info(plistlib.dumps(data)))
            self.assertEqual(result["CFBundleName"], "Twitch Streamside")
            self.assertNotIn("UIDesignRequiresCompatibility", result)
            self.assertIn("CFBundleIcons~ipad", result)

    def test_malformed_primary_metadata_is_refused(self):
        for data in ({"CFBundleIcons": "bad"}, {"CFBundleIcons~ipad": []},
                     {"CFBundleIcons": {"CFBundlePrimaryIcon": "bad"}}):
            with self.assertRaisesRegex(ValueError, "unsupported"):
                apply_icon_info(data)

    def test_checked_in_sizes_have_no_alpha_or_custom_appearance_variants(self):
        icons = load_icons()
        self.assertEqual(set(icons), set(ICON_SIZES))
        for name, data in icons.items():
            with self.subTest(name=name):
                check_png(data, ICON_SIZES[name])
                self.assertEqual(data[25], 2)  # RGB, not RGBA.
                self.assertNotIn("dark", name.lower())
                self.assertNotIn("tinted", name.lower())
                self.assertNotIn("clear", name.lower())

    def test_missing_wrong_size_transparent_truncated_or_corrupt_png_is_refused(self):
        data = (ICON_DIRECTORY / "StreamsideIcon60x60@3x.png").read_bytes()
        for changed in (b"not PNG", data[:-1], data + b"extra", data[:80] + b"X" + data[81:]):
            with self.subTest(data=changed[:16]), self.assertRaises(ValueError):
                check_png(changed, 180)
        with self.assertRaisesRegex(ValueError, "120x120"):
            check_png(data, 120)
        rgba = bytearray(data)
        rgba[25] = 6
        struct.pack_into(">I", rgba, 29, zlib.crc32(rgba[12:29]) & 0xFFFFFFFF)
        with self.assertRaisesRegex(ValueError, "opaque RGB"):
            check_png(bytes(rgba), 180)
        kind, payload = b"tRNS", b"\0" * 6
        chunk = struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        with self.assertRaisesRegex(ValueError, "transparency"):
            check_png(data[:33] + chunk + data[33:], 180)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileNotFoundError):
            load_icons(Path(directory))

    def test_finished_ipa_icons_assets_extensions_and_repatching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework = fixtures.IPAPatcherTests.make_framework(root)
            source, output, second = self.source(root), root / "first.ipa", root / "second.ipa"
            patch_ipa(source, framework, output)
            patch_ipa(output, framework, second)
            with zipfile.ZipFile(output) as first, zipfile.ZipFile(second) as again:
                self.assertEqual(len(again.namelist()), len(set(again.namelist())))
                for name, expected in load_icons().items():
                    self.assertEqual(first.read("Payload/Twitch.app/" + name), expected)
                    self.assertEqual(again.read("Payload/Twitch.app/" + name), expected)
                for name, expected in {"Assets.car": b"donor asset catalog", "TwitchAppIcon60x60@2x.png": b"native icon retained",
                                       "PlugIns/Example.appex/Info.plist": b"extension unchanged"}.items():
                    self.assertEqual(again.read("Payload/Twitch.app/" + name), expected)
                info = plistlib.loads(again.read("Payload/Twitch.app/Info.plist"))
                self.assertIs(info["UIDesignRequiresCompatibility"], True)
                self.assertEqual(info["CFBundleShortVersionString"], "31.5")

    def test_icon_corruption_during_packaging_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework, source = fixtures.IPAPatcherTests.make_framework(root), self.source(root)
            output = root / "output.ipa"
            output.write_bytes(b"existing")
            original_write = zipfile.ZipFile.writestr
            def corrupt(archive, item, data, *args, **kwargs):
                name = item.filename if isinstance(item, zipfile.ZipInfo) else item
                if name.endswith("/StreamsideIcon60x60@3x.png"):
                    data = b"corrupted"
                return original_write(archive, item, data, *args, **kwargs)
            with patch.object(zipfile.ZipFile, "writestr", corrupt), self.assertRaisesRegex(ValueError, "app icon"):
                patch_ipa(source, framework, output, force=True)
            self.assertEqual(output.read_bytes(), b"existing")
            self.assertFalse(list(root.glob("*.tmp")))

    def test_independent_verifier_rejects_missing_icons_and_old_asset_selectors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework, source = fixtures.IPAPatcherTests.make_framework(root), self.source(root)
            output = root / "output.ipa"
            patch_ipa(source, framework, output)
            for mode in ("missing", "metadata"):
                changed = root / f"{mode}.ipa"
                with zipfile.ZipFile(output) as original, zipfile.ZipFile(changed, "w") as archive:
                    for item in original.infolist():
                        if mode == "missing" and item.filename.endswith("/StreamsideIcon60x60@3x.png"):
                            continue
                        data = original.read(item)
                        if mode == "metadata" and item.filename == "Payload/Twitch.app/Info.plist":
                            info = plistlib.loads(data)
                            info["CFBundleIcons"]["CFBundlePrimaryIcon"]["CFBundleIconName"] = "TwitchAppIcon"
                            data = plistlib.dumps(info)
                        archive.writestr(item, data)
                with zipfile.ZipFile(changed) as archive, self.assertRaisesRegex(ValueError, "icon"):
                    verify_archive(archive, fixtures.synthetic_dylib(), (framework / "Info.plist").read_bytes())

    def test_direct_cli_patching_and_verification_use_the_same_icon_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            framework, source = fixtures.IPAPatcherTests.make_framework(root), self.source(root)
            output = root / "output.ipa"
            tools = Path(__file__).resolve().parents[1] / "tools"
            for command in ([sys.executable, str(tools / "patch_ipa.py"), str(source),
                             "--framework", str(framework), "--output", str(output)],
                            [sys.executable, str(tools / "verify_ipa.py"), str(output),
                             "--framework", str(framework)]):
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
