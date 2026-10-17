"""Real, official opportunity pages. Status is intentionally conservative.

Sources are curated, not a claim of a live opening or personal eligibility.
"""
from datetime import date

CATALOG = [
    {"id": "mlh-ghw-nov-2026", "title": "MLH Global Hack Week — Builders Week", "category": "hackathon", "organization": "Major League Hacking", "url": "https://ghw.mlh.com/", "start_date": "2026-11-06", "end_date": "2026-11-12", "required_skills": [], "description": "Free online community learning and building event; consult official registration details.", "eligibility_note": "MLH describes Global Hack Week as open to anyone, anywhere. Check event-specific registration.", "source_type": "official_organizer", "last_source_reviewed": "2026-10-17"},
    {"id": "mlh-ghw-dec-2026", "title": "MLH Global Hack Week — Open Source Week", "category": "hackathon", "organization": "Major League Hacking", "url": "https://ghw.mlh.com/", "start_date": "2026-12-04", "end_date": "2026-12-10", "required_skills": [], "description": "Free online event focused on open source. Consult the organizer for registration details.", "eligibility_note": "Check the official event page for up-to-date details.", "source_type": "official_organizer", "last_source_reviewed": "2026-10-17"},
    {"id": "outreachy-2026-dec", "title": "Outreachy December 2026 Internship Cohort", "category": "internship", "organization": "Outreachy", "url": "https://www.outreachy.org/apply/project-selection/", "start_date": "2026-12-07", "end_date": "2027-03-08", "initial_application_deadline": "2026-08-31", "final_application_deadline": "2026-11-02", "required_skills": [], "description": "Paid remote open-source internship. Initial applications for this cohort are closed; final applications are for previously approved applicants.", "eligibility_note": "Complex eligibility rules, including student availability and initial application approval. ORBIT cannot determine eligibility from skills alone.", "source_type": "official_organizer", "last_source_reviewed": "2026-10-17"},
    {"id": "gsoc-2026", "title": "Google Summer of Code 2026 — Participating Organizations", "category": "internship", "organization": "Google Summer of Code", "url": "https://summerofcode.withgoogle.com/programs/2026/organizations", "required_skills": [], "description": "Official directory of 2026 participating open-source organizations. This is not a currently open application listing.", "eligibility_note": "Review program rules and application window on the official site.", "source_type": "official_organizer", "last_source_reviewed": "2026-10-17"},
]


def discover_real_opportunities(category: str = 'all', today: date | None = None) -> list[dict]:
    today = today or date.today()
    requested = (category or 'all').strip().casefold()
    aliases = {'hackathons': 'hackathon', 'internships': 'internship', 'volunteering': 'volunteer'}
    requested = aliases.get(requested, requested)
    results = []
    for item in CATALOG:
        if requested not in ('all', '', item['category']):
            continue
        entry = dict(item)
        if entry['id'] == 'outreachy-2026-dec':
            entry['availability'] = 'initial_applications_closed'
        elif entry['id'] == 'gsoc-2026':
            entry['availability'] = 'historical_program_directory'
        elif entry.get('end_date') and today > date.fromisoformat(entry['end_date']):
            entry['availability'] = 'event_ended'
        elif entry.get('start_date') and today < date.fromisoformat(entry['start_date']):
            entry['availability'] = 'upcoming_event_registration_unverified'
        else:
            entry['availability'] = 'event_period_registration_unverified'
        entry['verified'] = 'official_source_exists'  # NOT verification that applications are open
        entry['live_checked'] = False
        entry['application_submitted'] = False
        results.append(entry)
    return results
