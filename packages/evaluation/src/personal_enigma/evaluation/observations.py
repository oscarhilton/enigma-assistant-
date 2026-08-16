"""Run-time observation inputs for Demo Mode evaluation.

These capture what Enigma *did* during a demo run. They are never Private Mode
artefacts and must not embed private storage roots or HMAC material.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SurfacedAlert(BaseModel):
    """One attention item observed during evaluation."""

    id: str
    title: str = ""
    kind: str = ""
    score: float = 0.0
    obligation_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    duplicate_of: str | None = None
    resolved_underlying: bool = False
    surfaced_at: datetime | None = None

    @field_validator("surfaced_at", mode="before")
    @classmethod
    def _parse_surfaced_at(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
        return value


class PrivacyProbe(BaseModel):
    """A remote-facing payload checked against privacy invariants."""

    id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    people: list[dict[str, Any]] = Field(default_factory=list)
    source_type: str | None = None
    privacy_level: str | None = None
    was_blocked: bool = False
    block_reason: str | None = None


class MemoryObservation(BaseModel):
    """Observed memory state at a checkpoint (stub-friendly)."""

    at: datetime | None = None
    memory_ids: list[str] = Field(default_factory=list)
    texts: list[str] = Field(default_factory=list)


class CostEvent(BaseModel):
    """Stub provider cost event for extrapolation."""

    category: Literal[
        "attention_reasoning",
        "memory_extraction",
        "context_summarisation",
        "privacy_classification",
        "secondary_verification",
        "other",
    ] = "other"
    model: str = "stub"
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usd: float = 0.0


class RetrievalObservation(BaseModel):
    """Stub retrieval hit list for recall@k."""

    query_id: str
    hits: list[str] = Field(default_factory=list)
    relevant_ids: list[str] = Field(default_factory=list)
    k: int = 5


class EvaluationObservations(BaseModel):
    """Everything the runner needs besides ground truth."""

    alerts: list[SurfacedAlert] = Field(default_factory=list)
    privacy_probes: list[PrivacyProbe] = Field(default_factory=list)
    memories: list[MemoryObservation] = Field(default_factory=list)
    cost_events: list[CostEvent] = Field(default_factory=list)
    retrieval: list[RetrievalObservation] = Field(default_factory=list)
    evaluated_at: datetime | None = None
    provider: str | None = None
    model: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    privacy_policy_version: str = "v1"
    git_commit: str | None = None
    # Optional D08e scale / fingerprint context (Demo Mode only).
    corpus_fingerprint: dict[str, Any] | None = None
    message_count: int | None = None
    background_count: int | None = None
    noise_count: int | None = None
    background_false_alerts: int | None = None
    noise_false_alerts: int | None = None
    remote_calls: int = 0
    index_size_bytes: int | None = None
    ingest_time_ms: float | None = None
    retrieval_latency_ms: float | None = None
    # Optional A-arm (spine-only) metrics for storyline recall under noise (§41).
    spine_metrics: dict[str, Any] | None = None

    @field_validator("evaluated_at", mode="before")
    @classmethod
    def _parse_evaluated_at(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
        return value


__all__ = [
    "CostEvent",
    "EvaluationObservations",
    "MemoryObservation",
    "PrivacyProbe",
    "RetrievalObservation",
    "SurfacedAlert",
]
