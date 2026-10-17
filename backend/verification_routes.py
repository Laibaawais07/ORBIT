"""Additive audit and real-source endpoints; no existing routes replaced."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.real_opportunities import discover_real_opportunities
from backend.approvals import get_approval_request

router = APIRouter(tags=['ORBIT verification'])

@router.get('/api/opportunities/real')
def real_opportunities(category: str = 'all'):
    results = discover_real_opportunities(category)
    return {'source': 'curated_official_pages', 'live_checked': False,
            'warning': 'Official pages are real, but registration status is not checked live. Review each source before applying.',
            'count': len(results), 'opportunities': results}

@router.get('/api/approvals/{request_id}/audit')
def approval_audit(request_id: str):
    record = get_approval_request(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Approval request not found')
    return {'request_id': request_id, 'status': record['status'],
            'can_use_roadmap': record['status'] == 'approved',
            'human_decision_required': record['status'] == 'pending',
            'external_application_submitted': False}

@router.get('/verification')
def verification_dashboard():
    file = Path(__file__).resolve().parents[1] / 'frontend' / 'verification.html'
    if not file.exists():
        raise HTTPException(status_code=404, detail='verification.html missing')
    return FileResponse(file)
