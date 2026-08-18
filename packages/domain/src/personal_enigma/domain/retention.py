"""Retention lineage metadata — deterministic forget graph operations (SEC-06)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryLayer(StrEnum):
    """Four-layer lifecycle position for durable PRIVATE_DERIVED rows."""

    ACTIVE = "active"
    SHADOW = "shadow"


class RetentionClass(StrEnum):
    """When justification for retaining a derived record ends."""

    ACTIVE_UNTIL_RESOLVED = "active_until_resolved"
    EPHEMERAL_ANSWER_ONLY = "ephemeral_answer_only"
    EXPIRE_WITH_SOURCE = "expire_with_source"
    DURABLE_SHADOW = "durable_shadow"


class DerivedRecordType(StrEnum):
    """Derivative classes that participate in forget cascades."""

    FACT = "fact"
    RELATION = "relation"
    EMBEDDING = "embedding"
    SUMMARY = "summary"
    FTS_CHUNK = "fts_chunk"
    AGGREGATE = "aggregate"
    FEATURE = "feature"


class RetentionPurpose(StrEnum):
    """Why Enigma retained a derived record."""

    OPEN_LOOP_TRACKING = "open_loop_tracking"
    ATTENTION_RANKING = "attention_ranking"
    RELATION_INFERENCE = "relation_inference"
    RETRIEVAL_INDEX = "retrieval_index"
    INTERACTION_AGGREGATE = "interaction_aggregate"


class LineageMetadata(BaseModel):
    """Lightweight lineage enabling ``forget(source_id)`` as a graph operation."""

    derived_from: list[str] = Field(default_factory=list)
    purpose: RetentionPurpose
    retention_class: RetentionClass
    expires_after_resolution: str | None = None


class DerivedRecord(BaseModel):
    """Structured PRIVATE_DERIVED row with lineage — no inline raw source bodies."""

    id: str
    record_type: DerivedRecordType
    memory_layer: MemoryLayer
    payload: dict[str, Any] = Field(default_factory=dict)
    lineage: LineageMetadata
    confidence: float = 1.0
    created_at: datetime
    resolved_at: datetime | None = None


class ForgetAuditEntry(BaseModel):
    """Non-sensitive deletion metadata — ids and scope only, never content."""

    source_id: str
    deleted_derived_ids: list[str] = Field(default_factory=list)
    surviving_derived_ids: list[str] = Field(default_factory=list)
    blob_ref: str | None = None
    forgotten_at: datetime


class SensitiveInferenceClass(StrEnum):
    """Pilot classes that must not be persisted permanently."""

    MEDICAL = "medical"
    SEXUALITY = "sexuality"
    POLITICAL = "political"
    SUBSTANCE = "substance"
    INTIMATE_RELATIONSHIP = "intimate_relationship"
    FINANCIAL_DISTRESS = "financial_distress"
    BEHAVIOURAL_ROUTINE = "behavioural_routine"
