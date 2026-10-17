"""Authenticated application preparation and live source health routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.live_sources import check_sources
from backend.application_packets import create_packet, get_packet, confirm_handoff
from backend.approvals import get_approval_request

router = APIRouter(tags=['ORBIT completion'])

class ApplicationDraft(BaseModel):
    source_id: str
    approval_request_id: str
    motivation: str = Field(min_length=15, max_length=2500)
    achievements: str = Field(default='', max_length=2500)

@router.get('/api/opportunities/live-check')
async def live_check(category: str = 'all'):
    results = await check_sources(category)
    return {'count': len(results), 'live_checked': True,
            'registration_status_verified': False,
            'note': 'Live HTTP checks confirm page reachability only, not registration availability. Consult organizer.',
            'opportunities': results}

@router.post('/api/applications/draft')
def draft_application(data: ApplicationDraft):
    try:
        return create_packet(data.source_id, data.approval_request_id, data.motivation, data.achievements)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get('/api/applications/{packet_id}')
def read_application(packet_id: str):
    item = get_packet(packet_id)
    if not item:
        raise HTTPException(status_code=404, detail='Application packet not found')
    return item

@router.post('/api/applications/{packet_id}/handoff')
def handoff_application(packet_id: str):
    try:
        item = confirm_handoff(packet_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail='Application packet not found')
    return {'status': item['status'], 'official_url': item['content']['official_url'],
            'external_application_submitted': False,
            'next_action': 'Student must review and submit on the official organizer website.'}

@router.get('/api/approvals/{request_id}/gate-check')
def gate_check(request_id: str):
    record = get_approval_request(request_id)
    if not record:
        raise HTTPException(status_code=404, detail='Approval request not found')
    return {'status': record['status'], 'roadmap_unlocked': record['status'] == 'approved',
            'roadmap': record['roadmap'] if record['status'] == 'approved' else None}
