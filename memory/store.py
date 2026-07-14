import sqlite3
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = "tieredflow.db"


@dataclass
class Message:
    message_id: int
    session_id: str
    user_query: str
    response: str
    task_type: str
    tier: str
    model_id: str
    cost_usd: float
    latency_ms: int
    served_from_cache: bool
    timestamp: str


@dataclass
class Session:
    session_id: str
    started_at: str
    last_active: str
    total_cost_usd: float
    total_messages: int


class ConversationStore:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id    TEXT PRIMARY KEY,
                    started_at    TEXT NOT NULL,
                    last_active   TEXT NOT NULL,
                    total_cost_usd REAL DEFAULT 0.0,
                    total_messages INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id        TEXT NOT NULL,
                    user_query        TEXT NOT NULL,
                    response          TEXT NOT NULL,
                    task_type         TEXT,
                    tier              TEXT,
                    model_id          TEXT,
                    cost_usd          REAL DEFAULT 0.0,
                    latency_ms        INTEGER DEFAULT 0,
                    served_from_cache INTEGER DEFAULT 0,
                    timestamp         TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()
        logger.info(f"[Store] Database initialised at {self.db_path}")

    def create_session(self, session_id: str):
        """Create a new session record."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO sessions
                (session_id, started_at, last_active, total_cost_usd, total_messages)
                VALUES (?, ?, ?, 0.0, 0)
            """, (session_id, now, now))
            conn.commit()
        logger.info(f"[Store] Session created: {session_id}")

    def save_message(
        self,
        session_id: str,
        user_query: str,
        response: str,
        task_type: str = "",
        tier: str = "",
        model_id: str = "",
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        served_from_cache: bool = False,
    ):
        """Save a message and update session totals."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages
                (session_id, user_query, response, task_type, tier, model_id,
                 cost_usd, latency_ms, served_from_cache, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_query, response, task_type, tier, model_id,
                cost_usd, latency_ms, int(served_from_cache), now,
            ))
            conn.execute("""
                UPDATE sessions
                SET last_active    = ?,
                    total_cost_usd = total_cost_usd + ?,
                    total_messages = total_messages + 1
                WHERE session_id = ?
            """, (now, cost_usd, session_id))
            conn.commit()
        logger.info(f"[Store] Message saved for session {session_id}")

    def get_all_sessions(self) -> list[Session]:
        """Return all sessions ordered by most recent activity."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT session_id, started_at, last_active,
                       total_cost_usd, total_messages
                FROM sessions
                ORDER BY last_active DESC
            """).fetchall()
        return [Session(*row) for row in rows]

    def get_session_messages(self, session_id: str) -> list[Message]:
        """Return all messages for a given session."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT message_id, session_id, user_query, response,
                       task_type, tier, model_id, cost_usd, latency_ms,
                       served_from_cache, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY message_id ASC
            """, (session_id,)).fetchall()
        return [Message(*row) for row in rows]

    def delete_session(self, session_id: str):
        """Delete a session and all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        logger.info(f"[Store] Session deleted: {session_id}")


# Singleton
_store_instance: Optional[ConversationStore] = None


def get_store() -> ConversationStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = ConversationStore()
    return _store_instance