from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column


Base = declarative_base()


class Post(Base):
    __tablename__ = "board_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(String(500), default="")  # comma-separated
    category: Mapped[str] = mapped_column(String(100), default="")
    date: Mapped[str] = mapped_column(String(32), default="")  # keep as string (yyyy-mm-dd HH:MM)
    severity: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attachments: Mapped[List[Attachment]] = relationship("Attachment", cascade="all, delete-orphan", back_populates="post")


class Attachment(Base):
    __tablename__ = "board_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("board_posts.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)  # internal URL (etl-api)
    public_url: Mapped[str] = mapped_column(String(1000), default="")
    sha1: Mapped[str] = mapped_column(String(64), default="")
    size: Mapped[str] = mapped_column(String(32), default="")
    content_type: Mapped[str] = mapped_column(String(100), default="")

    post: Mapped[Post] = relationship("Post", back_populates="attachments")

