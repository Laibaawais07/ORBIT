import unittest
from pathlib import Path

class DashboardSmokeTests(unittest.TestCase):
    def test_frontend_exists(self):
        path = Path(__file__).resolve().parents[1] / 'frontend' / 'index.html'
        self.assertTrue(path.exists())
        html = path.read_text(encoding='utf-8')
        self.assertIn('/api/analyze', html)
        self.assertIn('/api/approvals', html)
        self.assertIn('DEMO LISTING', html)

if __name__ == '__main__':
    unittest.main()
