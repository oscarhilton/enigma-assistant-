"""Attention engine ranking — fixture scenarios and kind ordering."""

from __future__ import annotations

from personal_enigma.attention import (
    KIND_PRIORITY,
    AttentionEngine,
    AttentionItem,
    AttentionKind,
    HeuristicAttentionEngine,
    collect_attention_items,
)
from personal_enigma.domain import Obligation
from personal_enigma.fixtures import get_scenario, review_proposal_scenario


def test_heuristic_engine_satisfies_protocol() -> None:
    engine: AttentionEngine = HeuristicAttentionEngine(remote_llm_enabled=False)
    assert isinstance(engine, AttentionEngine)


def test_all_attention_kinds_distinguished() -> None:
    kinds = {
        AttentionKind.INFERRED_OBLIGATION,
        AttentionKind.EXPLICIT_REMINDER,
        AttentionKind.INFERRED_COMMITMENT,
        AttentionKind.CALENDAR_OBLIGATION,
    }
    assert kinds == set(AttentionKind)
    assert len(KIND_PRIORITY) == len(AttentionKind)
    assert (
        KIND_PRIORITY[AttentionKind.EXPLICIT_REMINDER]
        > KIND_PRIORITY[AttentionKind.INFERRED_COMMITMENT]
    )


def test_explicit_reminder_outranks_weak_inferred_commitment() -> None:
    """Reminders beat email inferences even when the inference has a high raw score."""
    engine = HeuristicAttentionEngine(remote_llm_enabled=False)
    weak = AttentionItem(
        title="Review proposal",
        body="Can you review before Monday?",
        kind=AttentionKind.INFERRED_COMMITMENT,
        score=999.0,
        evidence_ids=["msg_1"],
    )
    reminder = AttentionItem(
        title="Review proposal",
        body="Due Friday",
        kind=AttentionKind.EXPLICIT_REMINDER,
        score=0.0,
        evidence_ids=["rem_1"],
    )
    ranked = engine.rank([weak, reminder])
    assert ranked[0].kind == AttentionKind.EXPLICIT_REMINDER
    assert ranked[0].evidence_ids == ["rem_1"]
    assert ranked[1].kind == AttentionKind.INFERRED_COMMITMENT
    assert ranked[0].score > ranked[1].score


def test_kind_ordering_calendar_above_inferred_obligation() -> None:
    engine = HeuristicAttentionEngine()
    items = [
        AttentionItem(
            title="Draft notes",
            body="",
            kind=AttentionKind.INFERRED_OBLIGATION,
            score=10.0,
        ),
        AttentionItem(
            title="Proposal review",
            body="",
            kind=AttentionKind.CALENDAR_OBLIGATION,
            score=0.0,
        ),
        AttentionItem(
            title="Loose email ask",
            body="",
            kind=AttentionKind.INFERRED_COMMITMENT,
            score=50.0,
        ),
    ]
    ranked = engine.rank(items)
    assert [i.kind for i in ranked] == [
        AttentionKind.CALENDAR_OBLIGATION,
        AttentionKind.INFERRED_OBLIGATION,
        AttentionKind.INFERRED_COMMITMENT,
    ]


def test_review_proposal_scenario_top_is_explicit_reminder() -> None:
    pack = review_proposal_scenario()
    engine = HeuristicAttentionEngine(remote_llm_enabled=False)
    items = collect_attention_items(
        reminders=pack.reminders,
        messages=pack.messages,
        calendar_events=pack.calendar_events,
    )
    ranked = engine.rank(items)

    assert ranked, "expected attention items from review_proposal scenario"
    top = ranked[0]
    assert top.kind == AttentionKind.EXPLICIT_REMINDER
    assert top.title == "Review proposal"
    assert "rem_review_proposal" in top.evidence_ids

    kinds_present = {item.kind for item in ranked}
    assert AttentionKind.EXPLICIT_REMINDER in kinds_present
    assert AttentionKind.INFERRED_COMMITMENT in kinds_present
    assert AttentionKind.CALENDAR_OBLIGATION in kinds_present


def test_review_proposal_via_registry_includes_inferred_obligation() -> None:
    pack = get_scenario("review_proposal")
    assert pack.expected_obligation is not None
    engine = HeuristicAttentionEngine()
    items = collect_attention_items(
        reminders=pack.reminders,
        messages=pack.messages,
        calendar_events=pack.calendar_events,
        obligations=(pack.expected_obligation,),
    )
    ranked = engine.rank(items)
    kinds = [item.kind for item in ranked]
    assert AttentionKind.INFERRED_OBLIGATION in kinds
    assert kinds[0] == AttentionKind.EXPLICIT_REMINDER


def test_works_with_remote_llm_disabled() -> None:
    engine = HeuristicAttentionEngine(remote_llm_enabled=False)
    assert engine.remote_llm_enabled is False
    obligation = Obligation(description="Pay invoice", confidence=0.4)
    items = collect_attention_items(obligations=(obligation,))
    ranked = engine.rank(items)
    assert len(ranked) == 1
    assert ranked[0].kind == AttentionKind.INFERRED_OBLIGATION
