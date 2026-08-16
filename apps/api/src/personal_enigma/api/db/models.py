"""SQLAlchemy models for the local private database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for private persistence tables."""


class SyncCursorRow(Base):
    """Opaque per-source sync cursor for incremental ``DataSource`` fetches."""

    __tablename__ = "sync_cursors"

    source: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IngestedRecordRow(Base):
    """Canonical private records after ingestion (JSON payload)."""

    __tablename__ = "ingested_records"
    __table_args__ = (
        UniqueConstraint("provider", "provider_record_id", name="uq_ingested_provider_record"),
        Index("ix_ingested_source_type", "source_type"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ObligationRow(Base):
    """Durable obligation rows (evidence stored as JSON)."""

    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
