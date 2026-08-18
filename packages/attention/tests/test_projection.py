"""Attention projection — Jan 19/20 milestone semantics (R-L10)."""

from __future__ import annotations

from personal_enigma.attention.projection import project_attention_state
from personal_enigma.fixtures.demo_checkpoints import (
    ALEX_V1_MILESTONE_CHECKPOINTS,
    load_checkpoint_snapshot,
    load_semantic_inputs,
)


def _project(checkpoint_id: str):
    snapshot = load_checkpoint_snapshot(checkpoint_id)
    semantics = load_semantic_inputs(checkpoint_id)
    return project_attention_state(snapshot, semantics)


def test_jan19_token_in_context_not_needs_you() -> None:
    state = _project("cp-2026-01-19T10:00").state
    ids_needs = {row.id for row in state.needs_you}
    ids_context = {row.id for row in state.context}
    assert "item-obligation_token_audit" not in ids_needs
    assert "item-obligation_token_audit" in ids_context
    assert state.presentation.proactive_silence is True
    assert state.next_actions
    assert state.next_actions[0].source_candidate_id == "item-obligation_token_audit"
    assert state.next_actions[0].reason == "Unblocked now"


def test_jan20_brunch_needs_you_token_context() -> None:
    state = _project("cp-2026-01-20T11:00").state
    ids_needs = {row.id for row in state.needs_you}
    ids_context = {row.id for row in state.context}
    assert "item-obligation_brunch_book" in ids_needs
    assert "item-obligation_token_audit" in ids_context
    assert "item-obligation_token_audit" not in ids_needs
    assert state.presentation.chat_opening_count == 1
    assert state.presentation.proactive_silence is False


def test_context_and_next_actions_are_separate_buckets() -> None:
    for checkpoint_id in ALEX_V1_MILESTONE_CHECKPOINTS:
        state = _project(checkpoint_id).state
        context_ids = {row.id for row in state.context}
        next_source_ids = {
            row.source_candidate_id for row in state.next_actions if row.source_candidate_id
        }
        assert context_ids.isdisjoint({row.id for row in state.needs_you})
        if next_source_ids:
            assert next_source_ids.issubset(context_ids)
