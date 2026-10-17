import unittest
from datetime import date
from backend.real_opportunities import discover_real_opportunities
from backend.agent_engine import _validate_call, _build_result

class RealOpportunityTests(unittest.TestCase):
    def test_real_links_and_no_false_open_claim(self):
        entries = discover_real_opportunities('all', date(2026, 10, 17))
        self.assertGreaterEqual(len(entries), 3)
        for item in entries:
            self.assertTrue(item['url'].startswith('https://'))
            self.assertEqual(item['verified'], 'official_source_exists')
            self.assertFalse(item['live_checked'])
            self.assertNotEqual(item['availability'], 'open')

    def test_filter_and_expired(self):
        entries = discover_real_opportunities('hackathons', date(2027, 1, 1))
        self.assertTrue(entries)
        self.assertTrue(all(x['category'] == 'hackathon' for x in entries))
        self.assertTrue(all(x['availability'] == 'event_ended' for x in entries))

    def test_real_discovery_tool_is_safely_scoped(self):
        profile = {'category': 'internship', 'academic_year': 2, 'skills': ['Python'], 'hours_per_week': 5}
        self.assertEqual(_validate_call('discover_real_opportunities', {'category': 'hackathon'}, profile, {}, {}), {'category': 'internship'})

    def test_tool_trace_proves_execution_not_just_flag(self):
        profile = {'category': 'all'}
        empty = _build_result(profile, [], {}, {}, [], '', 'completed', [])
        self.assertFalse(empty['agentic'])
        self.assertEqual(empty['tool_verification']['executed_count'], 0)
        trace = [{'agent': 'Real Source Discovery', 'tool': 'discover_real_opportunities', 'arguments': {'category': 'all'}, 'result': []}]
        filled = _build_result(profile, trace, {}, {}, [], '', 'completed', [])
        self.assertTrue(filled['agentic'])
        self.assertTrue(filled['tool_verification']['has_real_source_discovery'])

if __name__ == '__main__': unittest.main()
