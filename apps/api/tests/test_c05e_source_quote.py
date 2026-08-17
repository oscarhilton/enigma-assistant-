"""C05e — recent sources and local quotation; verbatim chat never on the tool wire."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personal_enigma.api.conversation_context import (
    ConversationContext,
    project_recent_dialogue_for_egress,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_chat import RAW_TTL, DemoChatIndex, load_demo_chat_index
from personal_enigma.api.demo_orchestrator import (
    _compact_tool_data,
    context_summary,
    run_orchestrator_turn,
)
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import (
    DENIED_REMOTE_CAPABILITIES,
    DemoToolSession,
    ToolCallRecord,
    execute_tool,
    tool_schemas,
)
from personal_enigma.fixtures import build_chat_message
from personal_enigma.obligations import apply_chat_messages
from personal_enigma.privacy.egress.classification import RemoteSafeContext
from personal_enigma.privacy.egress.disclosure import CONVERSATION_EGRESS_EXCLUDED

JAN20 = "cp-2026-01-20T11:00"
UNTIL = datetime(2026, 1, 20, 11, 0, tzinfo=UTC)
JAN28 = datetime(2026, 1, 28, 11, 0, tzinfo=UTC)
RAW = "Mum and Dad are definitely coming Saturday btw"
FACT = "Elena confirmed her parents are coming Saturday."
FIREWORKS_MODEL = "accounts/fireworks/models/gpt-oss-120b"


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


def _session(index: DemoChatIndex | None = None, user_message: str = "") -> DemoToolSession:
    state = project_checkpoint(JAN20).state
    return DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN20,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
        user_message=user_message,
        chat_index=index or DemoChatIndex(),
    )


def test_denied_capabilities_include_wholesale_whatsapp() -> None:
    assert "whatsapp.search" in DENIED_REMOTE_CAPABILITIES
    assert "whatsapp.send" in DENIED_REMOTE_CAPABILITIES
    assert "raw chat bodies" in CONVERSATION_EGRESS_EXCLUDED


def test_alex_index_derives_parent_fact_without_raw_body_on_wire() -> None:
    index = load_demo_chat_index("alex-v1", until=UNTIL)
    session = _session(index, "Did Elena say whether her parents are definitely coming?")
    result = execute_tool(session, "world.explain", {})
    compact = _compact_tool_data(result.data)
    blob = str(compact).casefold()
    assert FACT in " ".join(
        item.get("text") or "" for item in result.turn_items if isinstance(item.get("text"), str)
    )
    assert "mum and dad are definitely coming" not in blob
    assert "body_text" not in blob
    assert RAW.casefold() not in blob
    assert FACT in compact.get("facts", [])


def test_source_quote_is_local_and_omits_body_from_wire() -> None:
    message = build_chat_message(
        id="wa-elena-parents-coming",
        provider_message_id="wa-elena-parents-coming",
        body_text=RAW,
        sent_at=datetime(2026, 1, 19, 18, 30, tzinfo=UTC),
    )
    index = DemoChatIndex(messages=[message], world=apply_chat_messages([message]))
    session = _session(index, "What exactly did she say?")
    session.conversation = [
        {
            "kind": "user_message",
            "text": "Did Elena say whether her parents are definitely coming?",
        }
    ]
    result = execute_tool(session, "source.quote", {})
    compact = _compact_tool_data(result.data)
    assert result.data["quoted_locally"] is True
    assert result.data["source_id"] == "wa-elena-parents-coming"
    assert "body_text" not in result.data
    assert RAW.casefold() not in str(compact).casefold()
    quote = result.turn_items[0]
    assert quote["kind"] == "source_quote"
    assert quote["local_only"] is True
    assert RAW in quote["text"]


def test_expired_raw_cannot_be_quoted() -> None:
    message = build_chat_message(
        id="wa-old",
        provider_message_id="wa-old",
        body_text=RAW,
        sent_at=UNTIL - timedelta(days=8),
    )
    index = DemoChatIndex(
        messages=[message],
        world=apply_chat_messages([message]),
        expired_ids={message.id, message.provider_message_id},
    )
    session = _session(index, "What exactly did Elena say?")
    result = execute_tool(session, "source.quote", {})
    assert result.data["expired"] is True
    assert result.data["quoted_locally"] is False
    assert RAW not in str(result.turn_items)
    assert "no longer stored" in result.turn_items[0]["text"].casefold()


def test_source_recent_whatsapp_returns_ids_not_bodies() -> None:
    message = build_chat_message(
        provider_message_id="wa-elena-parents-coming",
        body_text=RAW,
        sent_at=datetime(2026, 1, 19, 18, 30, tzinfo=UTC),
    )
    index = DemoChatIndex(messages=[message], world=apply_chat_messages([message]))
    session = _session(index, "Anything in WhatsApp?")
    result = execute_tool(session, "source.recent", {"channel": "whatsapp"})
    compact = _compact_tool_data(result.data)
    assert result.data["channel"] == "whatsapp"
    assert "wa-elena-parents-coming" in result.data["recent_ids"]
    assert RAW.casefold() not in str(compact).casefold()
    assert "body_text" not in compact
    assert FACT in result.turn_items[0]["text"]


def _assert_no_verbatim_on_remote(blob: object) -> None:
    hay = str(blob).casefold()
    assert RAW.casefold() not in hay
    assert "body_text" not in hay


def test_follow_up_after_quote_does_not_leak_through_recent_dialogue() -> None:
    """QUOTE ≠ REMOTE CONTEXT: local quote may render; Fireworks must not see the body."""
    index = load_demo_chat_index("alex-v1", until=UNTIL)
    state = project_checkpoint(JAN20).state
    session = DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN20,
        prior_state=None,
        at=state.simulated_time,
        conversation=[
            {
                "kind": "user_message",
                "text": "Did Elena say whether her parents are definitely coming?",
            }
        ],
        synthetic_services=SyntheticDemoServices(),
        chat_index=index,
    )
    quote_utterance = "What exactly did she say?"
    follow_utterance = "Oh good — do I need to do anything?"
    llm = _ScriptedLLM(
        {
            quote_utterance: [ToolCallRecord(name="source.quote")],
            follow_utterance: [ToolCallRecord(name="next_action.get")],
        }
    )
    quoted = run_orchestrator_turn(
        user_message=quote_utterance,
        session=session,
        llm=llm,
    )
    local_text = " ".join(
        str(item.get("text") or "") for item in quoted.turn_items
    )
    assert RAW in local_text
    assert any(item.get("kind") == "source_quote" for item in quoted.turn_items)
    for result in quoted.tool_results:
        _assert_no_verbatim_on_remote(_compact_tool_data(result.data))
        _assert_no_verbatim_on_remote(result.data)

    projected = project_recent_dialogue_for_egress(session.context.recent_dialogue)
    _assert_no_verbatim_on_remote(projected)
    summaries = [
        row.get("summary") for row in projected if row.get("role") == "assistant"
    ]
    assert any(
        isinstance(summary, str) and "local quotation" in summary.casefold()
        for summary in summaries
    )

    summary = context_summary(session.context, session.state)
    remote = RemoteSafeContext.for_conversation_orchestrator(
        user_message=follow_utterance,
        context_summary=summary,
        tools=tool_schemas(),
        model=FIREWORKS_MODEL,
        denied_capabilities=list(DENIED_REMOTE_CAPABILITIES),
    )
    wire = remote.wire_body
    _assert_no_verbatim_on_remote(wire)
    user_content = wire["messages"][1]["content"]
    _assert_no_verbatim_on_remote(user_content)
    assert "local quotation" in str(user_content).casefold()

    follow = run_orchestrator_turn(
        user_message=follow_utterance,
        session=session,
        llm=llm,
    )
    follow_local = " ".join(str(item.get("text") or "") for item in follow.turn_items)
    assert RAW not in follow_local
    for result in follow.tool_results:
        _assert_no_verbatim_on_remote(_compact_tool_data(result.data))
        _assert_no_verbatim_on_remote(result.data)
    _assert_no_verbatim_on_remote(
        project_recent_dialogue_for_egress(session.context.recent_dialogue)
    )
    nxt = execute_tool(session, "next_action.get", {})
    open_ids = [row.id for row in [*session.state.needs_you, *session.state.context]]
    open_ids.extend(row.source_candidate_id or row.id for row in session.state.next_actions)
    open_ids.extend(
        item["action"]["source_candidate_id"]
        for item in nxt.turn_items
        if item.get("kind") == "next_action"
    )
    assert "item-obligation_brunch_book" in open_ids


def test_raw_ttl_expires_quote_but_derived_fact_survives() -> None:
    """EXPIRY ≠ LOSS OF ALL UTILITY: 7-day RAW_TTL hides the body, not the fact."""
    assert RAW_TTL.days == 7
    index = load_demo_chat_index("alex-v1", until=JAN28)
    parents = next(
        message
        for message in index.messages
        if message.provider_message_id == "wa-elena-parents-coming"
    )
    assert index.is_expired(parents)
    assert FACT in [fact.summary for fact in index.world.facts]
    assert RAW not in " ".join(fact.summary for fact in index.world.facts)

    quote_session = _session(index, "What exactly did she say?")
    quote_session.conversation = [
        {
            "kind": "user_message",
            "text": "Did Elena say whether her parents are definitely coming?",
        }
    ]
    quoted = execute_tool(quote_session, "source.quote", {})
    assert quoted.data["expired"] is True
    assert quoted.data["quoted_locally"] is False
    assert RAW not in str(quoted.turn_items)
    _assert_no_verbatim_on_remote(_compact_tool_data(quoted.data))
    assert "no longer stored" in quoted.turn_items[0]["text"].casefold()

    explain = execute_tool(
        _session(index, "Are her parents still coming?"),
        "world.explain",
        {},
    )
    compact = _compact_tool_data(explain.data)
    assert FACT in compact.get("facts", [])
    assert FACT in " ".join(
        item.get("text") or ""
        for item in explain.turn_items
        if isinstance(item.get("text"), str)
    )
    _assert_no_verbatim_on_remote(compact)
    _assert_no_verbatim_on_remote(explain.data)
