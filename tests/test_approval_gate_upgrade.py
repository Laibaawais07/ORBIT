import tempfile
import unittest
from pathlib import Path
from backend import approvals
from backend.verification_routes import approval_audit

class HumanApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = approvals.DB_PATH
        approvals.DB_PATH = Path(self.temp.name) / 'approvals.sqlite3'

    def tearDown(self):
        approvals.DB_PATH = self.previous
        self.temp.cleanup()

    def test_pending_approved_and_rejected_access(self):
        first = approvals.create_approval_request(1, {'steps': ['Learn ML']})
        rid = first['request_id']
        self.assertFalse(approval_audit(rid)['can_use_roadmap'])
        self.assertTrue(approval_audit(rid)['human_decision_required'])
        approvals.decide_approval(rid, 'approved')
        self.assertTrue(approval_audit(rid)['can_use_roadmap'])
        self.assertIn('error', approvals.decide_approval(rid, 'rejected'))
        second = approvals.create_approval_request(2, {'steps': []})
        approvals.decide_approval(second['request_id'], 'rejected')
        self.assertFalse(approval_audit(second['request_id'])['can_use_roadmap'])
        self.assertFalse(approval_audit(second['request_id'])['external_application_submitted'])

if __name__ == '__main__': unittest.main()
