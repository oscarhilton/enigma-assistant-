"""C28 integration bridge — demo_tools assist.approve through event/effect spine."""

from __future__ import annotations

from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import AssistPlan, SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool
from personal_enigma.api.routes.demo import DemoSession, attach_event_spine_to_tool_session

BRUNCH_ID = "item-obligation_brunch_book"
TOKEN_ID = "item-obligation_token_audit"
JAN19 = "cp-2026-01-19T10:00"


def _brunch_plan(proposal_id: str = "assist-brunch-bridge") -> AssistPlan:
    return AssistPlan(
        proposal_id=proposal_id,
        title="Book Saturday brunch for Elena's parents",
        description="I'll book this on the synthetic demo calendar.",
        action_label="Approve",
        source_item_id=BRUNCH_ID,
        action_kind="calendar_book",
    )


def _note_plan(proposal_id: str = "assist-note-bridge") -> AssistPlan:
    return AssistPlan(
        proposal_id=proposal_id,
        title="Draft colour + spacing token inventory",
        description="I'll record a synthetic demo draft for this.",
        action_label="Approve",
        source_item_id=TOKEN_ID,
        action_kind="synthetic_note",
    )


def _wired_tool_session(*, fail_writes: bool = False) -> tuple[DemoSession, DemoToolSession]:
    state = project_checkpoint(JAN19).state
    tool = DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(fail_writes=fail_writes),
    )
    demo = attach_event_spine_to_tool_session(tool)
    return demo, tool


def _authorize_approve(tool: DemoToolSession, proposal_id: str) -> None:
    tool.context.set_pending_confirmation("APPROVE_CONFIRMATION", proposal_id)
    tool.context.current_assist_proposal_id = proposal_id


def _approve_via_tools(tool: DemoToolSession, proposal_id: str):
    _authorize_approve(tool, proposal_id)
    tool.user_message = "Go on then."
    return execute_tool(tool, "assist.approve", {"proposal_id": proposal_id})


def test_c28_bridge_demo_tools_approval_uses_event_effect_path() -> None:
    demo, tool = _wired_tool_session()
    plan = _brunch_plan()
    tool.pending_assists[plan.proposal_id] = plan

    result = _approve_via_tools(tool, plan.proposal_id)

    assert result.ok is True
    kinds = [row.kind for row in demo.semantic_events]
    assert "conversation.user_approved_effect" in kinds
    assert "effect.executed" in kinds
    assert "effect.verified" in kinds
    assert "work.handled" in kinds
    assert demo.effect_by_proposal[plan.proposal_id] in demo.effect_records


def test_c28_bridge_approval_of_effect_a_cannot_approve_effect_b() -> None:
    demo, tool = _wired_tool_session()
    plan_a = _brunch_plan("assist-bridge-a")
    plan_b = _note_plan("assist-bridge-b")
    tool.pending_assists[plan_a.proposal_id] = plan_a
    tool.pending_assists[plan_b.proposal_id] = plan_b
    demo.link_assist_to_work(proposal_id=plan_a.proposal_id, subject_id=BRUNCH_ID)
    demo.link_assist_to_work(proposal_id=plan_b.proposal_id, subject_id=TOKEN_ID)

    _approve_via_tools(tool, plan_a.proposal_id)

    assert plan_a.proposal_id in demo.effect_by_proposal
    assert plan_b.proposal_id not in demo.effect_by_proposal
    effect_a = demo.effect_records[demo.effect_by_proposal[plan_a.proposal_id]]
    assert effect_a.status == "VERIFIED"
    assert plan_b.proposal_id in tool.pending_assists


def test_c28_bridge_duplicate_approve_does_not_execute_twice() -> None:
    demo, tool = _wired_tool_session()
    plan = _brunch_plan("assist-bridge-dedupe")
    tool.pending_assists[plan.proposal_id] = plan

    first = _approve_via_tools(tool, plan.proposal_id)
    second = _approve_via_tools(tool, plan.proposal_id)

    assert first.ok is True
    assert second.ok is True
    assert second.data.get("deduplicated") is True
    effect = demo.effect_records[demo.effect_by_proposal[plan.proposal_id]]
    assert effect.execution_count == 1
    assert effect.verification_count == 1


