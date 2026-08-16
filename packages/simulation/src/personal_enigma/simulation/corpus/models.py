"""Corpus message models — source-layer only (no Enigma obligations)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CorpusProvenance(StrEnum):
    """Provenance gate for public Demo vs developer profiles (ADR-007)."""

    SYNTHETIC_CONFIRMED = "synthetic_confirmed"
    PUBLIC_REAL = "public_real"
    UNKNOWN = "unknown"


class CorpusMessage(BaseModel):
    """One email inside a corpus conversation.

    Forbidden: importance flags, obligations, attention labels, signal_class.
    """

    corpus_id: str
    conversation_id: str
    message_index: int

    sender_name: str
    sender_email: str

    recipient_names: list[str] = Field(default_factory=list)
    recipient_emails: list[str] = Field(default_factory=list)

    subject: str
    body_text: str


class CorpusConversation(BaseModel):
    """Thread-preserving conversation unit for selection + sanitisation."""

    id: str
    messages: list[CorpusMessage] = Field(default_factory=list)


class CorpusMetadata(BaseModel):
    """Adapter inspect() summary — not fed to Enigma."""

    corpus_id: str
    provenance: CorpusProvenance
    revision: str | None = None
    conversation_count: int | None = None
    description: str | None = None
