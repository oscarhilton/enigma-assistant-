"""Build remote-safe attention context from checkpoint candidates (R-L09)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from personal_enigma.identity import EntityResolver
from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.relation_inference import infer_relations_from_evidence
from personal_enigma.transformation.relations import SemanticRelation, merge_relations
from personal_enigma.transformation.title_sanitisation import (
    assert_no_raw_identity_in_text,
    pseudonymise_remote_text,
)


@dataclass(frozen=True, slots=True)
class AttentionCandidateInput:
    id: str
    title: str
    obligation_ids: list[str]
    evidence_ids: list[str]
    score: float


def build_remote_attention_context(
    *,
    checkpoint_id: str,
    checkpoint_at: datetime,
    candidates: list[AttentionCandidateInput],
    resolver: EntityResolver | None = None,
    context_mode: str = "production",
    may_transmit_remotely: bool = True,
) -> TransformedContext:
    """Shared production + evaluation path: relations[] + pseudonymised titles."""
    entities: list[str] = []
    parts = [f"Checkpoint {checkpoint_id} at {checkpoint_at.isoformat()}"]
    relation_groups: list[list[SemanticRelation]] = []

    for cand in candidates[:5]:
        safe_title = pseudonymise_remote_text(
            cand.title, resolver=resolver, entities=entities
        )
        assert_no_raw_identity_in_text(safe_title)
        parts.append(f"Candidate {cand.id}: {safe_title} score={cand.score:.2f}")
        for oid in cand.obligation_ids:
            token = f"OBLIGATION_{oid.removeprefix('obligation_').upper()}"
            if token not in entities:
                entities.append(token)
        for oid in cand.obligation_ids:
            relation_groups.append(
                infer_relations_from_evidence(
                    obligation_id=oid,
                    evidence_ids=list(cand.evidence_ids),
                    checkpoint_at=checkpoint_at,
                )
            )

    relations = merge_relations(*relation_groups) if relation_groups else []

    summary = " | ".join(parts)
    assert_no_raw_identity_in_text(summary)

    return TransformedContext(
        summary=summary,
        entities=sorted(set(entities)),
        relations=relations,
        metadata={
            "source_type": "attention_checkpoint",
            "context_mode": context_mode,
            "checkpoint_id": checkpoint_id,
            "record_id": checkpoint_id,
        },
        may_transmit_remotely=may_transmit_remotely,
    )


def candidate_input_from_observation(candidate: Any) -> AttentionCandidateInput:
    return AttentionCandidateInput(
        id=str(candidate.id),
        title=str(candidate.title),
        obligation_ids=list(candidate.obligation_ids),
        evidence_ids=list(candidate.evidence_ids),
        score=float(candidate.score),
    )


__all__ = [
    "AttentionCandidateInput",
    "build_remote_attention_context",
    "candidate_input_from_observation",
]
