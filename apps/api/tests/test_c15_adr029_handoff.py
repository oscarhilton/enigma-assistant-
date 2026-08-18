"""C15 — ADR-029 handoff: recover unsatisfied private request, not phatic.

Do not reopen C09c. Capsule retention is assumed. This contract is the
compiler using retained context after frustration.
"""

from __future__ import annotations

import json
from typing import Any

from personal_enigma.api.context_compilation import compile_remote_context, interpret_request
from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool
from personal_enigma.api.semantic_bootstrap import (
    SemanticInterpretation,
    compile_with_bootstrap,
    merge_request_interpretation,
)

TOKEN_ID = "item-obligation_token_audit"
JAN19 = "cp-2026-01-19T10:00"
_RANKING_RESIDUE = "Token audit kickoff first, token meeting second, Q1 checkout third."
_PRIVATE_TOOLS = frozenset(
    {
        "attention.get_current",
        "next_action.get",
        "agenda.get",
        "source.recent",
    }
)


class _ScriptedLLM:
    def __init__(self, script: dict[str, list[ToolCallRecord]]) -> None:
        self._script = script
        self.last_conversational_text: str | None = None

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


def _run(session: DemoToolSession, utterance: str, tools: list[str]) -> Any:
    script = {utterance: [ToolCallRecord(name=name) for name in tools]}
    return run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM(script),
        bootstrap=None,
    )


def _seed_six_prior_turns(session: DemoToolSession) -> None:
    """Reconstruct the live dump: six dialogue rows, TOKEN subject, mail unsatisfied."""
    result = execute_tool(session, "next_action.get", {})
    update_context_from_turn_items(session.context, result.turn_items)
    assert session.context.current_subject_id == TOKEN_ID

    _run(session, "what's on today?", ["agenda.get"])
    _run(session, "what should I do with this free time?", ["next_action.get"])
    _run(session, "look at my mail and tell me what's important", ["source.recent"])
    dialogue = session.context.recent_dialogue
    assert len(dialogue) == 6
    user_texts = [row.text for row in dialogue if row.role == "user"]
    assert any("mail" in text.casefold() and "important" in text.casefold() for text in user_texts)
    last = dialogue[-1]
    last.text = _RANKING_RESIDUE
    last.summary = _RANKING_RESIDUE
    capsule = session.context.live_grounded_frame()
    assert capsule is not None
    assert capsule.unresolved_request is not None
    assert capsule.unresolved_request.kind == "important_from_source"


def test_ffs_after_unsatisfied_private_request_compiles_private_query() -> None:
    """Flagship: frustration must not compile CONVERSATION_ONLY with zero tools."""
    session = _tool_session()
    _seed_six_prior_turns(session)
    assert session.context.current_subject_id == TOKEN_ID
    # Compiler must recover even when the live frame is no longer handed over.
    session.context.capsule = None
    assert session.context.live_grounded_frame() is None
    assert len(session.context.recent_dialogue) == 6

    compiled = compile_remote_context("ffs", session)
    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert compiled.profile != "CONVERSATION"
    assert compiled.evidence_domain != "CONVERSATION_ONLY"
    assert compiled.authority != "NONE"
    assert compiled.tool_names
    assert _PRIVATE_TOOLS & set(compiled.tool_names)
    assert "source" in compiled.capability_families or "attention" in compiled.capability_families
    assert compiled.working_set.get("request_kind") == "important_from_source"
    assert compiled.working_set.get("source") == "email"

    # must_not: treat transcript content as fresh ranking evidence
    wire = json.dumps(compiled.working_set, default=str).casefold()
    assert "kickoff" not in wire
    assert compiled.tool_names != []
    dialogue_blob = json.dumps(
        compiled.context_summary.get("recent_dialogue") or [],
        default=str,
    ).casefold()
    assert "mail" in dialogue_blob or "important" in dialogue_blob


def test_ugh_similar_frustration_recovers_the_same_private_request() -> None:
    session = _tool_session()
    _seed_six_prior_turns(session)
    session.context.capsule = None
    compiled = compile_remote_context("ugh", session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert compiled.tool_names
    assert _PRIVATE_TOOLS & set(compiled.tool_names)


def test_ffs_without_private_history_stays_conversation() -> None:
    session = _tool_session()
    compiled = compile_remote_context("ffs", session)
    assert compiled.evidence_domain == "CONVERSATION_ONLY"
    assert compiled.authority == "NONE"
    assert compiled.tool_names == []


def test_thanks_after_unsatisfied_mail_stays_phatic() -> None:
    session = _tool_session()
    _seed_six_prior_turns(session)
    session.context.capsule = None
    compiled = compile_remote_context("thanks", session)
    assert compiled.evidence_domain != "PRIVATE_WORLD"
    assert compiled.tool_names == []


def test_sky_blue_does_not_recover_private_request() -> None:
    session = _tool_session()
    _seed_six_prior_turns(session)
    compiled = compile_remote_context("why is the sky blue?", session)
    assert compiled.evidence_domain == "GENERAL_KNOWLEDGE"
    assert compiled.tool_names == []


def test_bootstrap_cannot_reclassify_ffs_as_phatic() -> None:
    session = _tool_session()
    _seed_six_prior_turns(session)
    session.context.capsule = None
    det = interpret_request("ffs", session)
    assert det.evidence_domain == "PRIVATE_WORLD"
    rogue = SemanticInterpretation(
        evidence_domain="CONVERSATION_ONLY",
        authority="NONE",
        confidence=0.99,
    )
    merged = merge_request_interpretation("ffs", det, rogue, None)
    assert merged.evidence_domain == "PRIVATE_WORLD"
    assert merged.authority == "READ"
    compiled = compile_with_bootstrap(
        "ffs",
        session,
        bootstrap=None,
        semantic=rogue,
    )
    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.tool_names
    assert _PRIVATE_TOOLS & set(compiled.tool_names)


def test_ranking_residue_is_not_the_answer() -> None:
    """Transcript recovers intent. A no-tool ranking does not satisfy the request."""
    session = _tool_session()
    _seed_six_prior_turns(session)
    session.context.capsule = None
    llm = _ScriptedLLM({"ffs": []})
    llm.last_conversational_text = _RANKING_RESIDUE
    run_orchestrator_turn(
        user_message="ffs",
        session=session,
        llm=llm,
        bootstrap=None,
    )
    # Compile still required a private tool; residue did not become truth.
    compiled = compile_remote_context("ffs", session)
    assert compiled.tool_names
    assert _PRIVATE_TOOLS & set(compiled.tool_names)
