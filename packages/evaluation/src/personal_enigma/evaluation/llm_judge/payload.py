"""Frozen candidate + evidence payloads for Judge checkpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from personal_enigma.transformation import TransformedContext


class EvidenceItem(BaseModel):
    """Sanitised evidence row referenced by id from judgements."""

    evidence_id: str
    summary: str
    entities: list[str] = Field(default_factory=list)
    source_type: str = ""


class JudgeCandidate(BaseModel):
    """One open-loop / candidate the local filter already selected."""

    candidate_id: str
    title: str
    evidence_ids: list[str] = Field(default_factory=list)
    due_at: str | None = None
    local_rank: int | None = None


class JudgeCheckpointRequest(BaseModel):
    """Whole-checkpoint Judge request (e.g. Wed 21 Jan noon).

    Remote-safe: built from TransformedContext / PERSON_* only when transmitted.
    """

    checkpoint_id: str
    clock: str
    scenario: str = "alex-v1"
    candidates: list[JudgeCandidate] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    # Optional sanitised context bundle for PAYG transport (replay / live).
    context: TransformedContext | None = None

    def evidence_id_set(self) -> set[str]:
        return {item.evidence_id for item in self.evidence}

    def candidate_id_set(self) -> set[str]:
        return {item.candidate_id for item in self.candidates}


__all__ = [
    "EvidenceItem",
    "JudgeCandidate",
    "JudgeCheckpointRequest",
]
