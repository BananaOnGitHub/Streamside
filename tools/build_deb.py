#!/usr/bin/env python3
"""Build rootful and rootless jailbreak packages without requiring Theos."""

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ID = "dev.tas.twitchadblock"
PACKAGE_NAME = "Twitch VAFT"
INSTALL_RELATIVE = Path("Library/MobileSubstrate/DynamicLibraries")
REPRODUCIBLE_TIMESTAMP = 946684800

def control(version: str, architecture: str) -> str:
    return "\n".join(
        [
            f"Package: {PACKAGE_ID}",
            f"Name: {PACKAGE_NAME}",
            f"Version: {version}",
            f"Architecture: {architecture}",
            "Description: Native VAFT-based video ad filtering for the Twitch iOS app.",
            "Author: TwitchAdBlock-VAFT-iOS contributors",
            "Maintainer: TwitchAdBlock-VAFT-iOS contributors",
            "Section: Tweaks",
            "Depends: mobilesubstrate",
            "Conflicts: com.level3tjg.twitchadblock",
            "",
        ]
    )

def build_variant(version: str, scheme: str, prefix: Path, architecture: str) -> Path:
    dylib = ROOT / "build" / "TwitchAdBlock.dylib"
    filter_plist = ROOT / "packaging" / "TwitchAdBlock.plist"
    if not dylib.is_file():
        raise SystemExit("build/TwitchAdBlock.dylib is missing; run make build first")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    output = dist / f"{PACKAGE_ID}_{version}_{architecture}.deb"
    with tempfile.TemporaryDirectory(prefix=f"tas-{scheme}-") as directory:
        package_root = Path(directory)
        os.chmod(package_root, 0o755)
        metadata = package_root / "DEBIAN"
        install = package_root / prefix / INSTALL_RELATIVE
        metadata.mkdir(parents=True)
        install.mkdir(parents=True)
        (metadata / "control").write_text(control(version, architecture), encoding="utf-8")
        shutil.copy2(dylib, install / "TwitchAdBlock.dylib")
        shutil.copy2(filter_plist, install / "TwitchAdBlock.plist")
        os.chmod(install / "TwitchAdBlock.dylib", 0o755)
        os.chmod(install / "TwitchAdBlock.plist", 0o644)
        for path in sorted(package_root.rglob("*"), reverse=True):
            os.utime(path, (REPRODUCIBLE_TIMESTAMP, REPRODUCIBLE_TIMESTAMP), follow_symlinks=False)
        os.utime(package_root, (REPRODUCIBLE_TIMESTAMP, REPRODUCIBLE_TIMESTAMP))
        environment = os.environ.copy()
        environment.setdefault("SOURCE_DATE_EPOCH", str(REPRODUCIBLE_TIMESTAMP))
        subprocess.run(
            ["dpkg-deb", "--root-owner-group", "-Zxz", "-z9", "--build", str(package_root), str(output)],
            check=True,
