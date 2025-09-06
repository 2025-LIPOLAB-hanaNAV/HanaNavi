import os
import sqlite3
from typing import Optional


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def ensure_fts5(db_path: str) -> None:
    """Ensure an FTS5 table for posts exists (MVP schema)."""
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS posts USING fts5(
                title, body, tags, category, filetype, date
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def index_post(
    db_path: str,
    *,
    title: str,
    body: str,
    tags: str = "",
    category: str = "",
    filetype: str = "",
    date: Optional[str] = None,
) -> None:
    """Insert a post row into FTS5 index."""
    ensure_fts5(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO posts(title, body, tags, category, filetype, date) VALUES(?,?,?,?,?,?)",
            (title, body, tags, category, filetype, date or ""),
        )
        conn.commit()
    finally:
        conn.close()
