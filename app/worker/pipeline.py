import os
import time
import hashlib
import uuid
from typing import Dict, Any, List

from app.utils.config import get_settings
from app.models.embeddings import embed_passages
from app.parser.pdf_parser import parse_pdf
from app.parser.xlsx_parser import parse_xlsx
from app.parser.docx_parser import parse_docx
from app.worker.downloader import maybe_download
from app.worker.chunker import chunk_texts
from app.indexer.index_qdrant import upsert_embeddings, ensure_collection, delete_by_post_id
from app.indexer.index_sqlite_fts5 import index_post, save_post_meta, save_attachments, delete_post as sqlite_delete
import os as _os
_IR_BACKEND = _os.getenv("IR_BACKEND", "sqlite").lower()
_USE_OPENSEARCH = _IR_BACKEND == "opensearch" or _os.getenv("IR_DUAL", "0") == "1"
os_upsert_post = None
os_delete_post = None
if _USE_OPENSEARCH:
    try:
        from app.indexer.index_opensearch import upsert_post as os_upsert_post, delete_post as os_delete_post
    except Exception:  # pragma: no cover
        # Keep None fallbacks when OpenSearch tooling is unavailable
        os_upsert_post = None
        os_delete_post = None


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
    # Allow delete action
    action = str(event.get("action", "")).lower()
    if action == "post_deleted":
        return run_delete(event)
    if action == "post_updated":
        try:
            run_delete(event)
        except Exception:
            pass

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

    # 3) Qdrant: 첨부파일만 벡터 인덱싱 (게시글 본문 제외)
    if parsed_texts:  # 첨부파일이 있는 경우만
        chunks = chunk_texts(parsed_texts, chunk_size=400, overlap=50)
        vectors = embed_passages(chunks, dim=1024)

        try:
            ensure_collection("post_chunks", dim=1024)
        except Exception:
            pass
        points = []
        for i, (text, vec) in enumerate(zip(chunks, vectors)):
            pid = str(uuid.uuid4())
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
                    "source": f"{title}#attachment:{i}",  # 첨부파일임을 명시
                    "filetype": filetype,
                    "posted_at": date,
                }
            )
        upsert_embeddings("post_chunks", points, dim=1024)

    # 4) OpenSearch/SQLite FTS: 게시글 본문만 인덱싱 (첨부파일 제외)
    index_post(
        sqlite_path,
        post_id=post_id,
        title=title,
        body=body,  # 게시글 본문만 인덱싱
        tags=tags,
        category=category,
        filetype=filetype,
        posted_at=date,
        severity=str(event.get("severity", ""))
    )
    # Optional: also index into OpenSearch for scalable IR
    if _USE_OPENSEARCH and os_upsert_post is not None:
        try:
            os_upsert_post(
                post_id=post_id,
                title=title,
                body=body,  # 게시글 본문만 인덱싱
                tags=tags,
                category=category,
                filetype=filetype,
                posted_at=date,
                severity=str(event.get("severity", "")),
                index=_os.getenv("OPENSEARCH_INDEX", "posts"),
            )
        except Exception:
            pass

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


def run_delete(event: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    sqlite_path = settings.get("SQLITE_PATH", "/data/sqlite/ir.db")
    post_id = str(event.get("post_id", ""))
    if not post_id:
        raise ValueError("post_id required for delete")
    # Delete from Qdrant
    try:
        delete_by_post_id("post_chunks", post_id)
    except Exception:
        pass
    # Delete from SQLite FTS/meta
    try:
        sqlite_delete(sqlite_path, post_id=post_id)
    except Exception:
        pass
    # Delete from OpenSearch if enabled
    if _USE_OPENSEARCH and 'os_delete_post' in globals() and os_delete_post is not None:  # type: ignore
        try:
            os_delete_post(post_id, index=_os.getenv("OPENSEARCH_INDEX", "posts"))  # type: ignore
        except Exception:
            pass
    return {"status": "deleted", "post_id": post_id}
