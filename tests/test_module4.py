import unittest
from unittest.mock import AsyncMock, patch
from backend.agent_engine import _validate_call, _build_result
from backend.ai_agent import analyze_opportunity_with_ai

PROFILE = {'academic_year': 2, 'skills': ['Python'], 'category': 'all', 'hours_per_week': 6}

class Module4Tests(unittest.IsolatedAsyncioTestCase):
    async def test_analysis_fields(self):
        response = {k: 'Test' for k in ('summary','match_reason','skill_gaps','next_steps','student_approval_note')}
        with patch('backend.ai_agent.generate_json', new_callable=AsyncMock, return_value=response):
            result = await analyze_opportunity_with_ai(PROFILE, {'title': 'Demo'}, {}, None)
        self.assertEqual(result['summary'], 'Test')

    async def test_reject_unverified_opportunity(self):
        with self.assertRaises(ValueError):
            _validate_call('check_eligibility', {'opportunity_id': 99}, PROFILE, {1: {}}, {})

    async def test_cannot_roadmap_invented_skill(self):
        with self.assertRaises(ValueError):
            _validate_call('generate_growth_roadmap', {'missing_skills': ['Invented']}, PROFILE,
                           {1: {}}, {1: {'missing_skills': ['Python']}})

    async def test_profile_not_controlled_by_model(self):
        args = _validate_call('check_eligibility', {'opportunity_id': 1, 'student_year': 10, 'student_skills': ['fake']},
                              PROFILE, {1: {}}, {})
        self.assertEqual(args['student_year'], 2)
        self.assertEqual(args['student_skills'], ['Python'])

    async def test_no_trace_is_not_agentic(self):
       result = _build_result(PROFILE,[],{},{},[],"No actions","completed",[])
       self.assertFalse(result["agentic"])

if __name__ == '__main__':
    unittest.main()