def test_c28_bridge_execution_without_verification_does_not_update_world() -> None:
    demo, tool = _wired_tool_session(fail_writes=True)
    plan = _brunch_plan("assist-bridge-verify-fail")
    tool.pending_assists[plan.proposal_id] = plan
    demo.link_assist_to_work(proposal_id=plan.proposal_id, subject_id=BRUNCH_ID)

    result = _approve_via_tools(tool, plan.proposal_id)

    assert result.ok is False
    assert BRUNCH_ID not in tool.completed_item_ids
    effect = demo.effect_records[demo.effect_by_proposal[plan.proposal_id]]
    assert effect.status == "FAILED"
    assert demo.agent_work[effect.work_id].status == "VERIFYING"
    assert "work.handled" not in [row.kind for row in demo.semantic_events]


def test_c28_bridge_verification_success_updates_world_once() -> None:
    demo, tool = _wired_tool_session()
    plan = _brunch_plan("assist-bridge-world-once")
    tool.pending_assists[plan.proposal_id] = plan

    result = _approve_via_tools(tool, plan.proposal_id)

    assert result.ok is True
    assert BRUNCH_ID in tool.completed_item_ids
    effect = demo.effect_records[demo.effect_by_proposal[plan.proposal_id]]
    assert effect.verification_count == 1
    _approve_via_tools(tool, plan.proposal_id)
    assert len(tool.completed_item_ids) == 1


def test_c28_bridge_existing_user_visible_behaviour_remains_compatible() -> None:
    demo, tool = _wired_tool_session()
    token_turn = execute_tool(tool, "next_action.get", {})
    update_context_from_turn_items(tool.context, token_turn.turn_items)
    assert tool.context.current_subject_id == TOKEN_ID

    propose = run_orchestrator_turn(
        user_message="Can you help me do that?",
        session=tool,
        llm=_ScriptedLLM({"Can you help me do that?": [ToolCallRecord(name="assist.propose")]}),
    )
    assert propose.tool_results[0].ok
    proposal_id = tool.context.current_assist_proposal_id
    assert proposal_id

    approve = run_orchestrator_turn(
        user_message="Go on then.",
        session=tool,
        llm=_ScriptedLLM({"Go on then.": [ToolCallRecord(name="assist.approve")]}),
    )
    assert approve.tool_results[0].ok
    assert tool.synthetic_services.notes
    assert approve.tool_results[0].data.get("artifact_id")
    assert any(item["kind"] == "assist_result" for item in approve.turn_items)


def test_c28_bridge_ready_for_user_does_not_couple_to_notify_now() -> None:
    demo, tool = _wired_tool_session()
    plan = _brunch_plan("assist-bridge-no-notify")
    tool.pending_assists[plan.proposal_id] = plan

    before = len(tool.conversation)
    demo.link_assist_to_work(proposal_id=plan.proposal_id, subject_id=BRUNCH_ID)

    assert demo.agent_work[demo.agent_work_by_subject[BRUNCH_ID]].status == "READY_FOR_USER"
    assert len(tool.conversation) == before
    assert "attention_surfaced" not in [row["kind"] for row in demo.event_log]


def test_c28_bridge_legacy_approve_without_spine_cannot_update_world() -> None:
    state = project_checkpoint(JAN19).state
    tool = DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )
    plan = _brunch_plan("assist-bridge-no-spine")
    tool.pending_assists[plan.proposal_id] = plan
    _authorize_approve(tool, plan.proposal_id)
    tool.user_message = "Go on then."

    result = execute_tool(tool, "assist.approve", {"proposal_id": plan.proposal_id})

    assert result.ok is False
    assert result.data.get("reason") == "event_spine_required"
    assert BRUNCH_ID not in tool.completed_item_ids
    assert not tool.synthetic_services.calendar_events


class _ScriptedLLM:
    def __init__(self, script: dict[str, list[ToolCallRecord]]) -> None:
        self._script = script

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict,
        tools: list[dict],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del context_summary, tools, correlation_id
        return [call.model_copy(deep=True) for call in self._script[user_message]]
