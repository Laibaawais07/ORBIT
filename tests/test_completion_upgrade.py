import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from backend import approvals, application_packets
from backend.security import _session, _valid_session
from backend.application_packets import create_packet, confirm_handoff
from backend.live_sources import _safe_url, check_sources

class CompletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_a, self.old_b = approvals.DB_PATH, application_packets.DB_PATH
        approvals.DB_PATH = Path(self.tmp.name) / 'a.sqlite3'
        application_packets.DB_PATH = Path(self.tmp.name) / 'b.sqlite3'
        self.old_secret = os.environ.get('ORBIT_ACCESS_TOKEN')
        os.environ['ORBIT_ACCESS_TOKEN'] = 'a' * 40

    def tearDown(self):
        approvals.DB_PATH, application_packets.DB_PATH = self.old_a, self.old_b
        if self.old_secret is None:
            os.environ.pop('ORBIT_ACCESS_TOKEN', None)
        else:
            os.environ['ORBIT_ACCESS_TOKEN'] = self.old_secret
        self.tmp.cleanup()

    async def test_approval_rejection_and_handoff(self):
        pending = approvals.create_approval_request(1, {'steps': ['Learn Python']})
        rid = pending['request_id']
        with self.assertRaises(PermissionError):
            create_packet('mlh-ghw-nov-2026', rid, 'I want to learn more through teamwork.', 'Python')
        approvals.decide_approval(rid, 'approved')
        packet = create_packet('mlh-ghw-nov-2026', rid, 'I want to learn more through teamwork.', 'Python')
        self.assertEqual(packet['status'], 'draft')
        self.assertFalse(packet['external_application_submitted'])
        result = confirm_handoff(packet['packet_id'])
        self.assertEqual(result['status'], 'ready_for_manual_submission')
        self.assertFalse(result['external_application_submitted'])
        with self.assertRaises(ValueError):
            confirm_handoff(packet['packet_id'])
        rejected = approvals.create_approval_request(2, {'steps': []})
        approvals.decide_approval(rejected['request_id'], 'rejected')
        with self.assertRaises(PermissionError):
            create_packet('mlh-ghw-nov-2026', rejected['request_id'], 'I want to learn more through teamwork.', '')
        self.assertIn('error', approvals.decide_approval(rid, 'rejected'))

    async def test_signed_session(self):
        cookie = _session()
        self.assertTrue(_valid_session(cookie))
        self.assertFalse(_valid_session(cookie + 'wrong'))

    async def test_url_allowlist(self):
        self.assertTrue(_safe_url('https://ghw.mlh.com/'))
        self.assertFalse(_safe_url('http://ghw.mlh.com/'))
        self.assertFalse(_safe_url('https://evil.example/'))
        self.assertFalse(_safe_url('https://ghw.mlh.com.evil.example/'))

    async def test_live_check_does_not_claim_open(self):
        class FakeResponse:
            status_code = 200
        with patch('backend.live_sources.httpx.AsyncClient') as client:
            client.return_value.__aenter__.return_value.get = AsyncMock(return_value=FakeResponse())
            results = await check_sources('hackathon')
        self.assertTrue(results)
        self.assertEqual(results[0]['live_status'], 'official_page_reachable')
        self.assertFalse(results[0]['registration_open_verified'])

if __name__ == '__main__':
    unittest.main()
