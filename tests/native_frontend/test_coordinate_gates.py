"""Runner orchestration only: every actual Apple coordinate gate stays mandatory."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/native_frontend'))
from controls_ui import EXPECTED, run_controls_ui


class CoordinateGates(unittest.TestCase):
    names = ['testMarkedContentConsent', 'testGlassControls', 'testPlainControls',
             'testPreviewPanelLayoutAndActions', 'testThumbnailHoldAndTap']
    markers = {
        'testMarkedContentConsent': ['MARKED_CONTENT_UI', 'MARKED_PENDING_WATCH'],
        'testGlassControls': ['PLAYER_MOTION_CHECKS', 'PLAYER_OPACITY_PIXELS'],
        'testPlainControls': ['PLAYER_MOTION_CHECKS', 'PLAYER_OPACITY_PIXELS'],
        'testPreviewPanelLayoutAndActions': ['PREVIEW_PANEL', 'PREVIEW_SWIPES', 'CONTEXT_VIDEO'],
        'testThumbnailHoldAndTap': ['THUMBNAIL_COORDINATES', 'THUMBNAIL_LIFT', 'VERIFICATION_SETTINGS'],
    }

    def exercise(self, fail=None, missing_count=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'output').mkdir()
            folder = root / 'PlayerInput.xcodeproj'
            calls = []

            def run(args, **options):
                calls.append((args, options))
                selected = [a.rsplit('/', 1)[-1] for a in args if a.startswith('-only-testing:')]
                if selected:
                    name = selected[0]
                    if name == fail:
                        raise RuntimeError('Actual coordinate gate failed')
                    footer = 'Executed 0 tests, with 0 failures' if missing_count else 'Executed 1 test, with 0 failures'
                    return (f"Test Case '-[PlayerInputTests {name}]' passed\n" + footer + '\n'
                            + '\n'.join(marker + ' PASS: owned fixture' for marker in self.markers[name]))
                if 'xcresulttool' in args:
                    exported = Path(args[args.index('--output-path') + 1]); exported.mkdir()
                    (exported / 'owned.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                return ''

            with patch('controls_ui.project', return_value=folder):
                if fail or missing_count:
                    with self.assertRaises((RuntimeError, ValueError)):
                        run_controls_ui(root, root, 'owned-device', run)
                    with zipfile.ZipFile(root / 'output/player-input-failure.zip') as archive:
                        self.assertIn('owned.png', archive.namelist())
                else:
                    self.assertEqual(run_controls_ui(root, root, 'owned-device', run), EXPECTED)
            return calls

    def test_five_independent_required_gates_with_unique_result_bundles(self):
        calls = self.exercise()
        tests = [(args, opts) for args, opts in calls if 'test-without-building' in args]
        self.assertEqual(len(tests), 5)
        selections = [next(a for a in args if a.startswith('-only-testing:')).rsplit('/', 1)[-1] for args, _ in tests]
        self.assertEqual(selections, self.names)
        bundles = [args[args.index('-resultBundlePath') + 1] for args, _ in tests]
        self.assertEqual(len(set(bundles)), 5)
        self.assertTrue(all(opts['timeout'] <= 600 for _, opts in tests))

    def test_failed_gate_exports_its_own_evidence_without_retry_or_later_tests(self):
        calls = self.exercise(fail='testPlainControls')
        tests = [args for args, _ in calls if 'test-without-building' in args]
        self.assertEqual(len(tests), 3)
        export = next(args for args, _ in calls if 'xcresulttool' in args)
        self.assertEqual(Path(export[export.index('--path') + 1]).name, 'testPlainControls.xcresult')

    def test_pass_marker_without_actual_test_count_is_rejected(self):
        calls = self.exercise(missing_count=True)
        self.assertEqual(sum('test-without-building' in args for args, _ in calls), 1)
