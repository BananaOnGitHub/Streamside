"""Mechanical documentation contracts, independent of build/donor platforms."""
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest

from tools.check_docs import (Issue, check_links, check_versions, heading_slug,
                              markdown_files, parse_document)

ROOT = Path(__file__).resolve().parents[1]


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, text=''):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def check(self, text, files=None, name='docs/nested/README.md'):
        for path, content in (files or {}).items():
            self.write(path, content)
        origin = self.write(name, text)
        return check_links(self.root, [origin])[0]

    def test_nested_relative_paths_and_directory(self):
        self.assertEqual(self.check('[guide](../Guide.md) [source](../../src/a.c) [dir](../../src/)',
                                    {'docs/Guide.md': '# Guide', 'src/a.c': 'int a;'}), [])

    def test_same_document_and_cross_document_headings(self):
        self.assertEqual(self.check('# Setup\n[here](#setup) [there](../Guide.md#usage)',
                                    {'docs/Guide.md': 'Usage\n=====\n'}), [])

    def test_github_slug_formatting_punctuation_unicode(self):
        self.assertEqual(heading_slug("This'll be a _Helpful_ Section About Θ!"),
                         'thisll-be-a-helpful-section-about-θ')
        self.assertEqual(heading_slug('**One**  `snake_case` &amp; [Two](url) 😄'),
                         'one--snake_case--two-')
        self.assertEqual(heading_slug('A\tB snake_case \\_literal\\_'), 'ab-snake_case-_literal_')
        self.assertEqual(heading_slug('ΗΣ İ'), 'ησ-i')
        self.assertEqual(heading_slug('Use `<T>` and <em>types</em>'), 'use-t-and-types')
        self.assertEqual(heading_slug('Use `[x](foo)`'), 'use-xfoo')

    def test_collisions_include_preexisting_numbered_heading(self):
        doc = '# A\n# A\n# A-1\n# A\n[x](#a-1-1) [y](#a-2)'
        self.assertEqual(parse_document('a.md', doc).anchors, {'a', 'a-1', 'a-1-1', 'a-2'})
        self.assertEqual(self.check(doc), [])

    def test_encoded_path_and_utf8_fragment(self):
        self.assertEqual(self.check('[a](../Space%20Name.md#caf%C3%A9) [b](../Space%20Name.md#foo%2Dbar)',
                                    {'docs/Space Name.md': '# Café\n# Foo Bar'}), [])

    def test_encoded_delimiters_and_angle_destination_with_title(self):
        self.assertEqual(self.check('[a](<../hash# name.md>)'), [
            Issue('docs/nested/README.md', 1, "'../hash# name.md': missing repository target: docs/hash")])
        self.assertEqual(self.check('[a](<../hash%23 name.md> "A title")',
                                    {'docs/hash# name.md': ''}), [])

    def test_parentheses_and_escaped_parentheses(self):
        self.assertEqual(self.check('[a](../a(b).md) [b](../a\\(b\\).md)', {'docs/a(b).md': ''}), [])

    def test_markdown_and_html_images(self):
        self.assertEqual(self.check('![alt](../assets/icon.png)\n<img src="../assets/icon.png">',
                                    {'docs/assets/icon.png': 'bytes'}), [])
        issues = self.check('![alt](missing.png)\n<img src="missing.svg">')
        self.assertEqual([i.line for i in issues], [1, 2])

    def test_linked_image_checks_both_destinations(self):
        issues = self.check('[![logo](absent.png)](../Guide.md)', {'docs/Guide.md': ''})
        self.assertEqual(len(issues), 1)
        self.assertIn('absent.png', issues[0].reason)

    def test_source_test_script_asset_references(self):
        text = '[source](../../src/a.c#L1) [test](../../tests/a.py) [tool](../../tools/a.py) [asset](../../LICENSE)'
        self.assertEqual(self.check(text, {p: '' for p in ['src/a.c', 'tests/a.py', 'tools/a.py', 'LICENSE']}), [])

    def test_missing_target_and_anchor_report_origin_line(self):
        issues = self.check('# Present\n[x](absent.md)\n[y](#missing)')
        self.assertEqual([i.line for i in issues], [2, 3])
        self.assertTrue(all(i.path == 'docs/nested/README.md' for i in issues))
        self.assertIn('missing heading', issues[1].reason)

    def test_reference_full_collapsed_shortcut_and_unused(self):
        text = '[one][ Target ] [two][] [three]\n\n[target]: ../Guide.md "title"\n[two]: #usage\n[three]: ../Guide.md\n[unused]: ../Guide.md\n# Usage'
        self.assertEqual(self.check(text, {'docs/Guide.md': ''}), [])

    def test_reference_failure_points_to_use_site(self):
        issues = self.check('plain\n[a][target]\n\n[target]: absent.md')
        self.assertEqual(issues[0].line, 2)
        self.assertIn('absent.md', issues[0].reason)

    def test_undefined_reference(self):
        issues = self.check('[a][missing]\n[b][]\n[plain prose]')
        self.assertEqual(len(issues), 2)
        self.assertIn('undefined link reference', issues[0].reason)

    def test_malformed_destinations(self):
        for value in ['[a](unclosed', '[a](space name.md)', '[a](bad%GG.md)',
                      '[a](bad%FF.md)', '[a](<unclosed)', '[a][unclosed']:
            with self.subTest(value=value):
                self.assertTrue(self.check(value))

    def test_code_comments_escaped_links_and_footnotes_are_not_paths(self):
        text = '''`[a](missing)`
```markdown
[a](missing)
# Hidden
```
~~~
[b](missing)
~~~

    [c](missing)

<!-- [d](missing) -->
\\[e](missing)
`old/source.c` and historical-filename.md are prose.
[^note]
[^note]: old-file.md
'''
        self.assertEqual(self.check(text), [])
        self.assertNotIn('hidden', parse_document('a.md', text).anchors)

    def test_nested_list_links_are_checked(self):
        issues = self.check('- item\n    - [broken](missing.md)')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].line, 2)

    def test_all_absolute_schemes_and_protocol_relative_links_are_offline(self):
        text = ' '.join(f'[x]({url})' for url in ['https://invalid.example/a#old', 'http://invalid.example',
                        'mailto:maintainer@example.test', 'tel:+123', 'data:image/png;base64,abc',
                        'vscode://file/a', '//invalid.example/old.md'])
        self.assertEqual(self.check(text), [])

    def test_historical_links_use_immutable_external_scope_but_archive_is_checked(self):
        text = '`src/Removed.c`\n[old](https://github.com/o/r/blob/' + 'a' * 40 + '/src/Removed.c)'
        self.assertEqual(self.check(text, name='docs/archive/old.md'), [])
        issues = self.check(text + '\n[current](../../src/Removed.c)', name='docs/archive/old.md')
        self.assertEqual(len(issues), 1)

    def test_root_paths_queries_empty_destinations_and_explicit_html_anchors(self):
        self.assertEqual(self.check('<a id="Exact"></a>\n<a name="old"></a>\n'
                                   '[a](#Exact) [b](#user-content-old) [c]() [d](/README.md?raw=true)',
                                    {'README.md': ''}), [])

    def test_symlink_and_parent_escape_are_refused(self):
        issues = self.check('[a](../../../outside.md)')
        self.assertIn('escapes the checkout', issues[0].reason)
        (self.root / 'link').symlink_to(self.root.parent)
        issues = self.check('[a](../../link/outside.md)')
        self.assertIn('escapes the checkout', issues[0].reason)

    def test_annotation_escapes_workflow_command_characters(self):
        line = Issue('a,b:c.md', 3, 'bad%\r\n::warning::').annotation()
        self.assertEqual(line, '::error file=a%2Cb%3Ac.md,line=3::bad%25%0D%0A::warning::')


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'packaging').mkdir()
        (self.root / 'src').mkdir()
        self.metadata()

    def metadata(self, version='3.0.0', short='3.0.0', bundle='3.0.0.92', report='3.0.0-build.92'):
        (self.root / 'VERSION').write_text(version + '\n')
        (self.root / 'packaging/StreamsideFramework-Info.plist').write_bytes(plistlib.dumps({
            'CFBundleShortVersionString': short, 'CFBundleVersion': bundle, 'MinimumOSVersion': '15.0'}))
        (self.root / 'src/TASDiagnostics.c').write_text(f'// header\n#define TAS_REPORT_VERSION "{report}"\n')

    def test_current_metadata_agrees(self):
        self.assertEqual(check_versions(self.root), [])

    def test_distinct_build_number_is_not_public_version(self):
        self.metadata(bundle='3.0.0.100', report='3.0.0-build.100')
        self.assertEqual(check_versions(self.root), [])

    def test_short_bundle_and_report_drift_are_errors(self):
        for overrides, origin in [({'short': '2.3.0'}, 'packaging/StreamsideFramework-Info.plist'),
                                  ({'bundle': '2.3.0.92'}, 'packaging/StreamsideFramework-Info.plist'),
                                  ({'report': '3.0.0-build.91'}, 'src/TASDiagnostics.c')]:
            with self.subTest(overrides=overrides):
                self.metadata(**overrides)
                self.assertIn(origin, [i.path for i in check_versions(self.root)])

    def test_historical_donor_release_and_artifact_labels_do_not_participate(self):
        (self.root / 'README.md').write_text('Published 2.3.0; upcoming 3.1.0; Twitch 31.5; iOS 16.4')
        (self.root / 'old.plist').write_bytes(plistlib.dumps({'CFBundleShortVersionString': '1.0.0'}))
        self.assertEqual(check_versions(self.root), [])

    def test_missing_invalid_and_nonstring_metadata_fail_cleanly(self):
        self.metadata(bundle='3.0.0.0', report='3.0.0-build.0')
        self.assertTrue(check_versions(self.root))
        self.metadata(bundle=92)
        self.assertTrue(check_versions(self.root))
        (self.root / 'packaging/StreamsideFramework-Info.plist').write_text('invalid')
        self.assertTrue(check_versions(self.root))
        (self.root / 'VERSION').unlink()
        self.assertTrue(check_versions(self.root))
        (self.root / 'src/TASDiagnostics.c').write_text('// absent')
        self.assertTrue(check_versions(self.root))


class RepositoryTests(unittest.TestCase):
    def test_git_inventory_excludes_ignored_build_outputs_but_includes_archive_and_new_docs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.gitignore').write_text('/build/\n')
            (root / 'build').mkdir()
            (root / 'build/generated.md').touch()
            (root / 'docs/archive').mkdir(parents=True)
            (root / 'docs/archive/old.md').touch()
            (root / 'new.md').touch()
            self.assertEqual([p.relative_to(root).as_posix() for p in markdown_files(root)],
                             ['docs/archive/old.md', 'new.md'])

    def test_cli_returns_failure_and_actionable_annotations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'README.md').write_text('# Title\n[broken](missing.md)')
            result = subprocess.run([sys.executable, str(ROOT / 'tools/check_docs.py'),
                                     '--root', str(root), '--github-actions'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('::error file=README.md,line=2::', result.stdout)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
