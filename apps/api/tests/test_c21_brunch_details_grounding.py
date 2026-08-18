"""C21 — brunch details grounding fence (fail closed on wrong compile)."""

from __future__ import annotations

from personal_enigma.api.context_compilation import (
    CompiledRemoteContext,
    build_compiled_turn_manifest,
)
from personal_enigma.api.conversation_context import (
    ConversationContext,
    DialogueTurn,
    remember_turn_local_constraint,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import _ordinary_conversation_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession
from personal_enigma.api.respond_grounding import (
    apply_respond_grounding_fence,
    seek_source_evidence_covered,
    violates_replace_conversational_choice,
)

BRUNCH_ID = "item-obligation_brunch_book"
JAN19 = "cp-2026-01-19T10:00"

_FABRICATED_RESPONSE = (
    "Here are the details for the Saturday brunch:\n\n"
    "**Restaurant**\n"
    "- **Name:** The Riverside Brunch Club\n"
    "- **Address:** 12 Baker Street, London W1U 6RR\n"
    "- **Phone:** +44 20 7945 1234\n\n"
    "**Reservation**\n"
    "- **Time:** 11:30 am\n"
    "- **Party size:** 4 guests\n\n"
    "**Pricing (per adult)**\n"
    "- Brunch buffet: **£38.00**\n\n"
    "**Next step:** Shall I go ahead and confirm the reservation?"
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


def _seed_brunch_dialogue(session: DemoToolSession) -> None:
    ctx = session.context
    ctx.current_subject_id = BRUNCH_ID
    ctx.current_subject_kind = "attention_item"
    remember_turn_local_constraint(
        ctx, key="location", value="london", applies_to=BRUNCH_ID
    )
    for role, act, text in (
        ("user", "ordinary_conversation", "london"),
        ("user", "ordinary_conversation", "maybe its not in the email... I guess 10am?"),
        ("user", "ordinary_conversation", "will be 4 of us"),
        ("assistant", "answer", "Sunny Side Café, Bistro Brunch, or Garden Terrace"),
        ("user", "ordinary_conversation", "Bistro Brunch!"),
    ):
        ctx.remember_dialogue_turn(
            DialogueTurn(role=role, text=text, act=act, subject_id=BRUNCH_ID)
        )


def _conversation_only_compiled() -> CompiledRemoteContext:
    manifest = build_compiled_turn_manifest(
        profile="CONVERSATION",
        speech_act="QUESTION",
        earned_providers=[],
        used_providers=[],
        tool_names=[],
    )
    return CompiledRemoteContext(
        profile="CONVERSATION",
        speech_act="QUESTION",
        system_prompt="",
        context_summary={},
        tools=[],
        working_set={},
        providers_used=(),
        manifest=manifest,
        evidence_domain="CONVERSATION_ONLY",
        authority="NONE",
    )


def test_fabricated_response_triggers_replacement_detection() -> None:
    session = _tool_session()
    _seed_brunch_dialogue(session)
    assert violates_replace_conversational_choice(
        _FABRICATED_RESPONSE, session.context
    )


def test_grounding_fence_replaces_fabricated_brochure() -> None:
    session = _tool_session()
    _seed_brunch_dialogue(session)
    fenced = apply_respond_grounding_fence(
        _FABRICATED_RESPONSE,
        context=session.context,
        evidence_domain="CONVERSATION_ONLY",
        authority="NONE",
    )
    assert "Riverside" not in fenced
    assert "£38" not in fenced
    assert "Baker Street" not in fenced
    assert seek_source_evidence_covered(fenced)
    assert "Bistro Brunch" in fenced or "our conversation" in fenced.casefold()


def test_orchestrator_ordinary_turn_applies_fence() -> None:
    session = _tool_session()
    _seed_brunch_dialogue(session)
    compiled = _conversation_only_compiled()
    turn_items = _ordinary_conversation_turn(
        session.at,
        _FABRICATED_RESPONSE,
        session=session,
        compiled=compiled,
    )
    text = turn_items[0]["text"]
    assert "Riverside" not in text
    assert seek_source_evidence_covered(text)


def test_hedged_recall_of_bistro_brunch_allowed() -> None:
    session = _tool_session()
    _seed_brunch_dialogue(session)
    hedged = (
        "From our conversation: London, ~10:00 am, 4 guests, Bistro Brunch. "
        "I don't have verified commercial details yet — I'll check the supporting email."
    )
    fenced = apply_respond_grounding_fence(
        hedged,
        context=session.context,
        evidence_domain="CONVERSATION_ONLY",
        authority="NONE",
    )
    assert fenced == hedged
