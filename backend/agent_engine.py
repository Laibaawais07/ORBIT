"""ORBIT agent orchestrator: LLM chooses MCP tools, tools execute locally.

No tool can submit an external application. Demo opportunities are fictional.
"""
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
from fastmcp import Client
from backend.mcp_server import mcp
from backend.approvals import create_approval_request
from backend.real_opportunities import discover_real_opportunities
from backend.ai_agent import AIProviderError, provider_name, _safe_error

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

TOOLS = [
    {'name': 'discover_real_opportunities', 'description': 'Real Source Discovery specialist: list real official opportunity pages and conservative registration status. Prefer this to fictional demos. Always tell the user that open registration is unverified.', 'parameters': {'type': 'OBJECT', 'properties': {'category': {'type': 'STRING'}}, 'required': ['category']}},
    {'name': 'search_opportunities', 'description': 'Discovery specialist: find fictional demo opportunities by category. Always call this first.',
     'parameters': {'type': 'OBJECT', 'properties': {'category': {'type': 'STRING', 'description': 'Category from student profile'}}, 'required': ['category']}},
    {'name': 'check_eligibility', 'description': 'Eligibility specialist: check a demo opportunity against academic year and student skills.',
     'parameters': {'type': 'OBJECT', 'properties': {'opportunity_id': {'type': 'INTEGER'}, 'student_year': {'type': 'INTEGER'}, 'student_skills': {'type': 'ARRAY', 'items': {'type': 'STRING'}}}, 'required': ['opportunity_id', 'student_year', 'student_skills']}},
    {'name': 'generate_growth_roadmap', 'description': 'Growth specialist: propose a roadmap when missing skills exist. It requires human approval before use.',
     'parameters': {'type': 'OBJECT', 'properties': {'missing_skills': {'type': 'ARRAY', 'items': {'type': 'STRING'}}, 'hours_per_week': {'type': 'INTEGER'}}, 'required': ['missing_skills', 'hours_per_week']}},
]
TOOL_NAMES = {t['name'] for t in TOOLS}
SYSTEM = (
    'You are ORBIT, an autonomous opportunity planning orchestrator with Discovery, Eligibility, and Growth specialist tools. '
    'Use discover_real_opportunities first to find official sources. You may also use search_opportunities for clearly labeled fictional demos, then check eligibility and propose roadmaps for demo matches. '
    'Never claim a real source is currently accepting applications or that a student is eligible without verifying organizer rules. You may call multiple tools across turns. '
    'Only call roadmap for missing skills found in an eligibility tool response. '
    'Never claim these fictional listings are live or verified. '
    'Never submit an application or claim student approval. '
    'End with a concise summary after using the tools.'
)


def _extract_data(tool_result):
    value = getattr(tool_result, 'data', None)
    if value is not None:
        return value
    contents = getattr(tool_result, 'content', [])
    if contents and hasattr(contents[0], 'text'):
        try:
            return json.loads(contents[0].text)
        except (ValueError, TypeError):
            return contents[0].text
    return None


def _validate_call(name, args, profile, discovered, eligibility_by_id):
    """Enforce safe tool arguments regardless of what the LLM requests."""
    if name == 'discover_real_opportunities':
        return {'category': profile['category']}
    if name == 'search_opportunities':
        return {'category': profile['category']}
    if name == 'check_eligibility':
        opportunity_id = args.get('opportunity_id')
        if isinstance(opportunity_id, bool) or not isinstance(opportunity_id, int) or opportunity_id not in discovered:
            raise ValueError('Unknown opportunity ID; discover opportunities first')
        return {'opportunity_id': opportunity_id, 'student_year': profile['academic_year'], 'student_skills': profile['skills']}
    if name == 'generate_growth_roadmap':
        requested = args.get('missing_skills')
        if not isinstance(requested, list) or not requested or not all(isinstance(x, str) for x in requested):
            raise ValueError('Roadmap requires missing skills')
        allowed = {str(skill).casefold() for e in eligibility_by_id.values() for skill in e.get('missing_skills', [])}
        if not allowed or not all(skill.casefold() in allowed for skill in requested):
            raise ValueError('Roadmap skills must come from checked eligibility')
        return {'missing_skills': requested, 'hours_per_week': profile['hours_per_week']}
    raise ValueError('Tool is not allowed')


