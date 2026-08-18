from __future__ import annotations

from personal_enigma.api.demo_assist import AssistPlan
from personal_enigma.api.routes.demo import DemoSession

BRUNCH_ID = "item-obligation_brunch_book"


def _brunch_plan(proposal_id: str = "assist-brunch") -> AssistPlan:
    return AssistPlan(
        proposal_id=proposal_id,
        title="Book Saturday brunch for Elena's parents",
        description="I'll book this on the synthetic demo calendar.",
        action_label="Approve",
        source_item_id=BRUNCH_ID,
        action_kind="calendar_book",
    )


def test_c28_freeze_gate_resumes_same_work_and_dedupes_effect() -> None:
    session = DemoSession()

    work = session.receive_source_event(
        event_id="src-brunch-1",
        subject_id=BRUNCH_ID,
        title="Book Saturday brunch for Elena's parents",
    )
    assert work.status == "DETECTED"
    assert len(session.agent_work) == 1

    duplicate_source = session.receive_source_event(
        event_id="src-brunch-1",
        subject_id=BRUNCH_ID,
    )
    assert duplicate_source.work_id == work.work_id
    assert len(session.agent_work) == 1

    session.advance_agent_work(work.work_id)
    session.wait_for_dependency(work.work_id, dependency_key="dep:elena-confirmed")
    assert session.agent_work[work.work_id].status == "WAITING_EXTERNAL"

    plan = _brunch_plan()
    session.pending_assists[plan.proposal_id] = plan
    resumed = session.receive_dependency_event(
        event_id="dep-event-1",
        subject_id=BRUNCH_ID,
        dependency_key="dep:elena-confirmed",
        proposal_id=plan.proposal_id,
    )
    assert resumed.work_id == work.work_id
    assert resumed.status == "READY_FOR_USER"

    execution = session.start_assist_execution(plan.proposal_id)
    effect = next(iter(session.effect_records.values()))
    assert session.agent_work[work.work_id].status == "VERIFYING"
    assert effect.status == "EXECUTED"
    assert effect.execution_count == 1
    assert execution.artifact_id
    assert BRUNCH_ID not in session.completed_item_ids

    duplicate_dependency = session.receive_dependency_event(
        event_id="dep-event-1",
        subject_id=BRUNCH_ID,
        dependency_key="dep:elena-confirmed",
        proposal_id=plan.proposal_id,
    )
    assert duplicate_dependency.work_id == work.work_id
    assert session.agent_work[work.work_id].status == "VERIFYING"
    assert next(iter(session.effect_records.values())).execution_count == 1

    result = session.verify_assist_effect(plan.proposal_id, execution)
    assert result["ok"] is True
    assert "booked" in result["message"].lower()
    assert session.agent_work[work.work_id].status == "HANDLED"
    assert next(iter(session.effect_records.values())).status == "VERIFIED"
    assert next(iter(session.effect_records.values())).verification_count == 1
    assert BRUNCH_ID in session.completed_item_ids


def test_c28_semantic_events_expose_causality_chain() -> None:
    session = DemoSession()
    work = session.receive_source_event(
        event_id="src-brunch-2",
        subject_id=BRUNCH_ID,
        title="Book Saturday brunch for Elena's parents",
    )
    session.advance_agent_work(work.work_id)
    session.wait_for_dependency(work.work_id, dependency_key="dep:reply")

    plan = _brunch_plan("assist-brunch-2")
    session.pending_assists[plan.proposal_id] = plan
    session.receive_dependency_event(
        event_id="dep-event-2",
        subject_id=BRUNCH_ID,
        dependency_key="dep:reply",
        proposal_id=plan.proposal_id,
    )
    execution = session.start_assist_execution(plan.proposal_id)
    session.verify_assist_effect(plan.proposal_id, execution)

    payload = session.events_payload()
    kinds = [row["kind"] for row in payload["semantic_events"]]
    assert kinds == [
        "source.event_detected",
        "work.created",
        "work.investigating",
        "work.waiting_external",
        "world.dependency_arrived",
        "work.ready_for_user",
        "conversation.user_approved_effect",
        "effect.executed",
        "effect.verified",
        "work.handled",
    ]
    handled = payload["semantic_events"][-1]
    executed = payload["semantic_events"][-3]
    assert handled["caused_by"] == [execution.execution_id]
    assert executed["work_id"] == work.work_id
    assert payload["agent_work"][0]["effect_id"] == payload["effects"][0]["effect_id"]


