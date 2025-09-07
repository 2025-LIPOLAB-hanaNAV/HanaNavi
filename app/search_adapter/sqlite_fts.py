import os
import sqlite3
import re
from typing import List, Tuple, Dict, Any


def _db_path() -> str:
    return os.getenv("SQLITE_PATH", "/data/sqlite/ir.db")


def _normalize_query(q: str) -> str:
    # Collapse multiple spaces
    q = re.sub(r"\s+", " ", q).strip()
    # Remove spaces inserted between Korean syllables: e.g., "몽 골" -> "몽골"
    prev = None
    while prev != q:
        prev = q
        q = re.sub(r"([가-힣])\s+([가-힣])", r"\1\2", q)
    return q


def _fallback_like(conn: sqlite3.Connection, query: str, limit: int) -> List[Tuple[str, float, Dict[str, Any]]]:
    # Very simple LIKE-based fallback for small datasets, when MATCH yields 0 rows
    tokens = [t for t in re.split(r"\s+", query) if t]
    tokens = tokens[:3]  # limit terms to keep it cheap
    if not tokens:
        return []
    pattern = "%" + "%".join(tokens) + "%"
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.rowid AS id, m.post_id AS post_id, p.title, p.body, p.tags, p.category, p.filetype, p.posted_at
        FROM posts p
        LEFT JOIN fts_row_map m ON m.rowid = p.rowid
        WHERE p.title LIKE ? OR p.body LIKE ?
        LIMIT ?
        """,
        (pattern, pattern, limit),
    )
    out: List[Tuple[str, float, Dict[str, Any]]] = []
    for row in cur.fetchall():
        doc_id = f"post:{row['id']}"
        body = row["body"] or ""
        snippet = body[:300]
        payload = {
            "title": row["title"],
            "snippet": snippet,
            "tags": row["tags"],
            "category": row["category"],
            "filetype": row["filetype"],
            "date": row["posted_at"],
            "post_id": row["post_id"],
        }
        out.append((doc_id, 0.5, payload))  # neutral score
    return out


def bm25_search(query: str, top_k: int = 50) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Return list of (doc_id, score, payload) from FTS5 with BM25 ranking.

    payload contains: {title, snippet, tags, category, filetype, date}
    """
    path = _db_path()
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        q = _normalize_query(query)
        # Use bm25(fts) scoring; snippet limited
        cur.execute(
            """
            SELECT p.rowid AS id, m.post_id AS post_id, p.title, p.body, p.tags, p.category, p.filetype, p.posted_at,
                   bm25(p) AS score
            FROM posts p
            LEFT JOIN fts_row_map m ON m.rowid = p.rowid
            WHERE p MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (q, top_k),
        )
        out: List[Tuple[str, float, Dict[str, Any]]] = []
        rows = cur.fetchall()
        if not rows:
            # Fallback LIKE scan when MATCH yields 0 rows (esp. for Korean with spaced syllables)
            return _fallback_like(conn, q, top_k)
        for row in rows:
            doc_id = f"post:{row['id']}"
            body = row["body"] or ""
            snippet = body[:300]
            payload = {
                "title": row["title"],
                "snippet": snippet,
                "tags": row["tags"],
                "category": row["category"],
                "filetype": row["filetype"],
                "date": row["posted_at"],
                "post_id": row["post_id"],
            }
            # bm25 lower score = more relevant; invert for consistency
            score = 1.0 / (1.0 + float(row["score"]))
            out.append((doc_id, score, payload))
        return out
    finally:
        conn.close()
