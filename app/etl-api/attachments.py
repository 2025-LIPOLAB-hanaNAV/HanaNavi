import os
from typing import List, Dict, Any

from app.indexer.index_sqlite_fts5 import list_attachments


def get_attachments(post_id: str, public_base: str) -> List[Dict[str, Any]]:
    items = list_attachments(os.getenv("SQLITE_PATH", "/data/sqlite/ir.db"), post_id=post_id)
    out = []
    for it in items:
        fn = it.get("filename", "")
        out.append(
            {
                "filename": fn,
                "sha1": it.get("sha1"),
                "public_url": f"{public_base}/files/{fn}",
            }
        )
    return out

