"""Database configuration and persistence model for Phase 2."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./infrawise.db")


def _engine_options(database_url: str) -> dict[str, Any]:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(DATABASE_URL, **_engine_options(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ArchitectureRecord(Base):
    """Single JSON snapshot; the ArchSpec remains the source of truth."""

    __tablename__ = "architectures"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def init_db() -> None:
    """Create the minimal schema when the service starts."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that closes sessions on every request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
