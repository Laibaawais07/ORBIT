"""Provider-independent AI explanations. No API secrets are logged."""
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

class AIProviderError(RuntimeError):
    pass


def provider_name():
    return os.getenv('AI_PROVIDER', 'gemini').strip().lower()


async def generate_json(instructions: str, payload: dict) -> dict:
    provider = provider_name()
    if provider == 'gemini':
        key = os.getenv('GEMINI_API_KEY', '').strip()
        if not key:
            raise AIProviderError('GEMINI_API_KEY is missing from .env')
        model = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        request = {
            'systemInstruction': {'parts': [{'text': instructions}]},
            'contents': [{'role': 'user', 'parts': [{'text': json.dumps(payload)}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.2},
        }
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(url, headers={'x-goog-api-key': key}, json=request)
        if response.status_code >= 400:
            raise AIProviderError(f'Gemini API HTTP {response.status_code}: {_safe_error(response)}')
        try:
            parts = response.json()['candidates'][0]['content']['parts']
            return json.loads(''.join(p.get('text', '') for p in parts))
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise AIProviderError('Gemini returned no valid JSON response') from exc
    if provider == 'openai':
        from openai import AsyncOpenAI
        if not os.getenv('OPENAI_API_KEY'):
            raise AIProviderError('OPENAI_API_KEY is missing from .env')
        async with AsyncOpenAI(timeout=35, max_retries=1) as client:
            result = await client.responses.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
                instructions=instructions + ' Return a valid JSON object.',
                input=json.dumps(payload),
                text={'format': {'type': 'json_object'}},
            )
        return json.loads(result.output_text)
    raise AIProviderError('AI_PROVIDER must be gemini or openai')


def _safe_error(response):
    try:
        err = response.json().get('error', {})
        return str(err.get('message', 'API request failed'))[:300]
    except (ValueError, AttributeError):
        return 'API request failed'


async def analyze_opportunity_with_ai(student_profile, opportunity, eligibility, roadmap):
    result = await generate_json(
        'You are the ORBIT Growth Specialist. Respond only with JSON with string fields '
        'summary, match_reason, skill_gaps, next_steps, student_approval_note. '
        'Treat all supplied opportunities as fictional demonstrations, never as verified open calls. '
        'Never invent requirements, deadlines, URLs or achievements. Student approval is mandatory.',
        {'student_profile': student_profile, 'opportunity': opportunity,
         'eligibility': eligibility, 'roadmap': roadmap},
    )
    fields = ('summary', 'match_reason', 'skill_gaps', 'next_steps', 'student_approval_note')
    if not isinstance(result, dict) or not all(isinstance(result.get(k), str) for k in fields):
        raise AIProviderError('AI returned unexpected analysis fields')
    return {k: result[k] for k in fields}
