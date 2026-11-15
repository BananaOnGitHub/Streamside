"""Synthetic quota, source and artifact safety checks; no accounts or network calls."""
import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import apple_builds as builds


class Routing(unittest.TestCase):
    def setUp(self):
        self.user = dict(personalTeam={'_id': builds.CONFIG['codemagic_personal_team']},
            buildTimes=dict(monthlyFreeBuildTimeLimit=30000, currentPeriod={'free': 660}),
            billing={'usage': dict(freeLimit={'buildTime': 30000},
                                  currentPeriod={'buildTime': {'mac_mini_m2_free': 660}})})

    def test_small_sample_keeps_cold_start_floor_and_full_timeout_reserve(self):
        result = builds.budget(self.user, [], [660])
        self.assertEqual(result['provider'], 'codemagic')
        self.assertEqual(result['remaining_minutes'], 489)
        self.assertEqual(result['predicted_minutes'], 25)
        self.assertEqual(result['required_minutes'], 50)

    def test_insufficient_budget_and_exact_threshold(self):
        for remaining, provider in [(49, 'github'), (50, 'codemagic'), (0, 'github')]:
            self.user['buildTimes']['currentPeriod']['free'] = 30000 - remaining * 60
            self.user['billing']['usage']['currentPeriod']['buildTime']['mac_mini_m2_free'] = 30000 - remaining * 60
            self.assertEqual(builds.budget(self.user, [], [])['provider'], provider)

    def test_account_wide_active_reservation(self):
        result = builds.budget(self.user, [{'status': 'building'}] * 4, [])
        self.assertEqual(result['reserved_minutes'], 480)
        self.assertEqual(result['provider'], 'github')

    def test_quota_disagreement_or_other_personal_account_rejected(self):
        for mutate in [lambda u: u['personalTeam'].update(_id='other'),
                       lambda u: u['buildTimes']['currentPeriod'].update(free=-1),
                       lambda u: u['buildTimes'].update(monthlyFreeBuildTimeLimit=500)]:
            user = copy.deepcopy(self.user)
            mutate(user)
            with self.assertRaises(ValueError):
                builds.budget(user, [], [])

    def test_percentile_uses_upper_sample_and_headroom(self):
        result = builds.budget(self.user, [], [600] * 18 + [1200, 1800])
        self.assertEqual(result['predicted_minutes'], 15)
        self.assertEqual(builds.budget(self.user, [], [3000]*5)['provider'], 'github')

    def test_unknown_account_response_falls_back_without_submission(self):
        class Client:
            def request(self, *args, **kwargs):
                return {'unrecognized': True}
        result = builds.select(Client())
        self.assertEqual(result['provider'], 'github')
        self.assertIn('unavailable', result['reason'])

    def test_pending_submission_prevents_double_start(self):
        with tempfile.TemporaryDirectory() as d:
            ticket = Path(d)/'build.json'
            builds.write(ticket, dict(provider='codemagic', submission='pending'))
            with patch.object(builds, 'github_runs', side_effect=AssertionError('Duplicate request')):
                self.assertEqual(builds.start(None, 'a'*40, ticket)['submission'], 'pending')

    def test_uncertain_post_preserves_pending_ticket_and_does_not_fallback(self):
        class Client:
            def history(self): return []
            def request(self, *args, **kwargs): raise builds.ServiceError('Network failure')
        with tempfile.TemporaryDirectory() as d:
            ticket = Path(d)/'build.json'
            with patch.object(builds, 'github_runs', return_value=[]), patch.object(builds, 'select', return_value={'provider':'codemagic'}):
                with self.assertRaises(builds.ServiceError): builds.start(Client(), 'a'*40, ticket)
            self.assertEqual(json.loads(ticket.read_text())['submission'], 'pending')

    def test_authenticated_requests_cannot_redirect(self):
        self.assertIsNone(builds.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.test'))

    def test_tar_traversal_and_links_rejected(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('components/link', tarfile.SYMTYPE)]:
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode='w') as tar:
                member = tarfile.TarInfo(name); member.type = kind
                tar.addfile(member)
            data.seek(0)
            with tarfile.open(fileobj=data) as tar, self.assertRaises(ValueError): builds.safe_files(tar, 'tar')

    def test_zip_duplicate_paths_rejected(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('a', b'1')
            z.writestr('../a', b'2')
        data.seek(0)
        with zipfile.ZipFile(data) as z, self.assertRaises(ValueError): builds.safe_files(z, 'zip')

    def test_source_mismatch_rejected_before_status_updates(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(builds, 'gh', return_value=json.dumps(dict(headSha='b'*40))):
                with self.assertRaises(builds.ServiceError):
                    builds.status(None, dict(provider='github', build_id='1', source_revision='a'*40), Path(d)/'ticket')


if __name__ == '__main__': unittest.main()
