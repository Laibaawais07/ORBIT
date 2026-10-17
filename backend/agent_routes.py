"""Additive FastAPI endpoints for the agent engine."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.agent_engine import run_agent
from backend.ai_agent import AIProviderError, provider_name

router = APIRouter(prefix='/api/agent', tags=['ORBIT agents'])

class AgentProfile(BaseModel):
    academic_year: int = Field(ge=1, le=10)
    skills: list[str] = Field(min_length=1)
    category: str = 'all'
    hours_per_week: int = Field(default=5, ge=1, le=80)

@router.get('/status')
def agent_status():
    return {'provider': provider_name(), 'engine': 'Gemini function calling + FastMCP',
            'tools': ['discover_real_opportunities', 'search_opportunities', 'check_eligibility', 'generate_growth_roadmap'],
            'external_applications_enabled': False}

@router.post('/run')
async def agent_run(profile: AgentProfile):
    try:
        return await run_agent(profile.model_dump())
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
