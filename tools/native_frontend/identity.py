"""Stable source/probe identity shared by compilation and local IPA assembly."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source_identity():
    digest = hashlib.sha256(b"swiftui\0")
    digest.update((ROOT / "tools/workspace_paths.py").read_bytes())
    for directory in ("native", "tools/native_frontend"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and path.suffix in {".c", ".h", ".m", ".swift", ".json", ".py", ".tbd", ".png"}:
                digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes())
    digest.update((ROOT / "native/framework-info.plist").read_bytes())
    return digest.hexdigest()
