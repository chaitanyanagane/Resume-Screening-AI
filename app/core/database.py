"""
SQLAlchemy engine, session factory, and ``get_db`` FastAPI dependency.

Supports both SQLite (development) and PostgreSQL (production) transparently.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.core.config import settings

# ── Engine creation ─────────────────────────────────────────────────────
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///./") and not os.access(".", os.W_OK):
    # Fallback to /tmp in read-only environments like Vercel serverless
    db_url = "sqlite:////tmp/hiresense.db"

_connect_args = {}
_engine_kwargs: dict = {"pool_pre_ping": True}

if db_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False
    # SQLite does not support pool_size / max_overflow
    _engine_kwargs.pop("pool_pre_ping", None)

engine = create_engine(
    db_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)

# Enable foreign key enforcement for SQLite
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = DELETE")
        cursor.close()

# ── Session factory ─────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Declarative base ───────────────────────────────────────────────────
Base = declarative_base()


# ── FastAPI dependency ──────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
