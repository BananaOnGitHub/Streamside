#!/usr/bin/env python3
"""Offline checks for explicit documentation links and current build identities.

This is a deliberately bounded Markdown reader, not a prose or release reviewer.
No network access, generated files, archive exemptions, or third-party packages.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import plistlib
import re
import subprocess
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    reason: str

    def annotation(self) -> str:
        def escape(value: str, prop: bool = False) -> str:
            value = value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            return value.replace(',', '%2C').replace(':', '%3A') if prop else value
        return f'::error file={escape(self.path, True)},line={self.line}::{escape(self.reason)}'


@dataclass
class Document:
    path: str
    anchors: set[str] = field(default_factory=set)
    links: list[tuple[int, str]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


def blank(text: str) -> str:
    return ''.join('\n' if c == '\n' else ' ' for c in text)


def visible_blocks(text: str) -> str:
    """Hide comments and code blocks while preserving line/character positions."""
    text = re.sub(r'<!--.*?(?:-->|\Z)', lambda m: blank(m[0]), text, flags=re.S)
    result = []
    fence = None
    in_list = False
    for line in text.splitlines(keepends=True):
        content = re.sub(r'^(?: {0,3}> ?)+', '', line)
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', content.rstrip('\n'))
        if fence:
            result.append(blank(line))
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
        elif marker:
            fence = (marker[1][0], len(marker[1]))
            result.append(blank(line))
        else:
            if re.match(r'^ {0,3}(?:[-+*]|\d+[.)])\s', content):
                in_list = True
            elif content.strip() and not content[0].isspace():
                in_list = False
            result.append(blank(line) if not in_list and re.match(r'^(?: {4}|\t)', content) else line)
    return ''.join(result)


def hide_inline_code(text: str) -> str:
    return re.sub(r'(?<!\\)(`+)(?!`)(.*?)(?<!`)\1(?!`)',
                  lambda m: blank(m[0]), text, flags=re.S)


def heading_slug(text: str) -> str:
    # Keep visible Markdown label text, inline code, and entity text.
    literals = []
    def protect(value: str) -> str:
        literals.append(value)
        return f'\x00{len(literals) - 1}\x00'
    text = re.sub(r'(`+)(.*?)\1', lambda m: protect(m[2]), text)
    text = re.sub(r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])', lambda m: protect(m[1]), text)
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\[[^\]]*\]', r'\1', text)
    text = re.sub(r'(?<!\w)_{1,3}(.+?)_{1,3}(?!\w)', r'\1', text)
    text = text.replace('*', '').replace('~', '')
    text = re.sub(r'\x00(\d+)\x00', lambda m: literals[int(m[1])], text)
    text = unescape(text)
    # GitHub uses simple character downcasing, without final-sigma context.
    text = ''.join(c.lower()[0] for c in text)
    return ''.join(c for c in text if c in '_-' or not (
        unicodedata.category(c).startswith(('P', 'S', 'C')) or c.isspace() and c != ' '
    )).replace(' ', '-')


class HTMLReferences(HTMLParser):
    def __init__(self, document: Document):
        super().__init__(convert_charrefs=True)
        self.document = document

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value is not None and (key == 'id' or tag == 'a' and key == 'name'):
                self.document.anchors.add(value)
            if value is not None and (key == 'href' or key == 'src'):
                self.document.links.append((self.getpos()[0], value))

    handle_startendtag = handle_starttag


def closing(text: str, start: int, left: str, right: str) -> int | None:
    """Find a balanced Markdown label/destination, respecting escapes and titles."""
    depth, quote, i = 1, None, start + 1
    while i < len(text):
        c = text[i]
        if c == '\\':
            i += 2
            continue
        if quote:
            if c == quote:
                quote = None
        elif left == '(' and c in '\"\'' and text[i - 1].isspace():
            quote = c
        elif c == left:
            depth += 1
        elif c == right:
            depth -= 1
            if not depth:
                return i
        i += 1
    return None


def destination(value: str) -> str:
    value = value.strip()
    if value.startswith('<'):
        end = value.find('>')
        if end < 0:
            raise ValueError('unclosed angle-bracket destination')
        target, tail = value[1:end], value[end + 1:].strip()
    else:
        match = re.match(r'(?:\\.|[^\s])*', value)
        target, tail = match[0], value[match.end():].strip()
    if tail and not re.fullmatch(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\([^()]*\)', tail, re.S):
        raise ValueError('invalid link destination/title; encode spaces or use <...>')
    return unescape(re.sub(r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])', r'\1', target))


def label_key(label: str) -> str:
    return ' '.join(label.split()).casefold()


def parse_document(path: str, text: str) -> Document:
    document = Document(path)
    prose = visible_blocks(text)
    used = set()
    lines = prose.splitlines()
    for i, line in enumerate(lines):
        content = re.sub(r'^(?: {0,3}> ?)+', '', line)
        atx = re.match(r'^ {0,3}#{1,6}(?:\s+(.*?)|\s*)$', content)
        heading = None
        if atx:
            heading = re.sub(r'\s+#+\s*$', '', atx[1] or '').strip()
        elif i + 1 < len(lines) and content.strip() and re.fullmatch(r' {0,3}(?:=+|-+)\s*', lines[i + 1]):
            heading = content.strip()
        if heading is not None:
            base = slug = heading_slug(heading)
            number = 0
            while slug in used:
                number += 1
                slug = f'{base}-{number}'
            used.add(slug)
            document.anchors.add(slug)
    prose = hide_inline_code(prose)
    HTMLReferences(document).feed(prose)
    definitions = {}
    definition_links = {}
    # Definitions may precede or follow their uses. Their destinations are also
    # checked when unused; locations of used references point to the use site.
    for match in re.finditer(r'^ {0,3}\[([^\]\n]+)\]:[^\S\n]*(.*)$', prose, re.M):
        line = prose.count('\n', 0, match.start()) + 1
        key = label_key(match[1])
        if key.startswith('^'):  # GFM footnotes are not repository links.
            continue
        try:
            target = destination(match[2])
            definitions.setdefault(key, target)
            definition_links.setdefault(key, (line, target))
        except ValueError as exc:
            document.issues.append(Issue(path, line, str(exc)))
        prose = prose[:match.start()] + blank(match[0]) + prose[match.end():]
    used_definitions = set()
    i = 0
    while i < len(prose):
        if prose[i] == '\\':
            i += 2
            continue
        if prose[i] != '[':
            i += 1
            continue
        end = closing(prose, i, '[', ']')
        if end is None:
            i += 1
            continue
        label = prose[i + 1:end]
        line = prose.count('\n', 0, i) + 1
        # A linked image has an independent asset destination inside its label.
        if '![' in label:
            inner = parse_document(path, label)
            document.links.extend((line + n - 1, target) for n, target in inner.links)
            document.issues.extend(Issue(path, line + issue.line - 1, issue.reason) for issue in inner.issues)
        next_pos = end + 1
        if next_pos < len(prose) and prose[next_pos] == '(':
            finish = closing(prose, next_pos, '(', ')')
            if finish is None:
                document.issues.append(Issue(path, line, 'unclosed inline link destination'))
                i = end + 1
                continue
            try:
                document.links.append((line, destination(prose[next_pos + 1:finish])))
            except ValueError as exc:
                document.issues.append(Issue(path, line, str(exc)))
            i = finish + 1
            continue
        if next_pos < len(prose) and prose[next_pos] == '[':
            finish = closing(prose, next_pos, '[', ']')
            if finish is None:
                document.issues.append(Issue(path, line, 'unclosed reference label'))
                i = end + 1
                continue
            key = label_key(prose[next_pos + 1:finish] or label)
            if key not in definitions:
                document.issues.append(Issue(path, line, f'undefined link reference [{key}]'))
            else:
                document.links.append((line, definitions[key]))
                used_definitions.add(key)
            i = finish + 1
            continue
        key = label_key(label)
        if key in definitions:
            document.links.append((line, definitions[key]))
            used_definitions.add(key)
        i = end + 1
    document.links.extend(link for key, link in definition_links.items() if key not in used_definitions)
    return document


def markdown_files(root: Path) -> list[Path]:
    """Use tracked files plus untracked, nonignored files for local previews."""
    result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            capture_output=True, check=True)
    return sorted({root / name for name in result.stdout.decode('utf-8').split('\0')
                   if name and Path(name).suffix.lower() == '.md'})


def check_links(root: Path, paths: list[Path]) -> tuple[list[Issue], int]:
    root = root.resolve()
    documents = {}
    issues = []
    for path in paths:
        name = path.relative_to(root).as_posix()
        try:
            documents[name] = parse_document(name, path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError) as exc:
            issues.append(Issue(name, 1, f'cannot read Markdown: {exc}'))
    count = 0
    for name, document in documents.items():
        issues.extend(document.issues)
        for line, target in document.links:
            count += 1
            try:
                if re.search(r'%(?![0-9a-fA-F]{2})', target):
                    raise ValueError('malformed percent escape')
                if any(ord(c) < 32 for c in target):
                    raise ValueError('control character in destination')
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    continue  # All absolute URI schemes and protocol-relative URLs are offline exclusions.
                decoded = unquote(url.path, encoding='utf-8', errors='strict')
                if '\\' in decoded:
                    raise ValueError('use / rather than backslashes in repository paths')
                base = root if decoded.startswith('/') else (root / name).parent
                resolved = (base / decoded.lstrip('/')).resolve() if decoded else root / name
                if not resolved.is_relative_to(root):
                    raise ValueError('repository link escapes the checkout')
                if not resolved.exists():
                    raise ValueError(f'missing repository target: {resolved.relative_to(root)}')
                if url.fragment and resolved.suffix.lower() == '.md':
                    fragment = unquote(url.fragment, encoding='utf-8', errors='strict')
                    linked_name = resolved.relative_to(root).as_posix()
                    linked = documents.get(linked_name)
                    if linked is None:
                        linked = parse_document(linked_name, resolved.read_text(encoding='utf-8'))
                    anchors = linked.anchors
                    if fragment not in anchors and not (fragment.startswith('user-content-') and fragment[13:] in anchors):
                        raise ValueError(f'missing heading/HTML anchor #{fragment} in {linked_name}')
                # Fragments on non-Markdown assets/source files are renderer-specific.
            except (ValueError, OSError, UnicodeError) as exc:
                issues.append(Issue(name, line, f'{target!r}: {exc}'))
    return sorted(issues, key=lambda issue: (issue.path, issue.line, issue.reason)), count


def check_versions(root: Path) -> list[Issue]:
    path = 'native/framework-info.plist'
    try:
        info = plistlib.loads((root / path).read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException) as exc:
        return [Issue(path, 1, f'cannot read native framework metadata: {exc}')]
    if not isinstance(info, dict):
        return [Issue(path, 1, 'expected native framework metadata dictionary')]
    issues = []
    expected = {
        'CFBundleExecutable': 'StreamsideNativeProof',
        'CFBundleName': 'StreamsideNativeProof',
        'CFBundleIdentifier': 'dev.streamside.nativeproof',
        'CFBundlePackageType': 'FMWK',
        'SSNFrontend': 'swiftui',
    }
    for key, value in expected.items():
        if info.get(key) != value:
            issues.append(Issue(path, 1, f'{key} must be {value!r}'))
    for key, pattern in {
        'CFBundleShortVersionString': r'[0-9]+\.[0-9]+(?:\.[0-9]+)?',
        'CFBundleVersion': r'[1-9][0-9]*',
        'MinimumOSVersion': r'[0-9]+\.[0-9]+',
    }.items():
        value = info.get(key)
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            issues.append(Issue(path, 1, f'invalid {key}'))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--github-actions', action='store_true', help='emit file/line error annotations')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        paths = markdown_files(root)
        issues, count = check_links(root, paths)
        issues.extend(check_versions(root))
    except (OSError, UnicodeError, subprocess.CalledProcessError) as exc:
        print(f'documentation check could not run: {exc}')
        return 1
    for issue in issues:
        print(issue.annotation() if args.github_actions else f'{issue.path}:{issue.line}: {issue.reason}')
    print(f'Checked {len(paths)} Markdown files, {count} explicit references, and native framework metadata: {len(issues)} error(s).')
    return bool(issues)


if __name__ == '__main__':
    raise SystemExit(main())
