import os
import sqlite3
from typing import List, Tuple, Dict, Any


def _db_path() -> str:
    return os.getenv("SQLITE_PATH", "/data/sqlite/ir.db")


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
        # Use bm25(fts) scoring; snippet limited
        cur.execute(
            """
            SELECT rowid AS id, title, body, tags, category, filetype, posted_at,
                   bm25(posts) AS score
            FROM posts
            WHERE posts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, top_k),
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
            }
            # bm25 lower score = more relevant; invert for consistency
            score = 1.0 / (1.0 + float(row["score"]))
            out.append((doc_id, score, payload))
        return out
    finally:
        conn.close()
