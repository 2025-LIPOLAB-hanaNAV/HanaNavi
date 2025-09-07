from __future__ import annotations

import os
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
import httpx

from db import engine, get_session
from models import Base, Post, Attachment
from schemas import PostCreate, PostUpdate, PostOut, PostList, AttachmentOut


Base.metadata.create_all(bind=engine)

app = FastAPI(title="board-api", version="0.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _to_post_out(p: Post) -> PostOut:
    atts: List[AttachmentOut] = [
        AttachmentOut(
            id=a.id,
            filename=a.filename,
            url=a.url,
            public_url=a.public_url,
            sha1=a.sha1,
            size=a.size,
            content_type=a.content_type,
        )
        for a in p.attachments
    ]
    tags = [t for t in (p.tags or "").split(",") if t]
    return PostOut(
        id=p.id,
        title=p.title,
        body=p.body or "",
        tags=tags,
        category=p.category or "",
        date=p.date or "",
        severity=p.severity or "",
        attachments=atts,
    )


@app.get("/posts", response_model=PostList)
def list_posts(page: int = 1, page_size: int = 20, q: str = "") -> PostList:
    if page_size > 100:
        page_size = 100
    with get_session() as db:
        stmt = select(Post).order_by(Post.id.desc())
        rows = db.execute(stmt).scalars().all()
        items = rows
        if q:
            qq = q.lower()
            items = [r for r in rows if qq in (r.title or '').lower() or qq in (r.category or '').lower() or qq in (r.tags or '').lower()]
        total = len(items)
        start = max(0, (page - 1) * page_size)
        paged = items[start:start + page_size]
        return PostList(total=total, items=[_to_post_out(p) for p in paged])


@app.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int) -> PostOut:
    with get_session() as db:
        p = db.get(Post, post_id)
        if not p:
            raise HTTPException(status_code=404, detail="not found")
        return _to_post_out(p)


def _store_attachments(db: Session, p: Post, items: List[Dict[str, Any]]) -> None:
    p.attachments.clear()
    for it in items:
        p.attachments.append(
            Attachment(
                filename=it.get("filename", ""),
                url=it.get("url", ""),
                public_url=it.get("public_url") or "",
                sha1=it.get("sha1") or "",
                size=str(it.get("size") or ""),
                content_type=it.get("content_type") or "",
            )
        )


async def _notify_etl(event: Dict[str, Any]) -> None:
    etl_internal = os.getenv("ETL_BASE_URL", "http://etl-api:8000")
    url = f"{etl_internal}/ingest/webhook"
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            await cli.post(url, json=event)
    except Exception:
        # best-effort
        pass


@app.post("/posts", response_model=PostOut)
async def create_post(body: PostCreate) -> PostOut:
    with get_session() as db:
        p = Post(
            title=body.title,
            body=body.body or "",
            tags=",".join(body.tags or []),
            category=body.category or "",
            date=body.date or "",
            severity=body.severity or "",
        )
        db.add(p)
        db.flush()  # assign id
        _store_attachments(db, p, [a.model_dump() for a in body.attachments or []])
        db.flush()
        post_id = p.id

    # Notify ETL for indexing
    event = {
        "action": "post_created",
        "post_id": post_id,
        "title": body.title,
        "body": body.body,
        "tags": body.tags,
        "category": body.category,
        "date": body.date,
        "severity": body.severity,
        "attachments": [a.model_dump() for a in body.attachments or []],
    }
    await _notify_etl(event)

    # Return fresh object
    with get_session() as db:
        p = db.get(Post, post_id)
        assert p is not None
        return _to_post_out(p)


@app.put("/posts/{post_id}", response_model=PostOut)
async def update_post(post_id: int, body: PostUpdate) -> PostOut:
    with get_session() as db:
        p = db.get(Post, post_id)
        if not p:
            raise HTTPException(status_code=404, detail="not found")
        if body.title is not None:
            p.title = body.title
        if body.body is not None:
            p.body = body.body
        if body.tags is not None:
            p.tags = ",".join(body.tags)
        if body.category is not None:
            p.category = body.category
        if body.date is not None:
            p.date = body.date
        if body.severity is not None:
            p.severity = body.severity
        if body.attachments is not None:
            _store_attachments(db, p, [a.model_dump() for a in body.attachments])
        db.flush()

    # Notify ETL
    event = {
        "action": "post_updated",
        "post_id": post_id,
        "title": body.title,
        "body": body.body,
        "tags": body.tags,
        "category": body.category,
        "date": body.date,
        "severity": body.severity,
        "attachments": [a.model_dump() for a in (body.attachments or [])],
    }
    await _notify_etl(event)

    with get_session() as db:
        p = db.get(Post, post_id)
        assert p is not None
        return _to_post_out(p)


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int) -> Dict[str, Any]:
    with get_session() as db:
        p = db.get(Post, post_id)
        if not p:
            raise HTTPException(status_code=404, detail="not found")
        db.delete(p)
    # Notify ETL (best-effort)
    await _notify_etl({"action": "post_deleted", "post_id": post_id})
    return {"status": "ok", "post_id": post_id}

