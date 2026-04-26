import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "app_data.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                profile_pic TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                guest_id TEXT,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                summary TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_time ON chat_history(user_id, timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_guest_time ON chat_history(guest_id, timestamp DESC)")
        conn.commit()


def upsert_user(email: str, name: str, profile_pic: str) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users(email, name, profile_pic, created_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                name=excluded.name,
                profile_pic=excluded.profile_pic
            """,
            (email, name, profile_pic, now),
        )
        conn.commit()
        row = conn.execute("SELECT id, email, name, profile_pic, created_at FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else {"email": email, "name": name, "profile_pic": profile_pic, "created_at": now}


def save_chat_entry(
    query: str,
    response_payload: Dict[str, Any],
    summary: str,
    user_id: Optional[str] = None,
    guest_id: Optional[str] = None,
) -> int:
    now = datetime.utcnow().isoformat()
    payload = json.dumps(response_payload, ensure_ascii=True)
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_history(user_id, guest_id, query, response, summary, timestamp)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (user_id, guest_id, query, payload, summary, now),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_recent_history(user_id: Optional[str], guest_id: Optional[str], limit: int = 15) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 20))
    with _get_conn() as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT id, query, summary, timestamp
                FROM chat_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        elif guest_id:
            rows = conn.execute(
                """
                SELECT id, query, summary, timestamp
                FROM chat_history
                WHERE guest_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (guest_id, limit),
            ).fetchall()
        else:
            rows = []
    return [dict(r) for r in rows]


def get_history_item(entry_id: int, user_id: Optional[str], guest_id: Optional[str]) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, guest_id, query, response, summary, timestamp
            FROM chat_history
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()

    if not row:
        return None

    data = dict(row)
    if user_id and data.get("user_id") != user_id:
        return None
    if (not user_id) and guest_id and data.get("guest_id") != guest_id:
        return None
    if (not user_id) and (not guest_id):
        return None

    try:
        data["response"] = json.loads(data.get("response") or "{}")
    except json.JSONDecodeError:
        data["response"] = {}
    return data


def get_recent_queries_for_context(user_id: Optional[str], guest_id: Optional[str], limit: int = 3) -> List[str]:
    limit = max(1, min(limit, 5))
    with _get_conn() as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT query
                FROM chat_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        elif guest_id:
            rows = conn.execute(
                """
                SELECT query
                FROM chat_history
                WHERE guest_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (guest_id, limit),
            ).fetchall()
        else:
            rows = []
    return [str(r["query"]) for r in rows if r and r["query"]]
