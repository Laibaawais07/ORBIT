
import os
import tempfile
import unittest
from pathlib import Path

from backend import approvals


class ApprovalTests(unittest.TestCase):

    def setUp(self):
        # Create a temporary SQLite database for each test.
        fd, filename = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)

        self.test_db = Path(filename)
        self.old_db = approvals.DB_PATH

        approvals.DB_PATH = self.test_db

    def tearDown(self):
        # Restore the original database path.
        approvals.DB_PATH = self.old_db

        # Remove the temporary database file.
        # SQLite connections must be closed by backend code.
        if self.test_db.exists():
            self.test_db.unlink()

    def test_pending_approval_and_persistence(self):
        item = approvals.create_approval_request(
            1,
            {"steps": ["Study Python"]}
        )

        self.assertEqual(item["status"], "pending")

        saved = approvals.get_approval_request(
            item["request_id"]
        )

        self.assertEqual(
            saved["roadmap"]["steps"],
            ["Study Python"]
        )

        self.assertEqual(
            len(approvals.list_approval_requests()),
            1
        )

    def test_approve_once(self):
        item = approvals.create_approval_request(
            1,
            {"steps": []}
        )

        accepted = approvals.decide_approval(
            item["request_id"],
            "approved"
        )

        self.assertEqual(
            accepted["status"],
            "approved"
        )

        self.assertIsNotNone(
            accepted["decided_at"]
        )

        self.assertIn(
            "error",
            approvals.decide_approval(
                item["request_id"],
                "rejected"
            )
        )

    def test_reject(self):
        item = approvals.create_approval_request(
            2,
            {"steps": []}
        )

        result = approvals.decide_approval(
            item["request_id"],
            "rejected"
        )

        self.assertEqual(
            result["status"],
            "rejected"
        )

    def test_missing_and_invalid(self):
        self.assertIsNone(
            approvals.get_approval_request("missing")
        )

        self.assertIn(
            "error",
            approvals.decide_approval(
                "missing",
                "approved"
            )
        )

        self.assertIn(
            "error",
            approvals.decide_approval(
                "missing",
                "invalid"
            )
        )


if __name__ == "__main__":
    unittest.main()
