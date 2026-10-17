"""ORBIT UI routes. Install as backend/ui.py."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
FRONTEND = Path(__file__).resolve().parents[1] / 'frontend' / 'index.html'

@router.get('/app', include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND)
