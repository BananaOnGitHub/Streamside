"""Output placement must hold across command-line entry points and overrides."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkspacePathsTests(unittest.TestCase):
    def run_paths(self, override=None):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("STREAMSIDE_ARTIFACTS_DIR", None)
        if override is not None:
            env["STREAMSIDE_ARTIFACTS_DIR"] = str(override)
        return subprocess.run([sys.executable, "-c",
            "import json; from tools.workspace_paths import BUILD_DIR, DIST_DIR; "
            "print(json.dumps([str(BUILD_DIR), str(DIST_DIR)]))"],
            cwd=ROOT, env=env, capture_output=True, text=True)

    def test_default_is_sibling_artifacts(self):
        result = self.run_paths()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
            [str(ROOT.parent / "artifacts/build"), str(ROOT.parent / "artifacts/dist")])

    def test_external_override_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="streamside artifacts ") as directory:
            result = self.run_paths(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout),
                [str(Path(directory) / "build"), str(Path(directory) / "dist")])

    def test_checkout_and_symlink_into_checkout_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "checkout"
            link.symlink_to(ROOT, target_is_directory=True)
            for path in (ROOT, ROOT / "build", link / "generated"):
                with self.subTest(path=path):
                    result = self.run_paths(path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("must be outside the repository", result.stderr)
