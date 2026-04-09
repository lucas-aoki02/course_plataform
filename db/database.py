"""
db/database.py
──────────────
SQLAlchemy engine and session management.
Supports PostgreSQL (production) and SQLite (fallback/dev).
"""

from __future__ import annotations
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

import config
from db.models import Base

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
_connect_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    config.DATABASE_URL,
    connect_args=_connect_args,
    echo=False,          # Set to True for SQL query logging during dev
    pool_pre_ping=True,  # Detect stale connections
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ── Session Context Manager ────────────────────────────────────────────────────
@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yields a transactional SQLAlchemy session, auto-commits on success or Streamlit re-runs."""
    from streamlit.runtime.scriptrunner.script_runner import StopException, RerunException
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except (StopException, RerunException):
        # Streamlit flow control exceptions shouldn't rollback valid transactions
        db.commit()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── DB Initializer ─────────────────────────────────────────────────────────────
def init_db() -> None:
    """Create all tables if they don't exist yet."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
