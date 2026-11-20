"""Host checks for live build logging, failure propagation and bounded cleanup."""
import contextlib
import io
import os
import re
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/native_frontend"))
from build_progress import run_logged


class BuildProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.log = self.root / "build.log"
        self.summary = self.root / "summary.md"
        environment = patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(self.summary), "GITHUB_ACTIONS": "true"})
        environment.start(); self.addCleanup(environment.stop)

    def test_output_is_live_before_process_finishes(self):
        released = self.root / "release"
        class LiveSink(io.StringIO):
            def write(self, value):
                if value == "stream-marker\n": released.touch()
                return super().write(value)
        sink = LiveSink()
        code = "import time; from pathlib import Path; print('stream-marker', flush=True); " \
               "p=Path(" + repr(str(released)) + "); " \
               "exec('while not p.exists(): time.sleep(0.01)'); print('finished')"
        with contextlib.redirect_stdout(sink):
            observed = run_logged([sys.executable, "-u", "-c", code], cwd=self.root,
                                  log_path=self.log, timeout=3, label="Live output", summary=True)
        self.assertEqual(observed, "stream-marker\nfinished")
        self.assertTrue(released.exists(), "Output was buffered until command exit")
        self.assertIn("PASS: Live output", sink.getvalue())
        self.assertIn("**PASS** Live output", self.summary.read_text())

    def test_nonzero_exit_retains_output_and_fails_summary(self):
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            with self.assertRaisesRegex(RuntimeError, "exited 7"):
                run_logged([sys.executable, "-c", "print('specific failure'); raise SystemExit(7)"],
                           cwd=self.root, log_path=self.log, label="Compile fixture", summary=True)
        self.assertIn("specific failure", self.log.read_text())
        self.assertIn("::error title=Compile fixture", sink.getvalue())
        self.assertIn("**FAIL** Compile fixture", self.summary.read_text())

    def test_timeout_preserves_partial_output_and_kills_children(self):
        # A child that would write later must not outlive its timed-out parent.
        late = self.root / "escaped-child"
        child = "import time; from pathlib import Path; time.sleep(2); Path(" + repr(str(late)) + ").touch()"
        code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); print('partial',flush=True); time.sleep(20)"
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                run_logged([sys.executable, "-u", "-c", code], cwd=self.root,
                           log_path=self.log, timeout=0.5, label="Timeout fixture")
        self.assertIn("partial", self.log.read_text())
        time.sleep(2)
        self.assertFalse(late.exists(), "Child survived the owned command timeout")

    def test_completion_output_extends_only_finalization_and_requires_exit_zero(self):
        marker = re.compile(r"^suite passed\nsummary\n", re.MULTILINE)
        script = "import time; print('suite passed'); time.sleep(.1); print('summary'); time.sleep(1.1); "
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code), contextlib.redirect_stdout(io.StringIO()) as sink:
                def run():
                    return run_logged([sys.executable, "-u", "-c", script + f"raise SystemExit({exit_code})"],
                                      cwd=self.root, log_path=self.log, timeout=1, finalization=(marker, 2))
                if exit_code:
                    with self.assertRaisesRegex(RuntimeError, "exited 7"):
                        run()
                else:
                    self.assertEqual(run(), "suite passed\nsummary")
                self.assertIn("Test suite finished: allowing up to 2s", sink.getvalue())

    def test_finalization_timeout_is_bounded_even_with_repeated_completion_output(self):
        marker = re.compile(r"^suite passed\n", re.MULTILINE)
        code = "import time; exec(\"while True: print('suite passed'); time.sleep(.1)\")"
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            with self.assertRaisesRegex(RuntimeError, "during finalization"):
                run_logged([sys.executable, "-u", "-c", code], cwd=self.root, log_path=self.log,
                           timeout=1, finalization=(marker, 1.3))
        self.assertEqual(sink.getvalue().count("Test suite finished: allowing"), 1)

    def test_incomplete_completion_output_keeps_execution_deadline(self):
        marker = re.compile(r"^suite passed\nsummary\n", re.MULTILINE)
        code = "import time; print('suite passed'); time.sleep(10)"
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            with self.assertRaisesRegex(RuntimeError, "timed out after 1s:"):
                run_logged([sys.executable, "-u", "-c", code], cwd=self.root, log_path=self.log,
                           timeout=1, finalization=(marker, 2))
        self.assertNotIn("Test suite finished: allowing", sink.getvalue())

    def test_startup_has_its_own_deadline_then_execution_gets_its_budget(self):
        marker = re.compile(r"^case started\n", re.MULTILINE)
        # The command lasts longer than its execution budget but completes
        # inside that budget measured from the start of the case.
        run = "import time; time.sleep(.65); print('case started'); time.sleep(.65); print('done')"
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            self.assertEqual(run_logged([sys.executable, "-u", "-c", run], cwd=self.root,
                log_path=self.log, timeout=1, startup=(marker, 1.5)), "case started\ndone")
        self.assertIn("Test started: allowing up to 1s", sink.getvalue())
        hang = "import time; print('no test case yet'); time.sleep(10)"
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "after 0.5s during startup"):
                run_logged([sys.executable, "-u", "-c", hang], cwd=self.root,
                           log_path=self.log, timeout=5, startup=(marker, .5))

    def test_missing_executable_closes_group_and_records_failure(self):
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            with self.assertRaises(FileNotFoundError):
                run_logged([str(self.root / "missing")], cwd=self.root,
                           log_path=self.log, label="Missing compiler")
        self.assertIn("FAIL: Missing compiler", self.log.read_text())
        self.assertTrue(sink.getvalue().rstrip().endswith("::endgroup::"))


