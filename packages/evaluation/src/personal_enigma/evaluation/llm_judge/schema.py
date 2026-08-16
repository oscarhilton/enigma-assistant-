"""Structured LLM Judge schema — no chain-of-thought (ADR-011)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class JudgementKind(StrEnum):
    OBLIGATION = "obligation"
    PENDING_REPLY = "pending_reply"
    SITUATIONAL = "situational"
    NOISE = "noise"


class JudgementStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    STALE = "stale"
    UNKNOWN = "unknown"


class JudgementImportance(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class JudgementAttention(StrEnum):
    MUST_SURFACE = "must_surface"
    MAY_SURFACE = "may_surface"
    SUPPRESS = "suppress"


class JudgementTiming(StrEnum):
    NOW = "now"
    SOON = "soon"
    LATER = "later"
    TOO_LATE = "too_late"
    NA = "n/a"


class StructuredJudgement(BaseModel):
    """One candidate judgement. Prose / CoT fields are intentionally absent."""

    candidate_id: str
    kind: JudgementKind
    status: JudgementStatus
    importance: JudgementImportance
    attention: JudgementAttention
    timing: JudgementTiming
    confidence: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("reason_codes")
    @classmethod
    def _reason_codes_are_tokens(cls, value: list[str]) -> list[str]:
        for code in value:
            if not code or any(ch.isspace() for ch in code):
                raise ValueError(f"reason_codes must be compact tokens, got {code!r}")
            if len(code) > 64:
                raise ValueError(f"reason_code too long: {code!r}")
        return value


class JudgeResponse(BaseModel):
    """Batch of structured judgements for one checkpoint."""

    judgements: list[StructuredJudgement] = Field(default_factory=list)
    model: str = "judge-fixture"
    schema_version: str = "1"


__all__ = [
    "JudgeResponse",
    "JudgementAttention",
    "JudgementImportance",
    "JudgementKind",
    "JudgementStatus",
    "JudgementTiming",
    "StructuredJudgement",
]
