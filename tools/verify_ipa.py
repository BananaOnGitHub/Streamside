#!/usr/bin/env python3
"""Validate an unsigned IPA against its verified Streamside build artifact."""
from __future__ import annotations

import argparse
import plistlib
import zipfile
from pathlib import Path, PurePosixPath

try:
    from .artifact_guard import BINARY_NAME, FRAMEWORK_NAME, checked_artifact, compare_packaged
    from .macho import LC_LOAD_DYLIB, dylib_loads, encryption_ids
    from .verify_macho import FRAMEWORK_IDENTITY
except ImportError:
    from artifact_guard import BINARY_NAME, FRAMEWORK_NAME, checked_artifact, compare_packaged
    from macho import LC_LOAD_DYLIB, dylib_loads, encryption_ids
    from verify_macho import FRAMEWORK_IDENTITY

# Only input migration and historical provenance retain donor names. No output
# load command or package entry may retain these old injected components.
LEGACY_FILES = {"Tweach.dylib", "TwitchAdBlock.dylib"}
LEGACY_FRAMEWORKS = {"Tweach.framework", "VAFT.framework", "TwitchAdBlock.framework"}


def verify_archive(archive: zipfile.ZipFile, expected_binary: bytes,
                   expected_info: bytes) -> None:
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise ValueError("duplicate IPA entries are forbidden")
    bad = archive.testzip()
    if bad:
        raise ValueError(f"output CRC failure: {bad}")
    matches = [name for name in names if len(PurePosixPath(name).parts) == 3
               and name.startswith("Payload/") and PurePosixPath(name).parts[1].endswith(".app")
               and name.endswith("/Info.plist")]
    if len(matches) != 1:
        raise ValueError("expected exactly one main app Info.plist")
    root = str(PurePosixPath(matches[0]).parent)
    info = plistlib.loads(archive.read(matches[0]))
    executable_name = info.get("CFBundleExecutable")
    if not isinstance(executable_name, str) or PurePosixPath(executable_name).name != executable_name:
        raise ValueError("invalid CFBundleExecutable")
    executable = archive.read(f"{root}/{executable_name}")
    if any(encryption_ids(executable)):
        raise ValueError("packaged main executable is encrypted")
    loads = dylib_loads(executable)
    target = [(kind, name) for kind, name in loads
              if "Streamside" in name or any(old in name for old in ("Tweach", "VAFT.framework", "TwitchAdBlock"))]
    if target != [(LC_LOAD_DYLIB, FRAMEWORK_IDENTITY)]:
        raise ValueError("main executable must have exactly one required Streamside load and no donor loads")
    if any((LEGACY_FILES | LEGACY_FRAMEWORKS) & set(PurePosixPath(name).parts) for name in names):
        raise ValueError("obsolete donor component remains in the IPA")
    binary_entry = f"{root}/Frameworks/{FRAMEWORK_NAME}/{BINARY_NAME}"
    info_entry = f"{root}/Frameworks/{FRAMEWORK_NAME}/Info.plist"
    compare_packaged(archive.read(binary_entry), expected_binary)
    if archive.read(info_entry) != expected_info:
        raise ValueError("framework Info.plist changed during packaging")
    if f"{root}/Assets.car" not in names:
        raise ValueError("Assets.car is missing")


def verify_ipa(path: Path, framework: Path) -> None:
    binary, info = checked_artifact(framework, True)
    with zipfile.ZipFile(path) as archive:
        verify_archive(archive, binary, info)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa", type=Path)
    parser.add_argument("--framework", type=Path, default=Path("build/Streamside.framework"))
    args = parser.parse_args()
    try:
        verify_ipa(args.ipa, args.framework)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(f"verified unsigned IPA: {args.ipa}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