class SimulatorPasteboardTests(unittest.TestCase):
    def exercise(self, previous, *, body_fails=False, verify='0'):
        from simulator_environment import isolated_pasteboard, DOMAIN, KEY
        import subprocess
        calls = []
        result = subprocess.CompletedProcess([], 1 if previous is None else 0, '' if previous is None else previous, '')
        def run(args, **kwargs):
            calls.append(args)
            return verify if args[1] == 'read' else ''
        with patch('simulator_environment.subprocess.run', return_value=result) as probe:
            with isolated_pasteboard(run):
                if body_fails:
                    raise RuntimeError('fixture failed')
            probe.assert_called_once_with(['defaults', 'read', DOMAIN, KEY], capture_output=True, text=True, timeout=10)
        return calls

    def test_missing_preference_is_deleted_after_scope(self):
        from simulator_environment import DOMAIN, KEY
        calls = self.exercise(None)
        self.assertEqual(calls, [['defaults','write',DOMAIN,KEY,'-bool','false'],
                                ['defaults','read',DOMAIN,KEY], ['defaults','delete',DOMAIN,KEY]])

    def test_explicit_previous_values_are_restored(self):
        for previous in ['0', '1']:
            with self.subTest(previous=previous):
                calls = self.exercise(previous)
                self.assertEqual(calls[-1][-2:], ['-bool', 'true' if previous == '1' else 'false'])

    def test_fixture_failure_still_restores_host_preference(self):
        from simulator_environment import isolated_pasteboard, DOMAIN, KEY
        import subprocess
        calls = []
        def run(args, **kwargs):
            calls.append(args); return '0' if args[1] == 'read' else ''
        with patch('simulator_environment.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '1', '')):
            with self.assertRaisesRegex(RuntimeError, 'fixture failed'):
                with isolated_pasteboard(run):
                    raise RuntimeError('fixture failed')
        self.assertEqual(calls[-1], ['defaults','write',DOMAIN,KEY,'-bool','true'])

    def test_unknown_preference_is_rejected_before_mutation(self):
        from simulator_environment import isolated_pasteboard
        import subprocess
        calls = []
        with patch('simulator_environment.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'unknown', '')):
            with self.assertRaisesRegex(ValueError, 'Unrecognized'):
                with isolated_pasteboard(lambda *args, **kwargs: calls.append(args)):
                    self.fail('Unknown configuration must not reach simulator execution')
        self.assertEqual(calls, [])

    def test_failed_verification_restores_and_blocks_execution(self):
        from simulator_environment import isolated_pasteboard, DOMAIN, KEY
        import subprocess
        calls = []
        def run(args, **kwargs):
            calls.append(args); return '1' if args[1] == 'read' else ''
        with patch('simulator_environment.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '1', '')):
            with self.assertRaisesRegex(ValueError, 'not disabled'):
                with isolated_pasteboard(run):
                    self.fail('Unisolated environment must not run')
        self.assertEqual(calls[-1], ['defaults','write',DOMAIN,KEY,'-bool','true'])