def test_c28_rebuild_indexes_dedupes_after_process_reconstruction() -> None:
    session = DemoSession()
    work = session.receive_source_event(
        event_id="src-brunch-rebuild",
        subject_id=BRUNCH_ID,
        title="Book Saturday brunch for Elena's parents",
    )
    session.advance_agent_work(work.work_id)
    session.wait_for_dependency(work.work_id, dependency_key="dep:elena-confirmed")

    session.processed_event_ids.clear()
    session.agent_work_by_subject.clear()
    session._rebuild_event_spine_indexes()

    duplicate = session.receive_source_event(
        event_id="src-brunch-rebuild",
        subject_id=BRUNCH_ID,
    )
    assert duplicate.work_id == work.work_id
    assert len(session.agent_work) == 1


def test_c28_wrong_dependency_does_not_resume_blocked_work() -> None:
    session = DemoSession()
    work = session.receive_source_event(
        event_id="src-brunch-wrong-dep",
        subject_id=BRUNCH_ID,
        title="Book Saturday brunch for Elena's parents",
    )
    session.advance_agent_work(work.work_id)
    session.wait_for_dependency(work.work_id, dependency_key="dep:elena-confirmed")

    plan = _brunch_plan("assist-brunch-wrong-dep")
    session.pending_assists[plan.proposal_id] = plan
    unrelated = session.receive_dependency_event(
        event_id="dep-unrelated",
        subject_id=BRUNCH_ID,
        dependency_key="dep:someone-else-replied",
        proposal_id=plan.proposal_id,
    )
    assert unrelated.work_id == work.work_id
    assert unrelated.status == "WAITING_EXTERNAL"
    assert "work.ready_for_user" not in [
        row.kind for row in session.semantic_events
    ]

    matched = session.receive_dependency_event(
        event_id="dep-correct",
        subject_id=BRUNCH_ID,
        dependency_key="dep:elena-confirmed",
        proposal_id=plan.proposal_id,
    )
    assert matched.status == "READY_FOR_USER"


def test_c28_approval_is_specific_to_one_proposal() -> None:
    session = DemoSession()
    plan_a = _brunch_plan("assist-brunch-a")
    plan_b = AssistPlan(
        proposal_id="assist-brunch-b",
        title="Draft brunch confirmation note",
        description="I'll draft a note on the synthetic demo notepad.",
        action_label="Approve",
        source_item_id=BRUNCH_ID,
        action_kind="synthetic_note",
    )
    session.pending_assists[plan_a.proposal_id] = plan_a
    session.pending_assists[plan_b.proposal_id] = plan_b
    session.link_assist_to_work(proposal_id=plan_a.proposal_id, subject_id=BRUNCH_ID)
    session.link_assist_to_work(proposal_id=plan_b.proposal_id, subject_id=BRUNCH_ID)

    session.start_assist_execution(plan_a.proposal_id)
    effect_a = session.effect_records[session.effect_by_proposal[plan_a.proposal_id]]
    assert effect_a.status == "EXECUTED"
    assert plan_b.proposal_id not in session.effect_by_proposal


def test_c28_verification_failure_does_not_claim_handled() -> None:
    session = DemoSession()
    plan = _brunch_plan("assist-brunch-verify-fail")
    session.pending_assists[plan.proposal_id] = plan
    work = session.link_assist_to_work(
        proposal_id=plan.proposal_id,
        subject_id=BRUNCH_ID,
    )
    session.synthetic_services.fail_writes = True
    execution = session.start_assist_execution(plan.proposal_id)
    assert work.status == "VERIFYING"
    assert BRUNCH_ID not in session.completed_item_ids

    result = session.verify_assist_effect(plan.proposal_id, execution)
    effect = session.effect_records[session.effect_by_proposal[plan.proposal_id]]

    assert result["ok"] is False
    assert effect.status == "FAILED"
    assert session.agent_work[work.work_id].status == "VERIFYING"
    assert BRUNCH_ID not in session.completed_item_ids
    assert "work.handled" not in [row.kind for row in session.semantic_events]


def test_c28_ready_for_user_does_not_surface_attention() -> None:
    session = DemoSession()
    plan = _brunch_plan("assist-brunch-no-notify")
    session.pending_assists[plan.proposal_id] = plan

    before = len(session.conversation)
    session.link_assist_to_work(proposal_id=plan.proposal_id, subject_id=BRUNCH_ID)

    assert session.agent_work[session.agent_work_by_subject[BRUNCH_ID]].status == "READY_FOR_USER"
    assert len(session.conversation) == before
    assert "attention_surfaced" not in [row["kind"] for row in session.event_log]
