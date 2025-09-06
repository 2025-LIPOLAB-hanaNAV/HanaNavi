import os
import sqlite3
from typing import Optional, List, Dict, Any


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def ensure_fts5(db_path: str) -> None:
    """Ensure an FTS5 table for posts exists (MVP schema).

    Columns: title, body, tags, category, filetype, posted_at, severity
    """
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS posts USING fts5(
                title, body, tags, category, filetype, posted_at, severity
            );
            """
        )
        # Map FTS rowid -> external post_id
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fts_row_map(
                rowid INTEGER PRIMARY KEY,
                post_id TEXT
            );
            """
        )
        # Meta tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments(
                post_id TEXT,
                filename TEXT,
                sha1 TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS post_meta(
                post_id TEXT PRIMARY KEY,
                title TEXT,
                category TEXT,
                posted_at TEXT,
                severity TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def index_post(
    db_path: str,
    *,
    post_id: str,
    title: str,
    body: str,
    tags: str = "",
    category: str = "",
    filetype: str = "",
    posted_at: Optional[str] = None,
    severity: Optional[str] = None,
) -> None:
    """Insert a post row into FTS5 index."""
    ensure_fts5(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO posts(title, body, tags, category, filetype, posted_at, severity) VALUES(?,?,?,?,?,?,?)",
            (title, body, tags, category, filetype, posted_at or "", severity or ""),
        )
        rid = cur.lastrowid
        if rid is not None:
            cur.execute(
                "REPLACE INTO fts_row_map(rowid, post_id) VALUES(?,?)",
                (rid, post_id),
            )
        conn.commit()
    finally:
        conn.close()


def save_post_meta(db_path: str, *, post_id: str, title: str, category: str = "", posted_at: str = "", severity: str = "") -> None:
    ensure_fts5(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "REPLACE INTO post_meta(post_id, title, category, posted_at, severity) VALUES(?,?,?,?,?)",
            (post_id, title, category, posted_at, severity),
        )
        conn.commit()
    finally:
        conn.close()


def save_attachments(db_path: str, *, post_id: str, items: List[Dict[str, Any]]) -> None:
    ensure_fts5(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO attachments(post_id, filename, sha1) VALUES(?,?,?)",
            [(post_id, it.get("filename", ""), it.get("sha1", "")) for it in items],
        )
        conn.commit()
    finally:
        conn.close()


def list_attachments(db_path: str, *, post_id: str) -> List[Dict[str, Any]]:
    ensure_fts5(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT filename, sha1 FROM attachments WHERE post_id=?", (post_id,))
        return [{"filename": r["filename"], "sha1": r["sha1"]} for r in cur.fetchall()]
    finally:
        conn.close()
