"""C15 — semantic bootstrap interprets language; the compiler grants context."""

from __future__ import annotations

import json
from typing import Any

from personal_enigma.api.context_compilation import (
    compile_remote_context,
    interpret_request,
    tools_for_interpretation,
)
from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, ToolName, execute_tool
from personal_enigma.api.semantic_bootstrap import (
    FixtureSemanticBootstrap,
    SemanticInterpretation,
    build_bootstrap_payload,
    build_bootstrap_remote_context,
    build_bootstrap_transformed_context,
    compile_with_bootstrap,
    merge_request_interpretation,
)
from personal_enigma.privacy.egress.assert_remote_safe import assert_remote_safe

JAN19 = "cp-2026-01-19T10:00"
_PRIVATE_MARKERS = ("elena", "atlas", "brunch", "token inventory")
_FIXTURE = FixtureSemanticBootstrap()


class _ScriptedLLM:
    def __init__(self, script: dict[str, list[ToolCallRecord]]) -> None:
        self._script = script

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del context_summary, tools, correlation_id
        return [call.model_copy(deep=True) for call in self._script.get(user_message, [])]


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


def _run(
    session: DemoToolSession,
    utterance: str,
    tools: list[ToolName],
    *,
    bootstrap: FixtureSemanticBootstrap | None = _FIXTURE,
) -> Any:
    script = {utterance: [ToolCallRecord(name=name) for name in tools]}
    return run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM(script),
        bootstrap=bootstrap,
    )


def test_deterministic_baseline_unchanged_for_elliptical_private() -> None:
    """interpret_request stays the compiler baseline — not a new phrasebook."""
    session = _tool_session()
    coming = interpret_request("anything coming up?", session)
    assert coming.evidence_domain == "GENERAL_KNOWLEDGE"
    assert coming.capability_families == ()
    compiled = compile_remote_context("anything coming up?", session)
    assert compiled.evidence_domain == "GENERAL_KNOWLEDGE"
    assert compiled.tool_names == []


def test_anything_coming_up_via_semantic_survives_compiler() -> None:
    session = _tool_session()
    compiled = compile_with_bootstrap("anything coming up?", session, _FIXTURE)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert "agenda" in compiled.capability_families
    assert "agenda.get" in compiled.tool_names
    assert "assist.approve" not in compiled.tool_names


def test_sky_and_rain_are_not_over_privatized() -> None:
    session = _tool_session()
    for utterance in ("Why is the sky blue?", "why is rain wet?"):
        compiled = compile_with_bootstrap(utterance, session, _FIXTURE)
        assert compiled.evidence_domain == "GENERAL_KNOWLEDGE", utterance
        assert compiled.authority == "NONE", utterance
        assert compiled.tool_names == []
        assert compiled.providers_used == ()
        for module, decision in compiled.manifest.context.items():
            assert decision.include is False, f"{utterance}: {module}"


def test_rogue_semantic_cannot_privatize_generic_knowledge() -> None:
    session = _tool_session()
    det = interpret_request("Why is the sky blue?", session)
    rogue = SemanticInterpretation(
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
        candidate_families=("agenda",),
        confidence=0.99,
    )
    merged = merge_request_interpretation("Why is the sky blue?", det, rogue, None)
    assert merged.evidence_domain == "GENERAL_KNOWLEDGE"
    assert merged.capability_families == ()
    compiled = compile_remote_context(
        "Why is the sky blue?", session, interpretation=merged
    )
    assert compiled.tool_names == []


def test_week_then_work_inherits_capsule_without_compiler_phrase_family() -> None:
    session = _tool_session()
    _run(session, "What's on this week?", ["agenda.get"])
    capsule = session.context.live_capsule()
    assert capsule is not None
    assert capsule.temporal_constraint == "this_week"

    det_work = interpret_request("what about work?", session)
    assert det_work.constraints.scope is None

    work = compile_with_bootstrap("what about work?", session, _FIXTURE)
    assert work.evidence_domain == "PRIVATE_WORLD"
    assert work.authority == "READ"
    assert work.working_set["temporal_constraint"] == "this_week"
    assert work.working_set["scope"] == "work"
    assert "agenda.get" in work.tool_names


def test_elliptical_and_what_else_inherit_capsule_goal() -> None:
    session = _tool_session()
    _run(session, "What's on this week?", ["agenda.get"])
    frame = session.context.live_capsule()
    assert frame is not None
    assert frame.evidence_domain == "PRIVATE_WORLD"
    assert frame.temporal_constraint == "this_week"

    for utterance in ("and?", "what else?"):
        compiled = compile_with_bootstrap(utterance, session, _FIXTURE)
        assert compiled.evidence_domain == "PRIVATE_WORLD", utterance
        assert compiled.authority == "READ", utterance
        assert "agenda" in compiled.capability_families, utterance
        assert compiled.working_set["temporal_constraint"] == "this_week", utterance
        assert "agenda.get" in compiled.tool_names, utterance


