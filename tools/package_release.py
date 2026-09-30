#!/usr/bin/env python3
"""Create the release bundle."""

from __future__ import annotations

import hashlib
import os
import plistlib
import shutil
import tempfile
import zipfile
from pathlib import Path

try:
    from .artifact_guard import (BINARY_NAME, FRAMEWORK_NAME, checked_artifact,
                                 compare_packaged, receipt_path)
except ImportError:
    from artifact_guard import (BINARY_NAME, FRAMEWORK_NAME, checked_artifact,
                                compare_packaged, receipt_path)

ROOT = Path(__file__).resolve().parent.parent


def checked_zip(output: Path, files: list[tuple[Path, str]],
                binary_entries: dict[str, tuple[bytes, bool]]) -> None:
    """Check finished archive bytes before exposing any final bundle filename."""
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip.tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for source, destination in files:
                archive.write(source, destination)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() or len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError("invalid release bundle")
            for entry, (binary, framework) in binary_entries.items():
                compare_packaged(archive.read(entry), binary, framework)
            for source, destination in files:
                if archive.read(destination) != source.read_bytes():
                    raise ValueError(f"release bundle content changed: {destination}")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    dylib = ROOT / "build" / "TwitchAdBlock.dylib"
    framework = ROOT / "build" / FRAMEWORK_NAME
    framework_binary = framework / BINARY_NAME
    framework_info = framework / "Info.plist"
    if not dylib.is_file():
        raise SystemExit("build/TwitchAdBlock.dylib is missing; run make build first")
    if not framework_binary.is_file() or not framework_info.is_file():
        raise SystemExit("build/Streamside.framework is incomplete; run make build first")
    verified_dylib, _info = checked_artifact(dylib, False)
    verified_framework, verified_info = checked_artifact(framework, True)
    if plistlib.loads(verified_info).get("CFBundleShortVersionString") != version:
        raise ValueError("framework version differs from release VERSION")

    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    release_dylib = dist / "TwitchAdBlock.dylib"
    shutil.copy2(dylib, release_dylib)
    compare_packaged(release_dylib.read_bytes(), verified_dylib, False)
    shutil.copy2(receipt_path(dylib), receipt_path(release_dylib))
    release_framework = dist / "Streamside.framework.zip"
    framework_entry = f"{FRAMEWORK_NAME}/{BINARY_NAME}"
    checked_zip(release_framework, [
        (framework_binary, framework_entry),
        (framework_info, f"{FRAMEWORK_NAME}/Info.plist"),
        (receipt_path(framework), receipt_path(framework).name),
    ], {framework_entry: (verified_framework, True)})
    debs = sorted(dist.glob(f"dev.tas.twitchadblock_{version}_*.deb"))
    if len(debs) != 2:
        raise SystemExit("expected rootful and rootless DEBs; run make deb first")
    bundle = dist / f"TwitchAdBlock-VAFT-iOS-{version}.zip"
    files = [
        (dylib, "TwitchAdBlock.dylib"),
        (framework_binary, framework_entry),
        (framework_info, f"{FRAMEWORK_NAME}/Info.plist"),
        (receipt_path(framework), receipt_path(framework).name),
        (receipt_path(dylib), receipt_path(dylib).name),
        (ROOT / "VERSION", "VERSION"),
        (ROOT / "tools" / "patch_ipa.py", "tools/patch_ipa.py"),
        (ROOT / "tools" / "macho.py", "tools/macho.py"),
        (ROOT / "tools" / "artifact_guard.py", "tools/artifact_guard.py"),
        (ROOT / "tools" / "verify_macho.py", "tools/verify_macho.py"),
        (ROOT / "tools" / "verify_ipa.py", "tools/verify_ipa.py"),
        (ROOT / "README.md", "README.md"),
        (ROOT / "CHANGELOG.md", "CHANGELOG.md"),
        (ROOT / "LICENSE", "LICENSE"),
        (ROOT / "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        (ROOT / "UPSTREAM.md", "UPSTREAM.md"),
    ]
    files.extend((deb, deb.name) for deb in debs)
    prefix = f"TwitchAdBlock-VAFT-iOS-{version}/"
    checked_zip(bundle, [(source, prefix + destination) for source, destination in files], {
        prefix + "TwitchAdBlock.dylib": (verified_dylib, False),
        prefix + framework_entry: (verified_framework, True),
    })
    # Recheck receipts after packaging as well; a staging race must fail closed.
    checked_artifact(dylib, False)
    checked_artifact(framework, True)

    checksums = []
    for path in (release_dylib, release_framework, *debs, bundle):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {path.name}")
    (dist / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
