"""C15 — resolved private subject + attribute request → PRIVATE_QUERY + READ."""

from __future__ import annotations

from personal_enigma.api.context_compilation import compile_remote_context, interpret_request
from personal_enigma.api.conversation_context import (
    ConversationContext,
    DialogueTurn,
    remember_turn_local_constraint,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession
from personal_enigma.api.speech_acts import classify_speech_act

BRUNCH_ID = "item-obligation_brunch_book"
JAN19 = "cp-2026-01-19T10:00"
_GATE_UTTERANCE = "I would like details about the brunch please"
_PRIVATE_TOOLS = frozenset(
    {
        "attention.get_current",
        "next_action.get",
        "agenda.get",
        "source.recent",
        "world.explain",
    }
)


def _tool_session() -> DemoToolSession:
    state = project_checkpoint(JAN19).state
    return DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )


def _seed_brunch_arc(session: DemoToolSession) -> None:
    """Dialogue + constraints from dump turns 28–41 (compact)."""
    ctx = session.context
    ctx.current_subject_id = BRUNCH_ID
    ctx.current_subject_kind = "attention_item"
    ctx.temporal_constraint = "this_weekend"
    remember_turn_local_constraint(
        ctx, key="location", value="london", applies_to=BRUNCH_ID
    )
    turns = [
        ("user", "question", "london"),
        ("user", "ordinary_conversation", "will be 4 of us"),
        ("user", "ordinary_conversation", "go for it!"),
        ("assistant", "answer", "Sunny Side Café, Bistro Brunch, or Garden Terrace"),
        ("user", "ordinary_conversation", "Bistro Brunch!"),
    ]
    for role, act, text in turns:
        ctx.remember_dialogue_turn(
            DialogueTurn(role=role, text=text, act=act, subject_id=BRUNCH_ID)
        )
    ctx.set_pending_confirmation("SHOW_CONFIRMATION", BRUNCH_ID)


def test_attribute_request_classifies_as_question() -> None:
    assert classify_speech_act(_GATE_UTTERANCE) == "QUESTION"


def test_brunch_details_compiles_private_query_with_tools() -> None:
    session = _tool_session()
    _seed_brunch_arc(session)
    compiled = compile_remote_context(_GATE_UTTERANCE, session)
    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert compiled.evidence_domain != "CONVERSATION_ONLY"
    assert compiled.authority != "NONE"
    assert compiled.tool_names
    assert _PRIVATE_TOOLS & set(compiled.tool_names)
    assert compiled.working_set.get("request_kind") == "subject_details"
    assert "world.explain" in compiled.tool_names or "source.recent" in compiled.tool_names
    contract = compiled.working_set.get("capability_contract") or {}
    assert "reservation.confirm" in contract.get("unavailable", [])
    assert "reservation.book" in contract.get("unavailable", [])


def test_brunch_details_interpret_request_axes() -> None:
    session = _tool_session()
    _seed_brunch_arc(session)
    interp = interpret_request(_GATE_UTTERANCE, session)
    assert interp.profile == "PRIVATE_QUERY"
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.authority == "READ"
    assert interp.request_kind == "subject_details"


def test_thanks_with_brunch_subject_stays_conversation() -> None:
    session = _tool_session()
    _seed_brunch_arc(session)
    compiled = compile_remote_context("thanks", session)
    assert compiled.evidence_domain == "CONVERSATION_ONLY"
    assert compiled.authority == "NONE"
    assert compiled.tool_names == []
