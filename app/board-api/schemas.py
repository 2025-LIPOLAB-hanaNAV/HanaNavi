from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class AttachmentIn(BaseModel):
    filename: str
    url: str
    public_url: Optional[str] = ""
    sha1: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None


class PostCreate(BaseModel):
    title: str
    body: str = ""
    tags: List[str] = []
    category: str = ""
    date: str = ""
    severity: str = ""
    attachments: List[AttachmentIn] = []


class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    date: Optional[str] = None
    severity: Optional[str] = None
    attachments: Optional[List[AttachmentIn]] = None


class AttachmentOut(BaseModel):
    id: int
    filename: str
    url: str
    public_url: str | None = None
    sha1: str | None = None
    size: str | None = None
    content_type: str | None = None


class PostOut(BaseModel):
    id: int
    title: str
    body: str
    tags: List[str]
    category: str
    date: str
    severity: str
    attachments: List[AttachmentOut]


class PostList(BaseModel):
    total: int
    items: List[PostOut]

