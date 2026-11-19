"""Scoped Simulator settings for local-only clipboard interaction fixtures."""
from contextlib import contextmanager
import subprocess

DOMAIN = 'com.apple.iphonesimulator'
KEY = 'PasteboardAutomaticSync'


@contextmanager
def isolated_pasteboard(run):
    # Preserve only this public Simulator toggle, not the host's clipboard or
    # other preferences. Missing means Simulator's default, restored by delete.
    previous = subprocess.run(['defaults', 'read', DOMAIN, KEY], capture_output=True,
                              text=True, timeout=10)
    if previous.returncode not in (0, 1):
        raise ValueError('Cannot inspect Simulator pasteboard synchronization')
    value = previous.stdout.strip() if previous.returncode == 0 else None
    if value not in (None, '0', '1'):
        raise ValueError('Unrecognized Simulator pasteboard synchronization value')
    try:
        run(['defaults', 'write', DOMAIN, KEY, '-bool', 'false'],
            label='Disable host pasteboard sync for simulator clipboard tests')
        if run(['defaults', 'read', DOMAIN, KEY], label='Verify simulator pasteboard isolation') != '0':
            raise ValueError('Simulator host pasteboard synchronization was not disabled')
        yield
    finally:
        if value is None:
            run(['defaults', 'delete', DOMAIN, KEY], label='Restore default simulator pasteboard synchronization')
        else:
            run(['defaults', 'write', DOMAIN, KEY, '-bool', 'true' if value == '1' else 'false'],
                label='Restore previous simulator pasteboard synchronization')