def test_semantic_approve_cannot_override_deterministic_support() -> None:
    session = _tool_session()
    execute_tool(session, "next_action.get", {})
    det = interpret_request("I need help with that", session)
    assert det.authority == "SUPPORT"
    semantic = SemanticInterpretation(
        evidence_domain="PRIVATE_WORLD",
        authority="APPROVE",
        candidate_families=("assist",),
        confidence=0.99,
    )
    merged = merge_request_interpretation(
        "I need help with that", det, semantic, session.context.live_capsule()
    )
    assert merged.authority == "SUPPORT"
    assert "assist.approve" not in tools_for_interpretation(merged)
    compiled = compile_remote_context(
        "I need help with that", session, interpretation=merged
    )
    assert compiled.authority == "SUPPORT"
    assert "assist.approve" not in compiled.tool_names
    assert "assist.propose" not in compiled.tool_names


def test_bootstrap_payload_contains_no_private_world() -> None:
    session = _tool_session()
    _run(session, "What's on this week?", ["agenda.get"])
    payload = build_bootstrap_payload("anything coming up?", session.context.live_capsule())
    assert set(payload) == {"utterance", "conversation"}
    conversation = payload["conversation"]
    assert set(conversation) <= {
        "active_goal",
        "temporal_frame",
        "scope",
        "source_scope",
        "unresolved_request",
    }
    blob = json.dumps(payload).casefold()
    for marker in _PRIVATE_MARKERS:
        assert marker not in blob, marker
    assert "needs_you" not in blob
    assert "attention_working_set" not in blob
    assert "last_outcome" not in blob

    safe = build_bootstrap_transformed_context(
        "anything coming up?", session.context.live_capsule()
    )
    assert_remote_safe(safe)
    remote = build_bootstrap_remote_context(
        "anything coming up?",
        session.context.live_capsule(),
        model="accounts/fireworks/models/gpt-oss-120b",
    )
    wire = json.dumps(remote.wire_body).casefold()
    for marker in _PRIVATE_MARKERS:
        assert marker not in wire, marker
    assert remote.transformation_profile == "semantic_bootstrap_v1"
    assert "tools" not in remote.wire_body


def test_external_world_stays_dormant() -> None:
    session = _tool_session()
    det = interpret_request("Why is the sky blue?", session)
    semantic = SemanticInterpretation(
        evidence_domain="EXTERNAL_WORLD",
        authority="READ",
        confidence=0.9,
    )
    merged = merge_request_interpretation("Why is the sky blue?", det, semantic, None)
    assert merged.evidence_domain == "GENERAL_KNOWLEDGE"
    assert merged.capability_families == ()


def test_capsule_updates_after_orchestrator_turn() -> None:
    session = _tool_session()
    _run(session, "What's on this week?", ["agenda.get"])
    capsule = session.context.live_capsule()
    assert capsule is not None
    assert capsule.evidence_domain == "PRIVATE_WORLD"
    assert capsule.temporal_constraint == "this_week"

    _run(session, "what about work?", ["agenda.get"])
    follow = session.context.live_capsule()
    assert follow is not None
    assert follow.temporal_constraint == "this_week"
    assert follow.scope == "work"


_FRESH_WORLD_TOOLS = frozenset(
    {
        "agenda.get",
        "attention.get_current",
        "next_action.get",
        "next_action.get_alternatives",
        "source.recent",
        "source.quote",
    }
)


def test_adr031_five_step_falsification_sequence() -> None:
    """Hierarchy: baseline → capsule → bootstrap → compiler → world.

    Bootstrap is not required for the obvious today query. After sky-blue
    clears the frame, only semantic bootstrap recovers PRIVATE_WORLD.
    interpret_request stays the GENERAL_KNOWLEDGE baseline — not a phrasebook.
    """
    session = _tool_session()

    today = "what's on today?"
    det_today = interpret_request(today, session)
    assert det_today.evidence_domain == "PRIVATE_WORLD"
    assert det_today.authority == "READ"
    assert "agenda" in det_today.capability_families
    compiled_today = compile_remote_context(today, session)
    assert compiled_today.evidence_domain == "PRIVATE_WORLD"
    assert "agenda.get" in compiled_today.tool_names
    boot_today = compile_with_bootstrap(today, session, _FIXTURE)
    assert boot_today.authority == "READ"
    assert boot_today.authority != "APPROVE"
    assert "assist.approve" not in boot_today.tool_names
    _run(session, today, ["agenda.get"], bootstrap=None)
    frame = session.context.live_capsule()
    assert frame is not None
    assert frame.evidence_domain == "PRIVATE_WORLD"
    assert frame.temporal_constraint == "today"

    free = "what should I do with this free time?"
    det_free = interpret_request(free, session)
    assert det_free.evidence_domain == "PRIVATE_WORLD"
    assert det_free.frame_inherited is True
    assert det_free.request_kind == "next_work"
    assert det_free.authority in {"READ", "SUPPORT"}
    assert det_free.authority != "APPROVE"
    compiled_free = compile_with_bootstrap(free, session, _FIXTURE)
    assert compiled_free.working_set["temporal_constraint"] == "today"
    assert "attention.get_current" in compiled_free.tool_names or (
        "next_action.get" in compiled_free.tool_names
    )
    assert "assist.approve" not in compiled_free.tool_names
    _run(session, free, ["next_action.get"], bootstrap=None)

    else_utt = "anything else?"
    det_else = interpret_request(else_utt, session)
    assert det_else.evidence_domain == "PRIVATE_WORLD"
    assert det_else.frame_inherited is True
    compiled_else = compile_with_bootstrap(else_utt, session, _FIXTURE)
    assert compiled_else.evidence_domain == "PRIVATE_WORLD"
    assert compiled_else.authority == "READ"
    assert compiled_else.working_set["temporal_constraint"] == "today"
    assert compiled_else.tool_names
    _run(session, else_utt, ["agenda.get"])

    sky = "why is the sky blue?"
    compiled_sky = compile_with_bootstrap(sky, session, _FIXTURE)
    assert compiled_sky.evidence_domain == "GENERAL_KNOWLEDGE"
    assert compiled_sky.tool_names == []
    _run(session, sky, [])
    assert session.context.live_capsule() is None

    coming = "anything coming up?"
    det_coming = interpret_request(coming, session)
    assert det_coming.evidence_domain == "GENERAL_KNOWLEDGE"
    assert det_coming.capability_families == ()
    without = compile_remote_context(coming, session)
    assert without.evidence_domain == "GENERAL_KNOWLEDGE"
    assert without.tool_names == []
    recovered = compile_with_bootstrap(coming, session, _FIXTURE)
    assert recovered.evidence_domain == "PRIVATE_WORLD"
    assert recovered.authority == "READ"
    assert recovered.authority != "SUPPORT"
    assert recovered.authority != "APPROVE"
    assert "agenda" in recovered.capability_families
    assert "agenda.get" in recovered.tool_names
    assert "assist.approve" not in recovered.tool_names


