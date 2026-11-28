"""Runner orchestration only: every actual Apple coordinate gate stays mandatory."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/native_frontend'))
from build_progress import StartupTimeout
from controls_ui import EXPECTED, SELECTED_SUITE_FINISHED, SELECTED_SUITE_PASSED, run_controls_ui


class CoordinateGates(unittest.TestCase):
    names = ['testChatCatchUp', 'testMarkedContentConsent', 'testGlassControls', 'testPlainControls',
             'testPreviewPanelLayoutAndActions', 'testThumbnailHoldAndTap', 'testChannelProfile', 'testProfilePreviews']
    markers = {
        'testChannelProfile': ['CHANNEL_PROFILE_UI'],
        'testProfilePreviews': ['PROFILE_PREVIEWS'],
        'testChatCatchUp': ['CHAT_CATCH_UP', 'CHAT_RICH_TEXT'],
        'testMarkedContentConsent': ['MARKED_CONTENT_UI', 'MARKED_PENDING_WATCH', 'LOCAL_TEST_EDITOR'],
        'testGlassControls': ['PLAYER_MOTION_CHECKS', 'PLAYER_OPACITY_PIXELS', 'PLAYER_RESOLUTION', 'PLAYER_CLIPBOARD'],
        'testPlainControls': ['PLAYER_MOTION_CHECKS', 'PLAYER_OPACITY_PIXELS', 'PLAYER_RESOLUTION', 'PLAYER_CLIPBOARD'],
        'testPreviewPanelLayoutAndActions': ['PREVIEW_PANEL', 'PREVIEW_SWIPES', 'CONTEXT_VIDEO'],
        'testThumbnailHoldAndTap': ['THUMBNAIL_COORDINATES', 'THUMBNAIL_LIFT', 'VERIFICATION_SETTINGS'],
    }

    def exercise(self, fail=None, missing_count=False, missing_clipboard=False,
                 startup_stalls=None, expect_startup_failure=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'output').mkdir()
            folder = root / 'PlayerInput.xcodeproj'
            calls = []
            stalls = {name: list(outputs) for name, outputs in (startup_stalls or {}).items()}

            def run(args, **options):
                calls.append((args, options))
                selected = [a.rsplit('/', 1)[-1] for a in args if a.startswith('-only-testing:')]
                if selected:
                    name = selected[0]
                    if stalls.get(name):
                        raise StartupTimeout("Startup deadline exceeded", stalls[name].pop(0))
                    if name == fail:
                        raise RuntimeError('Actual coordinate gate failed')
                    count = '0 tests' if missing_count else '1 test'
                    footer = f"Test Suite 'Selected tests' passed at 2026-11-20 08:12:46.650.\n\t Executed {count}, with 0 failures (0 unexpected) in 1.000 (1.001) seconds"
                    return (f"Test Case '-[PlayerInputTests {name}]' passed\n" + footer + '\n'
                            + '\n'.join(marker + ' PASS: owned fixture' for marker in self.markers[name] if not (missing_clipboard and marker == 'PLAYER_CLIPBOARD')))
                if 'xcresulttool' in args:
                    exported = Path(args[args.index('--output-path') + 1]); exported.mkdir()
                    (exported / 'owned.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                return ''

            with patch('controls_ui.project', return_value=folder):
                if fail or missing_count or expect_startup_failure:
                    with self.assertRaises((RuntimeError, ValueError)):
                        run_controls_ui(root, root, 'owned-device', run)
                    with zipfile.ZipFile(root / 'output/player-input-failure.zip') as archive:
                        self.assertIn('owned.png', archive.namelist())
                else:
                    self.assertEqual(run_controls_ui(root, root, 'owned-device', run), EXPECTED)
            return calls

    def test_eight_independent_required_gates_with_unique_result_bundles(self):
        calls = self.exercise()
        tests = [(args, opts) for args, opts in calls if 'test-without-building' in args]
        self.assertEqual(len(tests), 8)
        selections = [next(a for a in args if a.startswith('-only-testing:')).rsplit('/', 1)[-1] for args, _ in tests]
        self.assertEqual(selections, self.names)
        bundles = [args[args.index('-resultBundlePath') + 1] for args, _ in tests]
        self.assertEqual(len(set(bundles)), 8)
        self.assertEqual([opts['timeout'] for _, opts in tests], [300, 300, 300, 300, 600, 300, 300, 300])
        self.assertTrue(all(opts['finalization'] == (SELECTED_SUITE_FINISHED, 120) for _, opts in tests))
        for name, (_, opts) in zip(self.names, tests):
            pattern, seconds = opts['startup']
            self.assertEqual(seconds, 150)
            self.assertIsNotNone(pattern.search(f"Test Case '-[PlayerInputTests.PlayerInputTests {name}]' started.\n"))
            self.assertIsNone(pattern.search("Test Case '-[PlayerInputTests.PlayerInputTests otherCase]' started.\n"))

    def test_only_successful_selected_suite_footer_starts_finalization(self):
        suite = "Test Suite 'Selected tests' passed at 2026-11-20 08:12:46.650.\n"
        summary = "\t Executed 1 test, with 0 failures (0 unexpected) in 208.647 (208.661) seconds\n"
        self.assertIsNotNone(SELECTED_SUITE_PASSED.search(suite + summary))
        for output in (suite, summary, suite + summary.replace('0 failures', '1 failure'),
                       suite + summary.replace('1 test', '0 tests'), suite.replace('passed', 'failed') + summary):
            self.assertIsNone(SELECTED_SUITE_PASSED.search(output))

    def test_completed_failed_suite_gets_finalization_but_is_not_a_pass(self):
        failure = ("Test Suite 'Selected tests' failed at 2026-11-20 11:07:25.266.\n"
                   "\t Executed 1 test, with 1 failure (0 unexpected) in 157.588 (157.603) seconds\n")
        self.assertIsNotNone(SELECTED_SUITE_FINISHED.search(failure))
        self.assertIsNone(SELECTED_SUITE_PASSED.search(failure))

    def test_failed_gate_exports_its_own_evidence_without_retry_or_later_tests(self):
        calls = self.exercise(fail='testPlainControls')
        tests = [args for args, _ in calls if 'test-without-building' in args]
        self.assertEqual(len(tests), 4)
        export = next(args for args, _ in calls if 'xcresulttool' in args)
        self.assertEqual(Path(export[export.index('--path') + 1]).name, 'testPlainControls.xcresult')

    def test_silent_startup_stall_reboots_once_and_runs_every_gate(self):
        calls = self.exercise(startup_stalls={'testMarkedContentConsent': ['Writing result bundle']})
        tests = [args for args, _ in calls if 'test-without-building' in args]
        self.assertEqual(len(tests), 9)
        recovery = [args for args, _ in calls if 'simctl' in args]
        self.assertEqual(recovery, [
            ['xcrun', 'simctl', 'shutdown', 'owned-device'],
            ['xcrun', 'simctl', 'boot', 'owned-device'],
            ['xcrun', 'simctl', 'bootstatus', 'owned-device', '-b'],
        ])
        bundles = [Path(args[args.index('-resultBundlePath') + 1]).name for args in tests]
        self.assertEqual(len(set(bundles)), 9)
        self.assertEqual(bundles[1:3], ['testMarkedContentConsent.xcresult', 'testMarkedContentConsent-startup-recovery.xcresult'])

    def test_second_startup_stall_fails_without_another_reboot(self):
        calls = self.exercise(startup_stalls={'testMarkedContentConsent': ['', '']}, expect_startup_failure=True)
        self.assertEqual(sum('test-without-building' in args for args, _ in calls), 3)
        self.assertEqual(sum('bootstatus' in args for args, _ in calls), 1)
        export = next(args for args, _ in calls if 'xcresulttool' in args)
        self.assertEqual(Path(export[export.index('--path') + 1]).name, 'testMarkedContentConsent-startup-recovery.xcresult')

    def test_any_test_execution_evidence_prevents_startup_retry(self):
        calls = self.exercise(startup_stalls={
            'testMarkedContentConsent': ["Test Suite 'Selected tests' started at 2026-11-20 08:12:46.650.\n"]
        }, expect_startup_failure=True)
        self.assertEqual(sum('test-without-building' in args for args, _ in calls), 2)
        self.assertFalse(any('simctl' in args for args, _ in calls))

    def test_pass_marker_without_actual_test_count_is_rejected(self):
        calls = self.exercise(missing_count=True)
        self.assertEqual(sum('test-without-building' in args for args, _ in calls), 1)

    def test_missing_clipboard_round_trips_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Both real Copy Link'):
            self.exercise(missing_clipboard=True)
