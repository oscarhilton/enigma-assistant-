"""C25 evidence bundle tests."""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.api.context_compilation import interpret_request
from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.evidence_bundle import (
    build_evidence_bundle,
    derive_courier_state,
    planned_tools_for_kind,
)


@dataclass
class _SessionStub:
    context: ConversationContext
    state: object = None


def _session() -> _SessionStub:
    return _SessionStub(context=ConversationContext())


def test_planned_tools_for_catch_up() -> None:
    tools = planned_tools_for_kind("catch_up")
    assert "attention.get_current" in tools
    assert "world.get_changes" in tools
    assert "agenda.get" in tools


def test_calendar_only_fetch_marks_coverage_inadequate_for_catch_up() -> None:
    bundle = build_evidence_bundle(
        question="what have i missed?",
        working_set={
            "request_kind": "catch_up",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("catch_up")},
            "capability_contract": {"allowed": ["agenda.get"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "agenda.get",
                "ok": True,
                "data": {"period": "today", "empty_horizon": True, "calendar_evidence_ids": []},
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert bundle.coverage_adequate is False
    assert "attention" in bundle.unsearched_sources
    assert derive_courier_state(bundle) == "partially_returned"
    assert any(
        assertion.subject == "calendar"
        and assertion.predicate == "has_items"
        and assertion.value is False
        for assertion in bundle.grounded_assertions
    )
    assert any(unknown.reason == "missing_evidence" for unknown in bundle.unknowns)
    assert any(challenge.disposition == "qualifies" for challenge in bundle.challenges)


def test_what_should_i_be_doing_compiles_next_work() -> None:
    session = _session()
    interp = interpret_request("what should i be doing?", session)
    assert interp.request_kind == "next_work"
    assert interp.authority == "READ"


def test_catch_up_compiles_private_world() -> None:
    session = _session()
    interp = interpret_request("what have i missed?", session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.request_kind == "catch_up"


def test_brunch_compiles_subject_details_with_personal_scope() -> None:
    session = _session()
    interp = interpret_request("what about the brunch", session)
    assert interp.request_kind == "subject_details"
    assert interp.constraints.scope == "personal"


def test_news_question_marks_blocked_bundle() -> None:
    bundle = build_evidence_bundle(
        question="the news?",
        working_set={
            "request_kind": None,
            "authority": "NONE",
            "capability_contract": {
                "allowed": [],
                "unavailable": ["arbitrary network"],
            },
        },
        tool_results=[],
        evidence_domain="GENERAL_KNOWLEDGE",
        authority="NONE",
    )
    assert "news" in bundle.unavailable_sources
    assert derive_courier_state(bundle) == "blocked"
    assert any(unknown.reason == "unavailable_capability" for unknown in bundle.unknowns)


def test_brunch_unresolved_when_no_subject() -> None:
    bundle = build_evidence_bundle(
        question="what about the brunch",
        working_set={
            "request_kind": "subject_details",
            "scope": "personal",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("subject_details")},
            "capability_contract": {"allowed": ["world.explain"], "unavailable": []},
        },
        tool_results=[],
        current_subject_id=None,
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert "brunch" in bundle.unresolved_referents
    assert derive_courier_state(bundle) == "confused"
    assert any(unknown.reason == "unresolved_referent" for unknown in bundle.unknowns)


def test_attention_tool_produces_grounded_assertion() -> None:
    bundle = build_evidence_bundle(
        question="what should i be doing?",
        working_set={
            "request_kind": "next_work",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("next_work")},
            "capability_contract": {"allowed": ["attention.get_current"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "attention.get_current",
                "ok": True,
                "data": {"needs_you_count": 2, "evidence_ids": ["need_1", "need_2"]},
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert any(
        assertion.subject == "attention"
        and assertion.predicate == "needs_you_count"
        and assertion.value == 2
        for assertion in bundle.grounded_assertions
    )
