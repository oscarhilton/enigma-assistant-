"""Demo API projection — maps simulation checkpoints to AttentionState without evaluation."""

from __future__ import annotations

from typing import Any

from personal_enigma.attention.projection import (
    AttentionItemView,
    AttentionState,
    ProjectionArtifacts,
    QualificationDebug,
    project_attention_state,
)
from personal_enigma.fixtures.demo_checkpoints import (
    load_checkpoint_snapshot,
    load_semantic_inputs,
)


def project_checkpoint(checkpoint_id: str) -> ProjectionArtifacts:
    snapshot = load_checkpoint_snapshot(checkpoint_id)
    semantics = load_semantic_inputs(checkpoint_id)
    return project_attention_state(snapshot, semantics)


def attention_state_payload(checkpoint_id: str) -> dict[str, Any]:
    return project_checkpoint(checkpoint_id).state.model_dump(mode="json")


def qualification_debug_payload(checkpoint_id: str, item_id: str) -> QualificationDebug:
    artifacts = project_checkpoint(checkpoint_id)
    debug = artifacts.debug_by_id.get(item_id)
    if debug is None:
        raise KeyError(item_id)
    return debug


def legacy_attention_items(state: AttentionState) -> list[dict[str, Any]]:
    """Map projection to legacy D10 dashboard shape (needs_you only)."""

    def _row(item: AttentionItemView, index: int) -> dict[str, Any]:
        return {
            "id": item.id,
            "title": item.title,
            "when": None,
            "why_now_glance": item.explanation,
            "body": item.explanation,
            "kind": "commitment",
            "priority": max(1, 5 - index),
            "confidence": item.actionability_now or 0.7,
            "attention_rank": item.composite_score or 0.0,
            "evidence_ids": item.evidence_ids,
            "qualification": "needs_you",
            "policy_decision": item.policy_decision,
        }

    return [_row(item, index) for index, item in enumerate(state.needs_you)]


__all__ = [
    "attention_state_payload",
    "legacy_attention_items",
    "project_checkpoint",
    "qualification_debug_payload",
]
