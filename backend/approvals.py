
"""Persistent, single-user DEMO approval records. No authentication yet."""

import json
import os
import sqlite3

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DB_PATH = Path(
    os.environ.get(
        "ORBIT_DB_PATH",
        str(
            Path(__file__).resolve().parents[1]
            / "data"
            / "orbit.sqlite3"
        )
    )
)


@contextmanager
def _connect():
    """Open a SQLite connection and always close it."""

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        DB_PATH,
        timeout=15
    )

    try:
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                request_id TEXT PRIMARY KEY,
                opportunity_id INTEGER NOT NULL,
                roadmap_json TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TEXT NOT NULL,
                decided_at TEXT
            )
        """)

        with conn:
            yield conn

    finally:
        conn.close()


def _row(row):
    if row is None:
        return None

    result = dict(row)

    result["roadmap"] = json.loads(
        result.pop("roadmap_json")
    )

    return result


def create_approval_request(
    opportunity_id: int,
    roadmap: dict
) -> dict:

    request_id = str(uuid4())

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO approvals
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                opportunity_id,
                json.dumps(roadmap),
                "pending",
                created_at,
                None
            )
        )

    return get_approval_request(request_id)


def get_approval_request(
    request_id: str
) -> dict | None:

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM approvals
            WHERE request_id = ?
            """,
            (request_id,)
        ).fetchone()

        return _row(row)


def decide_approval(
    request_id: str,
    decision: str
) -> dict:

    if decision not in (
        "approved",
        "rejected"
    ):
        return {
            "error": "Decision must be approved or rejected"
        }

    decided_at = datetime.now(
        timezone.utc
    ).isoformat()

    with _connect() as conn:

        cursor = conn.execute(
            """
            UPDATE approvals
            SET status = ?, decided_at = ?
            WHERE request_id = ?
              AND status = 'pending'
            """,
            (
                decision,
                decided_at,
                request_id
            )
        )

        if cursor.rowcount != 1:

            existing = conn.execute(
                """
                SELECT status
                FROM approvals
                WHERE request_id = ?
                """,
                (request_id,)
            ).fetchone()

            return {
                "error": (
                    "Approval request not found"
                    if existing is None
                    else "This request has already been decided"
                )
            }

    return get_approval_request(request_id)


def list_approval_requests():

    with _connect() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM approvals
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [
            _row(row)
            for row in rows
        ]
