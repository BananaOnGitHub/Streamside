"""Documentation layout is part of the offline developer-bundle contract."""
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.package_release import checked_zip, documentation_files


class DocumentationPackageTests(unittest.TestCase):
    def test_current_tree_includes_root_guides_moved_notices_and_archive(self):
        root = Path(__file__).resolve().parents[1]
        files = documentation_files(root)
        names = [name for _, name in files]
        self.assertEqual(len(names), len(set(names)))
        for name in (
            "README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE",
            "docs/README.md", "docs/ARCHITECTURE.md", "docs/HISTORY.md",
            "docs/UPSTREAM.md", "docs/THIRD_PARTY_NOTICES.md",
            "docs/licenses/MIT-NOTICES.txt",
            "docs/features/third-party-emotes/README.md",
            "docs/features/third-party-emotes/CHAT_RENDERING.md",
            "docs/archive/README.md",
            "docs/assets/streamsidelogo.png",
        ):
            self.assertIn(name, names)
        self.assertNotIn("UPSTREAM.md", names)
        self.assertNotIn("THIRD_PARTY_NOTICES.md", names)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "documentation.zip"
            checked_zip(output, files, {})
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                for source, name in files:
                    self.assertEqual(source.read_bytes(), archive.read(name))

    def test_missing_notice_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md", "LICENSE", "SECURITY.md",
                         "docs/README.md", "docs/UPSTREAM.md", "docs/THIRD_PARTY_NOTICES.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            with self.assertRaisesRegex(ValueError, "MIT-NOTICES"):
                documentation_files(root)


if __name__ == "__main__":
    unittest.main()
