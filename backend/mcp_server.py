
from fastmcp import FastMCP

# Create the MCP server for ORBIT
mcp = FastMCP("ORBIT Opportunity Tools")

# Temporary example opportunities.
# Later, we will replace these with real listings
# retrieved from verified sources.
OPPORTUNITIES = [
    {
        "id": 1,
        "title": "AI Research Internship",
        "category": "research",
        "required_skills": ["Python", "Machine Learning"],
        "minimum_year": 2
    },
    {
        "id": 2,
        "title": "Global Hackathon",
        "category": "hackathon",
        "required_skills": ["Python"],
        "minimum_year": 1
    },
    {
        "id": 3,
        "title": "Community Technology Volunteer",
        "category": "volunteering",
        "required_skills": ["Communication"],
        "minimum_year": 1
    }
]


@mcp.tool
def search_opportunities(category: str = "all") -> list[dict]:
    """
    Search example opportunities by category.

    category can be research, hackathon,
    volunteering, or all.
    """
    if category.lower() == "all":
        return OPPORTUNITIES

    return [
        opportunity
        for opportunity in OPPORTUNITIES
        if opportunity["category"].lower() == category.lower()
    ]


@mcp.tool
def check_eligibility(
    opportunity_id: int,
    student_year: int,
    student_skills: list[str]
) -> dict:
    """
    Check a student's academic-year requirement
    and identify missing skills for an opportunity.
    """

    opportunity = next(
        (
            item for item in OPPORTUNITIES
            if item["id"] == opportunity_id
        ),
        None
    )

    if opportunity is None:
        return {
            "error": "Opportunity not found"
        }

    required_year = opportunity["minimum_year"]

    year_eligible = student_year >= required_year

    student_skills_normalized = {
        skill.strip().lower()
        for skill in student_skills
    }

    missing_skills = [
        skill
        for skill in opportunity["required_skills"]
        if skill.lower() not in student_skills_normalized
    ]

    matched_skills = [
        skill
        for skill in opportunity["required_skills"]
        if skill.lower() in student_skills_normalized
    ]

    return {
        "opportunity": opportunity["title"],
        "academic_eligibility": (
            "eligible" if year_eligible else "ineligible"
        ),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "readiness": (
            "ready" if year_eligible and not missing_skills
            else "needs_preparation"
        )
    }

@mcp.tool
def generate_growth_roadmap(
    missing_skills: list[str],
    hours_per_week: int = 5
) -> dict:
    """
    Generate a basic skill development roadmap.
    This is a starter version using predefined steps.
    """

    if hours_per_week <= 0:
        return {"error": "Hours per week must be positive"}

    roadmaps = {
        "machine learning": [
            "Learn supervised and unsupervised learning basics",
            "Practice using scikit-learn",
            "Train and evaluate a simple ML model",
            "Build a portfolio project"
        ],
        "python": [
            "Learn Python syntax and data types",
            "Practice functions, loops, and data structures",
            "Build a small automation project",
            "Publish the project on GitHub"
        ],
        "communication": [
            "Practice professional written communication",
            "Prepare a short presentation",
            "Practice explaining a technical topic",
            "Collect feedback and improve"
        ]
    }

    plan = []

    for skill in missing_skills:
        steps = roadmaps.get(
            skill.lower(),
            [
                f"Study the fundamentals of {skill}",
                f"Complete a practical exercise in {skill}",
                f"Build a small project using {skill}",
                f"Collect feedback on your {skill} work"
            ]
        )

        plan.append({
            "skill": skill,
            "steps": steps
        })

    return {
        "hours_per_week": hours_per_week,
        "roadmap": plan,
        "status": "draft_pending_student_approval"
    }

if __name__ == "__main__":
    mcp.run()
