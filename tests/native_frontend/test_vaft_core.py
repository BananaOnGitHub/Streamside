"""Execute the shared production playlist engine; networking/Foundation are fake."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class SharedVAFT(unittest.TestCase):
    def test_shared_playlist_algorithm_and_stream_ownership(self):
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'vaft-core'
            built=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-pthread',
                '-I'+str(ROOT/'src'),str(ROOT/'tests/native_frontend/vaft_driver.c'),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            tested=subprocess.run([binary],capture_output=True,text=True,timeout=10)
            self.assertEqual(tested.returncode,0,tested.stderr)
            self.assertIn('VAFT_CORE PASS',tested.stdout)
