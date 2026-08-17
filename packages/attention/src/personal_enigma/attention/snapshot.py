"""Production-shaped checkpoint snapshot types for attention projection.

Duplicated from evaluation observations so runtime (Demo API, simulation) never
depends on ``packages/evaluation``. Evaluation may import these for parity.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class AttentionCandidateSnapshot(BaseModel):
    id: str
    title: str = ""
    kind: str = ""
    score: float = 0.0
    obligation_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    suppressed: bool = False
    suppress_reason: str | None = None


class NextActionSnapshot(BaseModel):
    title: str
    action_id: str | None = None
    estimated_minutes: int | None = None
    effort: str | None = None
    why_this_now: str | None = None


class MemoryStateSnapshot(BaseModel):
    at: datetime | None = None
    memory_ids: list[str] = Field(default_factory=list)
    texts: list[str] = Field(default_factory=list)
    open_obligation_ids: list[str] = Field(default_factory=list)


class CheckpointSnapshot(BaseModel):
    checkpoint_id: str
    at: datetime
    scenario: str = "alex-v1"
    scenario_version: str = "0.2.1"
    candidate_set: list[AttentionCandidateSnapshot] = Field(default_factory=list)
    suppressed_candidates: list[AttentionCandidateSnapshot] = Field(default_factory=list)
    next_action: NextActionSnapshot | None = None
    memory_state: MemoryStateSnapshot | None = None

    @field_validator("at", mode="before")
    @classmethod
    def _parse_at(cls, value: object) -> object:
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
    "AttentionCandidateSnapshot",
    "CheckpointSnapshot",
    "MemoryStateSnapshot",
    "NextActionSnapshot",
]
