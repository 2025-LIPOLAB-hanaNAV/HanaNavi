import sqlite3


def ensure_fts5(db_path: str) -> None:
    """Ensure an FTS5 table for posts exists (MVP schema)."""
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

