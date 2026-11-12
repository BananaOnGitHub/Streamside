"""Stable source/probe identity shared by compilation and local IPA assembly."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source_identity(frontend="swiftui"):
    digest = hashlib.sha256(frontend.encode() + b"\0")
    digest.update((ROOT / "tools/workspace_paths.py").read_bytes())
    for directory in ("native", "tools/native_frontend"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and path.suffix in {".c", ".h", ".m", ".swift", ".json", ".py", ".tbd"}:
                digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()
