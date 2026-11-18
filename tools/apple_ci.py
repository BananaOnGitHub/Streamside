#!/usr/bin/env python3
"""Identical donor-free Apple compilation gates for hosted providers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/native_frontend')]
from build_progress import run_logged
from workspace_paths import ARTIFACTS_DIR


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ARTIFACTS_DIR / 'apple-ci')
    args = parser.parse_args()
    out = args.output.resolve()
    if out == ROOT or ROOT in out.parents or out.exists():
        parser.error('Use a new output directory outside the checkout')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if os.environ.get('SSN_EXPECTED_REVISION') != revision:
        parser.error('Checkout does not match the requested source revision')
    out.mkdir(parents=True)
    result = dict(schema=1, source_revision=revision, passed=False, stages=[])
    commands = [
        ('Build logging tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/native_frontend', '-p', 'test_build_progress.py', '-v']),
        ('Shared VAFT playlist engine', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/native_frontend', '-p', 'test_vaft_core.py', '-v']),
        ('SwiftUI, interoperability and simulator gates', [sys.executable, '-u', 'tools/native_frontend/components.py', 'build', '--output', str(out / 'components')]),
        ('Foundation networking integration', ['make', 'test-foundation-cache']),
        ('Report comparison tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/native_frontend', '-p', 'test_comparison.py', '-v']),
        ('Build provider routing tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_apple_builds.py', '-v'])]
    try:
        for index, (label, command) in enumerate(commands):
            started = time.monotonic()
            try:
                run_logged(command, cwd=ROOT, log_path=out / f'stage-{index}.log', timeout=3000,
                           label=label, group=True, heartbeat=True, summary=True)
            except Exception:
                result['stages'].append(dict(name=label, passed=False, seconds=round(time.monotonic()-started, 3)))
                raise
            result['stages'].append(dict(name=label, passed=True, seconds=round(time.monotonic()-started, 3)))
        archive = out / 'streamside-components.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(out / 'components', arcname='components')
        result.update(passed=True, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                      archive_bytes=archive.stat().st_size)
    finally:
        (out / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