async def run_agent(profile: dict) -> dict:
    if provider_name() != 'gemini':
        raise AIProviderError('The autonomous agent currently requires AI_PROVIDER=gemini')
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        raise AIProviderError('GEMINI_API_KEY is missing')
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    messages = [{'role': 'user', 'parts': [{'text': json.dumps({'task': 'Analyze opportunities for this student', 'student_profile': profile})}]}]
    trace, discovered, eligibility_by_id, roadmaps, real_sources = [], {}, {}, [], []
    # Bounded iterations and calls to limit costs and prevent loops.
    async with httpx.AsyncClient(timeout=45) as http, Client(mcp) as mcp_client:
        for iteration in range(8):
            body = {'systemInstruction': {'parts': [{'text': SYSTEM}]}, 'contents': messages,
                    'tools': [{'functionDeclarations': TOOLS}], 'generationConfig': {'temperature': 0.1}}
            response = await http.post(url, headers={'x-goog-api-key': key}, json=body)
            if response.status_code >= 400:
                raise AIProviderError(f'Gemini API HTTP {response.status_code}: {_safe_error(response)}')
            try:
                candidate = response.json()['candidates'][0]['content']
                parts = candidate.get('parts', [])
            except (KeyError, IndexError, TypeError) as exc:
                raise AIProviderError('Gemini returned no agent response') from exc
            calls = [p['functionCall'] for p in parts if 'functionCall' in p]
            if not calls:
                text = '\n'.join(p.get('text', '') for p in parts).strip()
                return _build_result(profile, trace, discovered, eligibility_by_id, roadmaps, text, 'completed', real_sources)
            messages.append({'role': 'model', 'parts': parts})
            responses = []
            for call in calls[:6]:
                name, args = call.get('name', ''), call.get('args', {})
                if name not in TOOL_NAMES:
                    result = {'error': 'Tool not allowed'}
                else:
                    try:
                        validated = _validate_call(name, args, profile, discovered, eligibility_by_id)
                        if name == 'discover_real_opportunities':
                            result = discover_real_opportunities(validated['category'])
                        else:
                            output = await mcp_client.call_tool(name, validated)
                            result = _extract_data(output)
                        if name == 'discover_real_opportunities' and isinstance(result, list):
                            real_sources = result
                        if name == 'search_opportunities' and isinstance(result, list):
                            discovered.update({o['id']: o for o in result if isinstance(o, dict) and 'id' in o})
                        if name == 'check_eligibility' and isinstance(result, dict):
                            eligibility_by_id[validated['opportunity_id']] = result
                        if name == 'generate_growth_roadmap' and isinstance(result, dict):
                            # Roadmaps are suggestions only. Approval is created below.
                            roadmaps.append({'skills': validated['missing_skills'], 'roadmap': result})
                        trace.append({'agent': {'discover_real_opportunities': 'Real Source Discovery', 'search_opportunities': 'Discovery', 'check_eligibility': 'Eligibility', 'generate_growth_roadmap': 'Growth'}[name],
                                      'tool': name, 'arguments': validated, 'result': result})
                    except (ValueError, KeyError, TypeError) as exc:
                        result = {'error': str(exc)}
                responses.append({'functionResponse': {'name': name or 'unknown', 'response': {'result': result}}})
            messages.append({'role': 'user', 'parts': responses})
    return _build_result(profile, trace, discovered, eligibility_by_id, roadmaps, 'Tool iteration limit reached.', 'limit_reached', real_sources)


def _build_result(profile, trace, discovered, eligibility_by_id, roadmaps, summary, status, real_sources):
    approvals = []
    # Associate roadmaps with checked opportunities using matching missing skills.
    for item in roadmaps:
        skills = {s.casefold() for s in item['skills']}
        for opportunity_id, eligibility in eligibility_by_id.items():
            missing = {str(s).casefold() for s in eligibility.get('missing_skills', [])}
            if skills and skills == missing and eligibility.get('academic_eligibility') == 'eligible':
                approvals.append(create_approval_request(opportunity_id, item['roadmap']))
                break
    return {'status': status, 'ai_provider': 'gemini', 'agentic': bool(trace),
            'student_profile': profile, 'summary': summary,
            'opportunities': [{'opportunity': o, 'eligibility': eligibility_by_id.get(oid)} for oid, o in discovered.items()],
            'proposed_roadmaps': roadmaps, 'approval_requests': approvals, 'tool_trace': trace,
            'real_opportunities': real_sources, 'tool_verification': {'executed_count': len(trace), 'executed_tools': [t['tool'] for t in trace], 'has_real_source_discovery': any(t['tool'] == 'discover_real_opportunities' for t in trace)},
            'data_source': 'official_curated_sources_plus_optional_fictional_demo',
            'notice': 'Real sources are official but NOT live-checked for registration. Demo listings are fictional. Human approval is required for roadmap use. No application was submitted.'}
