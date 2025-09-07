import os
import sqlite3


def _db_path() -> str:
    return os.getenv("SQLITE_PATH", "/data/sqlite/ir.db")


def _iter_posts(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.rowid AS rowid, COALESCE(m.post_id, CAST(p.rowid AS TEXT)) AS post_id,
               p.title, p.body, p.tags, p.category, p.filetype, p.posted_at, p.severity
        FROM posts p
        LEFT JOIN fts_row_map m ON m.rowid = p.rowid
        ORDER BY p.rowid ASC
        """
    )
    for r in cur.fetchall():
        yield r


def main() -> None:
    # Late import to avoid dependency issues when not using OpenSearch
    try:
        from app.indexer.index_opensearch import upsert_post  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"OpenSearch client not available: {e}")

    path = _db_path()
    if not os.path.exists(path):
        print(f"SQLite DB not found: {path}")
        return
    conn = sqlite3.connect(path)
    try:
        total = 0
        for row in _iter_posts(conn):
            upsert_post(
                post_id=str(row["post_id"]),
                title=row["title"] or "",
                body=row["body"] or "",
                tags=row["tags"] or "",
                category=row["category"] or "",
                filetype=row["filetype"] or "",
                posted_at=row["posted_at"] or "",
                severity=row["severity"] or "",
                index=os.getenv("OPENSEARCH_INDEX", "posts"),
            )
            total += 1
            if total % 100 == 0:
                print(f"Indexed {total} posts to OpenSearch...")
        print(f"Reindex complete. Total posts indexed: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

