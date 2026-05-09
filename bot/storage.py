import logging
import os
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "configs.db")


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posted_configs (
                id         TEXT PRIMARY KEY,
                name       TEXT,
                protocol   TEXT,
                posted_at  TEXT
            )
        """)
        conn.commit()
    logger.info("Database initialized.")


def is_posted(config_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_configs WHERE id = ?", (config_id,)
        ).fetchone()
    return row is not None


def mark_posted(config_id: str, name: str, protocol: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted_configs (id, name, protocol, posted_at) VALUES (?, ?, ?, ?)",
            (config_id, name, protocol, datetime.utcnow().isoformat())
        )
        conn.commit()


def cleanup_old_records(days: int = 7) -> None:
    """Remove configs older than N days so they can be re-posted (configs rotate)."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        deleted = conn.execute(
            "DELETE FROM posted_configs WHERE posted_at < ?", (cutoff,)
        ).rowcount
        conn.commit()
    if deleted:
        logger.info(f"Cleaned up {deleted} old config record(s).")
