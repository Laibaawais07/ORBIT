"""Human-controlled application preparation. No automatic third-party submissions."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse
from backend.approvals import get_approval_request
from backend.real_opportunities import discover_real_opportunities

DB_PATH = Path(os.environ.get('ORBIT_APPLICATION_DB_PATH', str(Path(__file__).resolve().parents[1] / 'data' / 'orbit_applications.sqlite3')))

@contextmanager
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        con.execute('''CREATE TABLE IF NOT EXISTS application_packets (
            packet_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, approval_id TEXT NOT NULL,
            content TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
            confirmed_at TEXT)''')
        with con:
            yield con
    finally:
        con.close()


def _source(source_id):
    return next((o for o in discover_real_opportunities('all') if o['id'] == source_id), None)


def create_packet(source_id, approval_id, motivation, achievements):
    source = _source(source_id)
    if not source:
        raise ValueError('Unknown official opportunity source')
    approval = get_approval_request(approval_id)
    if not approval or approval['status'] != 'approved':
        raise PermissionError('An approved roadmap request is required to prepare an application packet')
    motivation = motivation.strip()
    achievements = achievements.strip()
    if not 15 <= len(motivation) <= 2500 or len(achievements) > 2500:
        raise ValueError('Motivation must be 15–2500 characters; achievements at most 2500')
    packet_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    content = {
        'source_title': source['title'], 'official_url': source['url'],
        'motivation': motivation, 'achievements_provided_by_student': achievements,
        'draft': f"I am interested in {source['title']}. {motivation}\n\nMy relevant experience: {achievements or 'To be completed by applicant.'}",
        'notice': 'Draft based only on student-provided facts. Review requirements, eligibility, and deadlines on the organizer website. No submission has occurred.'
    }
    with _db() as con:
        con.execute('INSERT INTO application_packets VALUES (?,?,?,?,?,?,?)',
                    (packet_id, source_id, approval_id, json.dumps(content), 'draft', now, None))
    return get_packet(packet_id)


def get_packet(packet_id):
    with _db() as con:
        row = con.execute('SELECT * FROM application_packets WHERE packet_id=?', (packet_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item['content'] = json.loads(item['content'])
    item['external_application_submitted'] = False
    return item


def confirm_handoff(packet_id):
    """User acknowledges that they will submit externally; does not claim submission."""
    packet = get_packet(packet_id)
    if not packet:
        return None
    if packet['status'] != 'draft':
        raise ValueError('Packet has already been handed off')
    approval = get_approval_request(packet['approval_id'])
    if not approval or approval['status'] != 'approved':
        raise PermissionError('Approval is no longer valid')
    with _db() as con:
        con.execute("UPDATE application_packets SET status='ready_for_manual_submission', confirmed_at=? WHERE packet_id=? AND status='draft'", (datetime.now(timezone.utc).isoformat(), packet_id))
    return get_packet(packet_id)
