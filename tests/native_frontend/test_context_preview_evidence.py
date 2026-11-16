"""Admission boundary for public, donor-free simulator failure stills."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/native_frontend'))
from controls_ui import preserve_failure_images


class ContextPreviewEvidence(unittest.TestCase):
    def test_only_bounded_real_pngs_are_exported_with_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exported = root / 'exported'; exported.mkdir()
            png = b'\x89PNG\r\n\x1a\nowned-fixture'
            (exported / 'owned.png').write_bytes(png)
            (exported / 'movie.mov').write_bytes(b'not a still')
            (exported / 'disguised.png').write_bytes(b'not a PNG')
            (exported / 'large.png').write_bytes(png + bytes(2 * 1024 * 1024))
            (exported / 'link.png').symlink_to(exported / 'owned.png')
            archive = root / 'evidence.zip'
            preserve_failure_images(exported, archive)
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(set(bundle.namelist()), {'owned.png', 'manifest.json'})
                manifest = json.loads(bundle.read('manifest.json'))
                self.assertEqual(manifest['files']['owned.png'], dict(bytes=len(png), sha256=hashlib.sha256(png).hexdigest()))

    def test_still_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exported = root / 'exported'; exported.mkdir()
            for index in range(20):
                (exported / f'{index:02}.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            archive = root / 'evidence.zip'; preserve_failure_images(exported, archive)
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(len(json.loads(bundle.read('manifest.json'))['files']), 8)
