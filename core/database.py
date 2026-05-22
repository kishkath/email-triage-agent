import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from .config import DB_PATH


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP NOT NULL,
                provider_used TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS digest_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT NOT NULL,
                digest_line TEXT NOT NULL,
                added_at TIMESTAMP NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def is_processed(email_id: str) -> bool:
    with _conn() as con:
        cur = con.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
        return cur.fetchone() is not None


def mark_processed(email_id: str, provider_used: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO processed_emails (email_id, processed_at, provider_used) VALUES (?, ?, ?)",
            (email_id, datetime.now(timezone.utc).isoformat(), provider_used),
        )


def add_to_digest(email_id: str, digest_line: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO digest_queue (email_id, digest_line, added_at) VALUES (?, ?, ?)",
            (email_id, digest_line, datetime.now(timezone.utc).isoformat()),
        )


def get_pending_digest() -> list[str]:
    with _conn() as con:
        cur = con.execute("SELECT digest_line FROM digest_queue WHERE sent = 0 ORDER BY added_at ASC")
        return [row[0] for row in cur.fetchall()]


def mark_digest_sent() -> None:
    with _conn() as con:
        con.execute("UPDATE digest_queue SET sent = 1 WHERE sent = 0")
