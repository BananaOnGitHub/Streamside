"""Generated outputs live beside the checkout, never inside it."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = Path(os.environ.get("STREAMSIDE_ARTIFACTS_DIR", REPO_ROOT.parent / "artifacts")).expanduser().resolve()
if ARTIFACTS_DIR == REPO_ROOT or REPO_ROOT in ARTIFACTS_DIR.parents:
    raise ValueError("STREAMSIDE_ARTIFACTS_DIR must be outside the repository")
NATIVE_ARTIFACTS_DIR = ARTIFACTS_DIR / "native-frontend"
CI_ARTIFACTS_DIR = ARTIFACTS_DIR / "ci"
