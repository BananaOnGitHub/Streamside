"""Viewport-first projection against the production JS source."""
from pathlib import Path
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parent.parent
class ViewportTests(unittest.TestCase):
 def test_visible_ranges_measurement_membership_and_immutable_budgets(self):
  node=shutil.which('node')
  if not node:self.skipTest('Node.js required')
  fixture=(ROOT/'tests/fixtures/investigation_bootstrap.js').read_text()
  source=(ROOT/'src/rn/Investigation.js').read_text()
  cases=(ROOT/'tests/fixtures/investigation_viewport.js').read_text()
  script="const vm=require('vm');const c=vm.createContext({});c._runtimeGlobal=c;c._observeNative=()=>1;vm.runInContext("+repr(fixture+'\n'+source+'\n'+cases+'\nexerciseViewport(install());')+",c);"
  result=subprocess.run([node,'-e',script],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
