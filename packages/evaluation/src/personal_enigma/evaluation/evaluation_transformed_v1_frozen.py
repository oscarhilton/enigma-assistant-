"""FROZEN evaluation_transformed_v1 stub — historical live-gate representation.

DO NOT EDIT after R-L09 step-5 freeze (2026-08-17). Preserves the confound we are
testing against: raw titles, shallow WAITING_ON only, no causal BLOCKED_BY graph.

Used only for three-column ablation (v1 vs v2 vs full_synthetic).
"""

from __future__ import annotations

from personal_enigma.evaluation.observations import CheckpointSnapshot
from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.relations import SemanticRelation


def snapshot_to_evaluation_transformed_v1_frozen(
    snapshot: CheckpointSnapshot,
) -> TransformedContext:
    candidates = snapshot.candidate_set[:5]
    parts = [f"Checkpoint {snapshot.checkpoint_id} at {snapshot.at.isoformat()}"]
    for cand in candidates:
        parts.append(f"Candidate {cand.id}: {cand.title} score={cand.score:.2f}")
    entities = [
        f"OBLIGATION_{oid.replace('obligation_', '').upper()}"
        for cand in candidates
        for oid in cand.obligation_ids
    ]
    relations: list[SemanticRelation] = []
    for cand in candidates:
        for oid in cand.obligation_ids:
            task = f"TASK_{oid.replace('obligation_', '').upper()}"
            rem_ids = [eid for eid in cand.evidence_ids if eid.startswith("rem-")]
            if rem_ids:
                relations.append(
                    SemanticRelation(
                        type="WAITING_ON",
                        subject=task,
                        object=f"EVIDENCE_{rem_ids[0].upper().replace('-', '_')}",
                        state="open",
                        causal="open_reminder_without_resolution_resource",
                    )
                )
    return TransformedContext(
        summary=" | ".join(parts),
        entities=sorted(set(entities)),
        relations=relations,
        metadata={
            "source_type": "evaluation_checkpoint",
            "context_mode": "evaluation_transformed_v1",
            "checkpoint_id": snapshot.checkpoint_id,
            "record_id": snapshot.checkpoint_id,
            "frozen": True,
        },
        may_transmit_remotely=True,
    )


__all__ = ["snapshot_to_evaluation_transformed_v1_frozen"]
