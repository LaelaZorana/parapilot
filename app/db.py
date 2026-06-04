"""SQLite storage for saved progress / matters (SPEC §7).

Lean SQLAlchemy setup. The DB stores a lightweight "matter" (a saved progress
record) and per-step completion. It never stores legal advice, only the user's
own checklist state and free-text notes.
"""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

_settings = get_settings()

# check_same_thread=False is needed for SQLite under the threaded dev server.
_connect_args = (
    {"check_same_thread": False} if _settings.db_url.startswith("sqlite") else {}
)
engine = create_engine(_settings.db_url, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they don't exist (idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
