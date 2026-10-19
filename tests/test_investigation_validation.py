"""Clean-build proof verification has no donor/runtime dependency."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
class ValidationTests(unittest.TestCase):
 def test_current_proof_and_missing_tampered_or_incomplete_proof(self):
  command=['python3',str(ROOT/'tools/validate_investigation_runtime.py'),'--check']
  original=json.loads((ROOT/'diagnostics/validation/hermes-v1.json').read_text())
  self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
  with tempfile.TemporaryDirectory() as tmp:
   file=Path(tmp)/'proof.json';self.assertNotEqual(subprocess.run(command+[str(file)],capture_output=True).returncode,0)
   for field,value in [('passed',False),('inputs',{}),('profiles',[]),('donor_getters',{}),('runtime_commit','wrong')]:
    altered=dict(original);altered[field]=value;file.write_text(json.dumps(altered));self.assertNotEqual(subprocess.run(command+[str(file)],capture_output=True).returncode,0,field)
