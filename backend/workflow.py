"""MCP-powered analysis; each proposed roadmap becomes a pending approval."""
import asyncio
from fastmcp import Client
from backend.mcp_server import mcp
from backend.approvals import create_approval_request
from backend.ai_agent import analyze_opportunity_with_ai


async def run_orbit_workflow(student_year: int, student_skills: list[str], category: str = 'all', hours_per_week: int = 5):
    async with Client(mcp) as client:
        search_result = await client.call_tool('search_opportunities', {'category': category})
        opportunities = search_result.data
        results = []
        for opportunity in opportunities:
            eligibility_result = await client.call_tool('check_eligibility', {
                'opportunity_id': opportunity['id'],
                'student_year': student_year,
                'student_skills': student_skills,
            })
            eligibility = eligibility_result.data
            roadmap = None
            approval = None
            if eligibility.get('academic_eligibility') == 'eligible' and eligibility.get('missing_skills'):
                roadmap_result = await client.call_tool('generate_growth_roadmap', {
                    'missing_skills': eligibility['missing_skills'],
                    'hours_per_week': hours_per_week,
                })
                roadmap = roadmap_result.data
                approval = create_approval_request(opportunity['id'], roadmap)
            results.append({
                'opportunity': opportunity,
                'eligibility': eligibility,
                'growth_roadmap': roadmap,
                'approval': approval,
            })
    return {
        'student_profile': {'academic_year': student_year, 'skills': student_skills, 'hours_per_week': hours_per_week},
        'opportunities': results,
        'status': 'awaiting_student_review',
        'data_source': 'fictional_demo_opportunities',
        'notice': 'Demo opportunities only. No real applications are submitted.',
    }


if __name__ == '__main__':
    from pprint import pprint
    pprint(asyncio.run(run_orbit_workflow(2, ['Python'], 'all', 6)))

async def run_orbit_ai_workflow(
    student_year: int,
    student_skills: list[str],
    category: str = "all",
    hours_per_week: int = 5
):
    # First run the existing FastMCP workflow.
    result = await run_orbit_workflow(
        student_year=student_year,
        student_skills=student_skills,
        category=category,
        hours_per_week=hours_per_week
    )

    # Add AI explanations without changing eligibility results.
    for item in result["opportunities"]:
        try:
            ai_analysis = await analyze_opportunity_with_ai(
                student_profile=result["student_profile"],
                opportunity=item["opportunity"],
                eligibility=item["eligibility"],
                roadmap=item.get("growth_roadmap")
            )

            item["ai_analysis"] = ai_analysis

        
        except Exception as exc:
            print(
             "ORBIT AI analysis failed:",
             type(exc).__name__,
             str(exc)
            )


            item["ai_analysis"] = {
                "summary": "AI analysis is temporarily unavailable.",
                "match_reason": "Refer to the eligibility results.",
                "skill_gaps": "Refer to the missing skills.",
                "next_steps": "Review the proposed roadmap.",
                "student_approval_note": (
                    "Student approval is required."
                )
            }

    result["ai_enabled"] = True
    return result