def test_bootstrap_may_not_improve_its_own_authority() -> None:
    """Comprehension may add PRIVATE_WORLD. Authority still re-earns as READ."""
    session = _tool_session()
    det = interpret_request("anything coming up?", session)
    assert det.evidence_domain == "GENERAL_KNOWLEDGE"
    assert det.authority == "NONE"
    rogue = SemanticInterpretation(
        evidence_domain="PRIVATE_WORLD",
        authority="APPROVE",
        candidate_families=("agenda", "assist"),
        confidence=0.99,
    )
    merged = merge_request_interpretation("anything coming up?", det, rogue, None)
    assert merged.evidence_domain == "PRIVATE_WORLD"
    assert merged.authority == "READ"
    assert "assist.approve" not in tools_for_interpretation(merged)
    assert "assist.propose" not in tools_for_interpretation(merged)


def test_mail_and_bootstrap_preserves_private_world_and_requires_fresh_tool() -> None:
    """Unresolved mail goal continues. Stale source.recent is not world truth."""
    session = _tool_session()
    mail = "look at my mail and tell me what's important"
    turn = _run(session, mail, ["source.recent"])
    assert turn.tool_calls[0].name == "source.recent"
    capsule = session.context.live_capsule()
    assert capsule is not None
    assert capsule.evidence_domain == "PRIVATE_WORLD"
    assert capsule.active_goal == "important_from_source"
    assert capsule.unresolved_request is not None
    assert capsule.unresolved_request.kind == "important_from_source"
    assert capsule.unresolved_request.status == "PARTIAL"
    assert capsule.last_outcome is not None
    assert capsule.last_outcome.capability == "source.recent"
    assert capsule.last_outcome.request_satisfied is False

    and_turn = "and?"
    det_and = interpret_request(and_turn, session)
    assert det_and.evidence_domain == "PRIVATE_WORLD"
    compiled = compile_with_bootstrap(and_turn, session, _FIXTURE)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert compiled.authority != "APPROVE"
    assert compiled.working_set["request_kind"] == "important_from_source"
    assert _FRESH_WORLD_TOOLS & set(compiled.tool_names)
    assert "source.recent" in compiled.tool_names or "attention.get_current" in compiled.tool_names
    stale = (compiled.working_set.get("capsule") or {}).get("last_outcome") or {}
    assert stale.get("request_satisfied") is False
    assert "assist.approve" not in compiled.tool_names

    empty = run_orchestrator_turn(
        user_message=and_turn,
        session=session,
        llm=_ScriptedLLM({and_turn: []}),
        bootstrap=_FIXTURE,
    )
    assert [row.name for row in empty.tool_results if row.ok] == []
    still = session.context.live_capsule()
    assert still is not None
    assert still.unresolved_request is not None
    assert still.unresolved_request.kind == "important_from_source"
    assert still.last_outcome is None or still.last_outcome.request_satisfied is False

    fresh = _run(session, and_turn, ["source.recent"])
    assert [row.name for row in fresh.tool_results if row.ok] == ["source.recent"]
    after = session.context.live_capsule()
    assert after is not None
    assert after.evidence_domain == "PRIVATE_WORLD"
    assert after.unresolved_request is not None
    assert after.last_outcome is not None
    assert after.last_outcome.request_satisfied is False
