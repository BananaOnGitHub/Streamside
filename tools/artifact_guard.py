#!/usr/bin/env python3
"""Bind validated build bytes to every subsequent packaging step.

Receipts are local build fingerprints, not cryptographic attestations. They live
outside the framework and must travel alongside it for unsigned IPA packaging.
Packagers verify, never silently normalize or regenerate a missing receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
from pathlib import Path

try:
    from .verify_macho import DYLIB_IDENTITY, FRAMEWORK_IDENTITY, verify_bytes
except ImportError:
    from verify_macho import DYLIB_IDENTITY, FRAMEWORK_IDENTITY, verify_bytes

APP_DISPLAY_NAME = "Twitch Streamside"
FRAMEWORK_NAME = "Streamside.framework"
BINARY_NAME = "Streamside"
BUNDLE_ID = "io.github.bananaongithub.tas.streamside"
SCHEMA = 1


def receipt_path(path: Path) -> Path:
    return path.with_name(path.name + ".macho.json")


def inspect_artifact(path: Path, framework: bool) -> tuple[dict, bytes, bytes | None]:
    binary_path = path / BINARY_NAME if framework else path
    data = binary_path.read_bytes()
    record = verify_bytes(data, FRAMEWORK_IDENTITY if framework else DYLIB_IDENTITY,
                          0 if framework else 65536, True, framework,
                          BINARY_NAME if framework else "Streamside.dylib")
    info_data = None
    if framework:
        info_data = (path / "Info.plist").read_bytes()
        info = plistlib.loads(info_data)
        expected = {"CFBundleExecutable": BINARY_NAME, "CFBundleName": BINARY_NAME,
                    "CFBundleIdentifier": BUNDLE_ID, "CFBundlePackageType": "FMWK"}
        if any(info.get(key) != value for key, value in expected.items()):
            raise ValueError("Streamside framework bundle identity is inconsistent")
        record["info_sha256"] = hashlib.sha256(info_data).hexdigest()
        record["version"] = info.get("CFBundleShortVersionString")
    return record, data, info_data


def write_receipt(path: Path, framework: bool) -> None:
    record, _data, _info = inspect_artifact(path, framework)
    receipt_path(path).write_text(json.dumps({"schema": SCHEMA, "artifact": record},
                                           indent=2, sort_keys=True) + "\n", encoding="utf-8")


def checked_artifact(path: Path, framework: bool) -> tuple[bytes, bytes | None]:
    receipt = receipt_path(path)
    if not receipt.is_file():
        raise ValueError(f"verified build receipt is missing: {receipt}; rebuild, do not bypass validation")
    expected = json.loads(receipt.read_text(encoding="utf-8"))
    record, data, info = inspect_artifact(path, framework)
    if expected != {"schema": SCHEMA, "artifact": record}:
        raise ValueError("artifact changed after build validation (hash/layout/identity/metadata mismatch)")
    return data, info


def compare_packaged(data: bytes, expected: bytes, framework: bool = True) -> None:
    # Structural validation gives a useful failure even if a packager picked the
    # raw linker output. Exact bytes additionally catch re-signing or code edits.
    verify_bytes(data, FRAMEWORK_IDENTITY if framework else DYLIB_IDENTITY,
                 0 if framework else 65536, True, framework,
                 BINARY_NAME if framework else "Streamside.dylib")
    if hashlib.sha256(data).digest() != hashlib.sha256(expected).digest() or data != expected:
        raise ValueError("packaged Mach-O differs from the validated build binary")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("record", "check"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--framework", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "record":
            write_receipt(args.path, args.framework)
        else:
            checked_artifact(args.path, args.framework)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"{args.action}: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
