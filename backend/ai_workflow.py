"""Dashboard-compatible workflow with Gemini explanations and honest fallback."""
import asyncio
import logging
from backend.workflow import run_orbit_workflow
from backend.ai_agent import analyze_opportunity_with_ai, provider_name

logger = logging.getLogger(__name__)

async def run_orbit_ai_workflow(student_year, student_skills, category='all', hours_per_week=5):
    result = await run_orbit_workflow(student_year, student_skills, category, hours_per_week)
    profile = result['student_profile']
    successful = 0
    for item in result['opportunities']:
        try:
            item['ai_analysis'] = await analyze_opportunity_with_ai(
                profile, item['opportunity'], item['eligibility'], item.get('growth_roadmap'))
            successful += 1
        except Exception as exc:
            logger.warning('AI analysis failed (%s): %s', type(exc).__name__, str(exc)[:250])
            item['ai_analysis'] = {
                'summary': 'AI analysis is temporarily unavailable.',
                'match_reason': 'Refer to the eligibility results.',
                'skill_gaps': 'Refer to the missing skills.',
                'next_steps': 'Review the proposed roadmap.',
                'student_approval_note': 'Student approval is required.',
            }
    result['ai_provider'] = provider_name()
    result['ai_enabled'] = bool(successful)
    result['ai_success_count'] = successful
    return result
