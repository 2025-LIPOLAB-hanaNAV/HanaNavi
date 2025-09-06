import os
import time
import hashlib
from typing import Dict, Any, List

from app.utils.config import get_settings
from app.models.embeddings import embed_passages
from app.parser.pdf_parser import parse_pdf
from app.parser.xlsx_parser import parse_xlsx
from app.parser.docx_parser import parse_docx
from app.worker.downloader import maybe_download
from app.worker.chunker import chunk_texts
from app.indexer.index_qdrant import upsert_embeddings
from app.indexer.index_sqlite_fts5 import index_post, save_post_meta, save_attachments


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _parse_attachment(path: str) -> List[str]:
    lower = path.lower()
    if lower.endswith(".pdf"):
        return parse_pdf(path)
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        return parse_xlsx(path)
    if lower.endswith(".docx"):
        return parse_docx(path)
    return []


def run_ingest(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single webhook event and index content.

    Expected minimal event fields:
    - post_id: int or str
    - title: str
    - body: str (optional)
    - tags, category, filetype, date: optional metadata
    - attachments: [{filename, url}] (optional)
    """
    settings = get_settings()
    storage = settings.get("STORAGE_DIR", "/data/storage")
    sqlite_path = settings.get("SQLITE_PATH", "/data/sqlite/ir.db")

    post_id = str(event.get("post_id", "unknown"))
    title = str(event.get("title", f"post:{post_id}"))
    body = str(event.get("body", ""))
    tags = ",".join(event.get("tags", []) or []) if isinstance(event.get("tags"), list) else str(event.get("tags", ""))
    category = str(event.get("category", ""))
    filetype = str(event.get("filetype", ""))
    date = str(event.get("date", ""))

    # 1) Download attachments
    attachments = event.get("attachments") or []
    post_dir = os.path.join(storage, "posts", post_id)
    local_paths: List[str] = []
    attachment_infos: List[Dict[str, Any]] = []
    for att in attachments:
        url = att.get("url")
        filename = att.get("filename") or f"file_{int(time.time())}"
        path = maybe_download(post_dir, filename, url)
        if path:
            # Hash verification
            with open(path, "rb") as f:
                digest = _sha1(f.read())
            expected = att.get("sha1") or att.get("checksum")
            if expected and expected != digest:
                raise ValueError(f"checksum mismatch for {filename}")
            local_paths.append(path)
            attachment_infos.append({"filename": filename, "sha1": digest})

    # 2) Parse attachments
    parsed_texts: List[str] = []
    for p in local_paths:
        parsed_texts.extend(_parse_attachment(p))

    # include body as a text source
    if body:
        parsed_texts.insert(0, body)

    # 3) Chunk
    chunks = chunk_texts(parsed_texts, chunk_size=400, overlap=50)

    # 4) Embed
    vectors = embed_passages(chunks, dim=1024)

    # 5) Upsert to Qdrant
    points = []
    for i, (text, vec) in enumerate(zip(chunks, vectors)):
        pid = f"{post_id}_{i}"
        points.append(
            {
                "id": pid,
                "vector": vec,
                "post_id": post_id,
                "chunk_id": i,
                "text": text,
                "title": title,
                "category": category,
                "tags": tags,
                "source": f"{title}#chunk:{i}",
                "filetype": filetype,
                "posted_at": date,
            }
        )
    upsert_embeddings("post_chunks", points, dim=1024)

    # 6) Index IR (title/body/tags...)
    index_post(
        sqlite_path,
        title=title,
        body="\n".join(parsed_texts),
        tags=tags,
        category=category,
        filetype=filetype,
        posted_at=date,
        severity=str(event.get("severity", "")),
    )

    # 7) Save meta + attachments for UI
    save_post_meta(
        sqlite_path,
        post_id=post_id,
        title=title,
        category=category,
        posted_at=date,
        severity=str(event.get("severity", "")),
    )
    if attachment_infos:
        save_attachments(sqlite_path, post_id=post_id, items=attachment_infos)

    return {
        "post_id": post_id,
        "title": title,
        "attachments": len(local_paths),
        "chunks": len(chunks),
        "indexed": True,
        "attachments_meta": attachment_infos,
    }
