"""C09 — bounded recent_dialogue is interpretive, not world truth."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.api.conversation_context import (
    RECENT_DIALOGUE_LIMIT,
    ConversationContext,
    DialogueTurn,
    classify_assistant_dialogue_egress,
    project_recent_dialogue_for_egress,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_chat import DemoChatIndex
from personal_enigma.api.demo_orchestrator import context_summary, run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool
from personal_enigma.fixtures import build_chat_message
from personal_enigma.obligations import apply_chat_messages
from personal_enigma.privacy.egress.classification import RemoteSafeContext
from personal_enigma.privacy.egress.disclosure import (
    CONVERSATION_EGRESS_EXCLUDED,
    CONVERSATION_EGRESS_INCLUDED,
)

TOKEN_ID = "item-obligation_token_audit"
JAN19 = "cp-2026-01-19T10:00"
JAN20 = "cp-2026-01-20T11:00"
RAW = "Mum and Dad are definitely coming Saturday btw"


class _ScriptedLLM:
    def __init__(self, script: dict[str, list[ToolCallRecord]]) -> None:
        self._script = script

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict,
        tools: list,
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del context_summary, tools, correlation_id
        return [call.model_copy(deep=True) for call in self._script[user_message]]


def _jan19() -> DemoToolSession:
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


def test_recent_dialogue_limit_is_six() -> None:
    assert RECENT_DIALOGUE_LIMIT == 6


def test_recent_dialogue_is_capped_and_shaped() -> None:
    session = _jan19()
    for index in range(5):
        utterance = f"hello {index}"
        run_orchestrator_turn(
            user_message=utterance,
            session=session,
            llm=_ScriptedLLM({utterance: []}),
        )
    turns = session.context.recent_dialogue
    assert len(turns) == RECENT_DIALOGUE_LIMIT
    projected = project_recent_dialogue_for_egress(turns)
    assert len(projected) == 6
    for row in projected:
        assert "role" in row
        assert "text" in row or "summary" in row
        assert "act" in row
    summary = context_summary(session.context, session.state)
    assert summary["recent_dialogue"] == projected
    remote = RemoteSafeContext.for_conversation_orchestrator(
        user_message="I'm excited to get going!",
        context_summary=summary,
        tools=[],
        model="accounts/fireworks/models/gpt-oss-120b",
    )
    user_content = remote.wire_body["messages"][1]["content"]
    assert "recent_dialogue" in user_content
    assert "hello 0" not in user_content
    assert "hello 4" in user_content


def test_recent_dialogue_helps_interpret_but_is_not_world_truth() -> None:
    session = _jan19()
    seed = execute_tool(session, "next_action.get", {})
    update_context_from_turn_items(session.context, seed.turn_items)
    done = "I've finished it!"
    run_orchestrator_turn(
        user_message=done,
        session=session,
        llm=_ScriptedLLM({done: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    excited = "I'm excited to get going!"
    turn = run_orchestrator_turn(
        user_message=excited,
        session=session,
        llm=_ScriptedLLM({excited: []}),
    )
    assert turn.tool_calls == []
    prior = project_recent_dialogue_for_egress(session.context.recent_dialogue)
    user_rows = [row for row in prior if row.get("role") == "user"]
    assert any("finished" in (row.get("text") or "") for row in user_rows)
    nxt = execute_tool(session, "next_action.get", {})
    ids = [
        item["action"]["source_candidate_id"]
        for item in nxt.turn_items
        if item.get("kind") == "next_action"
    ]
    assert TOKEN_ID not in ids


def test_local_assistant_quotation_is_not_replayed_raw() -> None:
    message = build_chat_message(
        id="wa-elena-parents-coming",
        provider_message_id="wa-elena-parents-coming",
        body_text=RAW,
        sent_at=datetime(2026, 1, 19, 18, 30, tzinfo=UTC),
    )
    index = DemoChatIndex(messages=[message], world=apply_chat_messages([message]))
    state = project_checkpoint(JAN20).state
    session = DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN20,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
        chat_index=index,
        user_message="What exactly did she say?",
    )
    result = execute_tool(session, "source.quote", {})
    classification, summary = classify_assistant_dialogue_egress(result.turn_items, RAW)
    assert classification == "local_only"
    assert summary == "Displayed a local quotation about the current subject"
    session.context.remember_dialogue_turn(
        DialogueTurn(
            role="assistant",
            text=RAW,
            act="world_answer",
            egress_classification=classification,
            summary=summary,
        )
    )
    projected = project_recent_dialogue_for_egress(session.context.recent_dialogue)
    blob = str(projected)
    assert RAW not in blob
    assert projected[0]["summary"] == "Displayed a local quotation about the current subject"
    assert "verbatim local assistant quotations" in CONVERSATION_EGRESS_EXCLUDED
    assert "recent dialogue (egress-filtered)" in CONVERSATION_EGRESS_INCLUDED


def test_prompt_says_recent_chat_is_not_world_truth() -> None:
    remote = RemoteSafeContext.for_conversation_orchestrator(
        user_message="What's next?",
        context_summary={"current_subject_id": TOKEN_ID, "recent_dialogue": []},
        tools=[],
        model="accounts/fireworks/models/gpt-oss-120b",
    )
    prompt = remote.wire_body["messages"][0]["content"]
    assert "Recent chat helps interpret" in prompt
    assert "It does not establish world truth" in prompt
    assert "Chat history remembers the conversation. World state remembers the world." in prompt
    assert "Send enough previous conversation to understand meaning" in prompt
