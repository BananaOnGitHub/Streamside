#!/usr/bin/env python3
"""Ubuntu build selection, resumable status and verified artifact retrieval. No signing."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/native_frontend')]
from workspace_paths import ARTIFACTS_DIR

CONFIG = json.loads((ROOT / 'tools/apple-builds.json').read_text())
TERMINAL = {'finished', 'failed', 'canceled', 'cancelled', 'timeout', 'skipped'}


class ServiceError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Codemagic:
    def __init__(self):
        path = Path(os.environ.get('STREAMSIDE_CODEMAGIC_TOKEN_FILE',
                    Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'streamside/codemagic-token'))
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise ServiceError('Codemagic token file must be owned by this user, regular, and mode 0600')
        self.token = path.read_text().strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{30,200}', self.token):
            raise ServiceError('Invalid Codemagic token file')

    def request(self, path, body=None, legacy=False):
        base = 'https://api.codemagic.io/' if legacy else 'https://codemagic.io/api/v3/'
        request = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                   headers={'x-auth-token': self.token, 'Content-Type': 'application/json'})
        try:
            # Never forward an authentication header through a redirect, or log response bodies.
            with urllib.request.build_opener(NoRedirect).open(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise ServiceError('Codemagic HTTP ' + str(error.code)) from None
        except (OSError, ValueError):
            raise ServiceError('Codemagic network or response failure') from None

    def history(self):
        builds, cursor = [], None
        for _ in range(10):
            suffix = '' if cursor is None else '&cursor=' + urllib.parse.quote(cursor, safe='')
            page = self.request('teams/' + CONFIG['codemagic_personal_team'] + '/builds?page_size=100' + suffix)
            builds.extend(page['data'])
            cursor = page['cursor']
            if not cursor:
                return builds
        raise ServiceError('Build history exceeds bounded pagination; balance reservation unknown')

    def build(self, identity):
        if not re.fullmatch('[a-f0-9]{24}', identity):
            raise ServiceError('Invalid Codemagic build ID')
        return self.request('builds/' + identity)['data']


def seconds(build):
    start = datetime.fromisoformat(build['started_at'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(build['finished_at'].replace('Z', '+00:00'))
    duration = (end - start).total_seconds()
    if not 0 < duration < 86400:
        raise ValueError('Invalid build duration')
    return duration


def budget(user, history, samples):
    """Quota values are seconds, verified against personal Billing UI; fail closed on changes."""
    if user['personalTeam']['_id'] != CONFIG['codemagic_personal_team']:
        raise ValueError('Personal account identity changed')
    times = user['buildTimes']
    usage = user['billing']['usage']
    limit = times['monthlyFreeBuildTimeLimit']
    used = times['currentPeriod']['free']
    if (type(limit) is not int or type(used) is not int or not 0 <= used <= limit <= 30000
        or limit != usage['freeLimit']['buildTime']
        or used != usage['currentPeriod']['buildTime']['mac_mini_m2_free']):
        raise ValueError('Quota schema or accounting disagreement')
    sample = sorted(samples[:20])
    if any(not math.isfinite(x) or x <= 0 for x in sample):
        raise ValueError('Invalid duration sample')
    # Small samples are not a percentile estimate: retain a 25 minute cold-start floor.
    p90 = sample[math.ceil(len(sample) * .9) - 1] / 60 if sample else 0
    prediction = math.ceil(p90 * 1.3 + 2)
    if len(sample) < 5:
        prediction = max(prediction, CONFIG['bootstrap_minutes'])
    # Reserve the full runner timeout for every active build, across all applications.
    active = sum(b['status'] not in TERMINAL for b in history)
    remaining = math.floor((limit - used) / 60)
    reserved = active * 120  # account builds may have the vendor's full 120 minute timeout
    required = max(prediction, CONFIG['max_minutes']) + CONFIG['reserve_minutes']
    enough = remaining - reserved >= required and prediction <= CONFIG['max_minutes']
    return dict(provider='codemagic' if enough else 'github', remaining_minutes=remaining,
                active_builds=active, reserved_minutes=reserved, sample_count=len(sample),
                predicted_minutes=prediction, required_minutes=required,
                reason='Verified free budget available' if enough else 'Insufficient conservative free budget')


def select(client):
    try:
        user = client.request('user', legacy=True)['user']
        history = client.history()
        samples = []
        for b in history:
            if (b['app_id'] == CONFIG['codemagic_app'] and b['workflow']['id'] == CONFIG['codemagic_workflow']
                and b['status'] == 'finished' and len(samples) < 20):
                detail = client.build(b['id'])
                if detail['instance_type'] == 'mac_mini_m2' and detail['config']['xcode_version'] == '26.6':
                    samples.append(seconds(detail))
        return budget(user, history, samples)
    except (ServiceError, KeyError, TypeError, ValueError):
        return dict(provider='github', reason='Codemagic quota/history unavailable or unrecognized; no build submitted')


def gh(*arguments):
    result = subprocess.run(['gh', *arguments], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise ServiceError('GitHub command failed: ' + arguments[0])
    return result.stdout


def current_source():
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ServiceError('Commit source changes before requesting a build')
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    if branch != CONFIG['branch']:
        raise ServiceError('Build dispatcher is limited to ' + CONFIG['branch'])
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    remote = json.loads(gh('api', 'repos/' + CONFIG['repository'] + '/git/ref/heads/' + branch))
    if remote['object']['sha'] != revision:
        raise ServiceError('Push this exact source commit before starting a build')
    return revision


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def github_runs(revision):
    return json.loads(gh('run', 'list', '--repo', CONFIG['repository'], '--workflow', CONFIG['github_workflow'],
        '--branch', CONFIG['branch'], '--commit', revision, '--limit', '20',
        '--json', 'databaseId,status,conclusion,url,headSha'))


def start(client, revision, ticket):
    if ticket.exists():
        return json.loads(ticket.read_text())
    # Adopt an existing run of this exact source instead of duplicating a UI/API dispatch.
    if client:
        try:
            matches = [b for b in client.history() if b['app_id'] == CONFIG['codemagic_app']
                       and b['workflow']['id'] == CONFIG['codemagic_workflow']
                       and (b.get('commit') or {}).get('hash') == revision]
            if matches:
                record = dict(provider='codemagic', source_revision=revision, build_id=matches[0]['id'], adopted=True)
                write(ticket, record)
                return record
        except ServiceError:
            pass
    matches = github_runs(revision)
    if matches:
        record = dict(provider='github', source_revision=revision, build_id=str(matches[0]['databaseId']), adopted=True)
        write(ticket, record)
        return record
    decision = select(client) if client else dict(provider='github', reason='No usable local Codemagic credential')
    record = dict(**decision, source_revision=revision, submission='pending')
    # Persist BEFORE the non-idempotent request. An uncertain response must never start another job.
    write(ticket, record)
    if decision['provider'] == 'codemagic':
        response = client.request('apps/' + CONFIG['codemagic_app'] + '/builds', dict(
            workflow_id=CONFIG['codemagic_workflow'], branch=CONFIG['branch'], instance_type='mac_mini_m2',
            labels=['ssn-' + revision], environment=dict(variables={'SSN_EXPECTED_REVISION': revision})))
        record['build_id'] = response['data']['id']
    else:
        gh('workflow', 'run', CONFIG['github_workflow'], '--repo', CONFIG['repository'], '--ref', CONFIG['branch'],
           '-f', 'expected_revision=' + revision)
    record['submission'] = 'accepted'
    write(ticket, record)
    return record


def status(client, record, ticket):
    if not record.get('build_id'):
        if record['provider'] == 'github':
            matches = github_runs(record['source_revision'])
            if matches:
                record['build_id'] = str(matches[0]['databaseId'])
        elif client:
            matches = [b for b in client.history() if 'ssn-' + record['source_revision'] in b['labels']]
            if matches:
                record['build_id'] = matches[0]['id']
        if not record.get('build_id'):
            raise ServiceError('Submission not yet identified. Check provider UI; do not resubmit or switch providers')
    if record['provider'] == 'codemagic':
        b = client.build(record['build_id'])
        if (b.get('commit') or {}).get('hash') != record['source_revision']:
            raise ServiceError('Codemagic source mismatch or checkout not yet reported')
        record.update(status=b['status'], successful=b['status'] == 'finished',
            url='https://codemagic.io/app/' + CONFIG['codemagic_app'] + '/build/' + record['build_id'])
    else:
        b = json.loads(gh('run', 'view', record['build_id'], '--repo', CONFIG['repository'],
                          '--json', 'status,conclusion,url,headSha'))
        if b['headSha'] != record['source_revision']:
            raise ServiceError('GitHub source mismatch')
        record.update(status=b['status'], successful=b['conclusion'] == 'success', url=b['url'])
    write(ticket, record)
    return record


def safe_files(archive, kind):
    """No links, devices, traversal, duplicate paths or decompression bombs."""
    entries = []
    seen, total = set(), 0
    members = archive.infolist() if kind == 'zip' else archive.getmembers()
    if len(members) > 250:
        raise ValueError('Archive has too many entries')
    for member in members:
        name = member.filename if kind == 'zip' else member.name
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or str(path) in seen:
            raise ValueError('Unsafe or duplicate artifact path')
        seen.add(str(path))
        if kind == 'zip':
            if stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Artifact link rejected')
            directory, size = member.is_dir(), member.file_size
        else:
            if not (member.isdir() or member.isfile()):
                raise ValueError('Artifact special file rejected')
            directory, size = member.isdir(), member.size
        total += size
        if total > 64 * 1024 * 1024:
            raise ValueError('Artifact exceeds size limit')
        if not directory:
            data = archive.read(member) if kind == 'zip' else archive.extractfile(member).read()
            entries.append((name, data))
    return entries


def fetch(client, record, out):
    if not record.get('successful'):
        raise ServiceError('Build has not passed; inspect failure evidence on its provider')
    download = out / 'download'
    if download.exists():
        raise ServiceError('Download already exists; preserve it or choose a fresh artifact directory')
    download.mkdir()
    if record['provider'] == 'codemagic':
        artifacts = client.build(record['build_id'])['artifacts']
        # Only artifact GETs use signed URLs. Never send the API token to storage hosts.
        entries = []
        for a in artifacts:
            if a['size_in_bytes'] > 64 * 1024 * 1024:
                raise ServiceError('Artifact download too large')
            url = a['short_lived_download_url']
            if not url.startswith('https://'):
                raise ServiceError('Artifact URL must use HTTPS')
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read(64 * 1024 * 1024 + 1)
            except OSError:
                raise ServiceError('Artifact transfer failed; obtain a fresh URL with status/fetch') from None
            if len(data) != a['size_in_bytes']:
                raise ServiceError('Artifact transfer size mismatch')
            if a['name'].endswith('.zip'):
                entries.extend(safe_files(zipfile.ZipFile(io.BytesIO(data)), 'zip'))
            else:
                entries.append((a['name'], data))
        for filename in ['streamside-components.tar.gz', 'validation.json']:
            matches = [data for name, data in entries if PurePosixPath(name).name == filename]
            if len(matches) != 1:
                raise ServiceError('Expected exactly one ' + filename)
            (download / filename).write_bytes(matches[0])
    else:
        gh('run', 'download', record['build_id'], '--repo', CONFIG['repository'],
           '--name', 'swiftui-components-' + record['source_revision'], '--dir', str(download))
    receipt = json.loads((download / 'validation.json').read_text())
    archive = (download / 'streamside-components.tar.gz').read_bytes()
    if (receipt['source_revision'] != record['source_revision'] or receipt['passed'] is not True
        or not receipt['stages'] or not all(x['passed'] is True for x in receipt['stages'])
        or receipt['archive_bytes'] != len(archive)
        or receipt['archive_sha256'] != hashlib.sha256(archive).hexdigest()):
        raise ServiceError('Validation receipt or archive hash mismatch')
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        for name, data in safe_files(tar, 'tar'):
            if not name.startswith('components/'):
                raise ServiceError('Unexpected artifact root')
            destination = download / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    from components import verify
    verify(download / 'components', record['source_revision'])
    environment = dict(os.environ, SSN_ABI_OBJECT=str(download / 'components/native/apple-abi.o'))
    for pattern in ['test_abi.py', 'test_components.py', 'test_core.py', 'test_launch.py', 'test_probes.py', 'test_launch_comparison.py', 'test_vaft_core.py']:
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/native_frontend', '-p', pattern, '-v'],
                       cwd=ROOT, env=environment, check=True)
    record.update(download_verified=True, archive_sha256=receipt['archive_sha256'],
                  components=str(download / 'components'))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'start', 'status', 'fetch'])
    args = parser.parse_args()
    try:
        try:
            client = Codemagic()
        except (OSError, ServiceError):
            client = None
        if args.command == 'plan':
            print(json.dumps(select(client) if client else dict(provider='github', reason='No usable local Codemagic credential'), indent=2))
            return
        revision = current_source()
        out = ARTIFACTS_DIR / 'ci' / revision
        out.mkdir(parents=True, exist_ok=True)
        ticket = out / 'build.json'
        with (out.parent / '.dispatch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.command == 'start':
                record = start(client, revision, ticket)
            else:
                record = status(client, json.loads(ticket.read_text()), ticket)
                if args.command == 'fetch':
                    record = fetch(client, record, out)
                    write(ticket, record)
            print(json.dumps(record, indent=2))
    except (OSError, ValueError, KeyError, TypeError, ServiceError, subprocess.CalledProcessError) as error:
        # No raw HTTP body, signed URL, request headers, environment or token in diagnostics.
        parser.exit(1, 'Build operation failed: ' + (str(error) if isinstance(error, ServiceError) else type(error).__name__) + '\n')


if __name__ == '__main__':
    main()
