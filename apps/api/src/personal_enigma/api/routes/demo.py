"""Demo Mode environment, timeline, and UI support routes (D1 + D10 + D13).

Attention stubs use PRIVATE UI names on the dashboard (Maya, Atlas). Why stubs
may use MODEL VIEW pseudonyms (PERSON_A) so demos can contrast local vs remote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from personal_enigma.api.build_identity import (
    attach_forensic_provenance,
    session_forensic_provenance,
)
from personal_enigma.api.conversation_context import (
    ConversationContext,
    reconcile_action_focus,
    update_context_from_turn_items,
)
from personal_enigma.api.db.demo import drop_demo_database
from personal_enigma.api.demo_assist import (
    AssistExecution,
    AssistPlan,
    SyntheticDemoServices,
    apply_verified_assist_effect,
    assist_result_item,
    execute_assist,
    overlay_session_world,
    verify_assist_execution,
)
from personal_enigma.api.demo_attestation import UserAttestation
from personal_enigma.api.demo_chat import DemoChatIndex, load_demo_chat_index
from personal_enigma.api.demo_intents import build_intent_turn, format_attention_summary_text
from personal_enigma.api.demo_orchestrator import (
    LlmTrace,
    build_intent_router_trace,
    demo_llm_conversation_enabled,
    run_orchestrator_turn,
)
from personal_enigma.api.demo_projection import (
    legacy_attention_items,
    project_checkpoint,
    qualification_debug_payload,
)
from personal_enigma.api.demo_tools import DemoToolSession
from personal_enigma.attention.projection import NextActionView
from personal_enigma.fixtures.demo_checkpoints import (
    DEFAULT_DEMO_CHECKPOINT,
    list_demo_checkpoints,
    load_checkpoint_snapshot,
)
from personal_enigma.simulation import (
    DEMO_BANNER_TEXT,
    DemoEnvironment,
    EnvironmentMode,
    SimulationClock,
    environment_mode_from_env,
    storage_root_for,
)
from personal_enigma.simulation.checkpoints import (
    bootstrap_demo_storage,
    reset_demo_storage,
)
from personal_enigma.simulation.engine import assert_demo_storage_root

# Alex milestone opens on Jan 19 — not an arbitrary epoch stub.
_DEMO_CHECKPOINT = DEFAULT_DEMO_CHECKPOINT


def _demo_wall_now() -> datetime:
    """Wall clock for Demo UI realtime playback (not used by domain logic)."""
    return datetime.now(tz=UTC)

# Baseline catalog — private UI names; priority ≠ confidence; rank ≠ confidence.
_STUB_ATTENTION_BASE: list[dict[str, Any]] = [
    {
        "id": "att-atlas-review",
        "title": "Review Atlas proposal before Friday",
        "when": "Before Friday",
        "why_now_glance": "Deadline approaching",
        "body": (
            "You said you'd review this before Friday, and it still appears unfinished."
        ),
        "kind": "commitment",
        "priority": 4,
        "confidence": 0.91,
        # Rank blends urgency/importance/actionability/timing; confidence is a
        # factor, not a substitute for priority (a high-confidence newsletter
        # must not outrank a medium-confidence manager commitment).
        "attention_rank": 0.86,
        "evidence_ids": ["ev-mail-1", "ev-cal-1"],
    },
    {
        "id": "att-maya-scheduling",
        "title": "Follow up with Maya on scheduling",
        "when": None,
        "why_now_glance": "Thread waiting on you",
        "body": "This scheduling thread still appears to be waiting on you.",
        "kind": "follow_up",
        "priority": 3,
        "confidence": 0.72,
        "attention_rank": 0.61,
        "evidence_ids": ["ev-mail-2"],
    },
]

_DEFAULT_SUPPRESSED = 47

# Developer-only suppression inspector filters (engine reasons — not ScenarioSignalClass).
_SUPPRESSION_FILTERS: tuple[str, ...] = (
    "background",
    "newsletter",
    "spam",
    "low_priority",
    "duplicate",
    "resolved",
)

# Representative suppressed samples for /demo/suppressed (totals stay on status).
_STUB_SUPPRESSED: list[dict[str, Any]] = [
    {
        "id": "sup-newsletter-1",
        "message": "Newsletter announcing a local weekend event",
        "suppression_reason": "newsletter",
        "classification": "informational",
        "open_obligation": "none",
        "relationship_relevance": "low",
        "deadline": "none",
        "decision": "suppressed",
        "why_not": [
            "Message is a bulk newsletter with no personal ask.",
            "No open obligation or deadline tied to USER.",
            "Relationship relevance is low relative to active commitments.",
        ],
    },
    {
        "id": "sup-background-1",
        "message": "Colleague thread about an office coffee machine",
        "suppression_reason": "background",
        "classification": "social chatter",
        "open_obligation": "none",
        "relationship_relevance": "low",
        "deadline": "none",
        "decision": "suppressed",
        "why_not": [
            "Conversation is ambient workplace chatter.",
            "USER is not asked to act.",
        ],
    },
    {
        "id": "sup-spam-1",
        "message": "Urgent prize claim with suspicious tracking links",
        "suppression_reason": "spam",
        "classification": "unsolicited",
        "open_obligation": "none",
        "relationship_relevance": "none",
        "deadline": "none",
        "decision": "suppressed",
        "why_not": [
            "Matches unsolicited / phishing-like patterns.",
            "No trusted sender relationship.",
        ],
    },
    {
        "id": "sup-low-1",
        "message": "Optional survey about desk chair preferences",
        "suppression_reason": "low_priority",
        "classification": "optional admin",
        "open_obligation": "none",
        "relationship_relevance": "low",
        "deadline": "none",
        "decision": "suppressed",
        "why_not": [
            "Ask is optional and low impact.",
            "Does not outrank open commitments in the attention window.",
        ],
    },
    {
        "id": "sup-dup-1",
        "message": "Calendar reminder duplicate of Friday Atlas review",
        "suppression_reason": "duplicate",
        "classification": "already covered",
        "open_obligation": "covered by att-atlas-review",
        "relationship_relevance": "medium",
        "deadline": "Friday",
        "decision": "suppressed",
        "why_not": [
            "Evidence already supports a surfaced attention item.",
            "Surfacing again would create a duplicate alert.",
        ],
    },
    {
        "id": "sup-resolved-1",
        "message": "Earlier scheduling ping that Maya already closed",
        "suppression_reason": "resolved",
        "classification": "closed loop",
        "open_obligation": "none",
        "relationship_relevance": "medium",
        "deadline": "none",
        "decision": "suppressed",
        "why_not": [
            "Thread shows completion evidence.",
            "No residual action for USER.",
        ],
    },
]

_STUB_MEMORY: list[dict[str, Any]] = [
    {
        "id": "mem-person-a",
        "category": "People",
        "statement": "PERSON_A is probably important at work.",
        "confidence": 0.86,
        "evidence_count": 4,
        "first_observed": "2026-01-10T09:00:00+00:00",
        "last_observed": "2026-02-15T16:00:00+00:00",
    },
    {
        "id": "mem-atlas",
        "category": "Projects",
        "statement": "PROJECT_B (Atlas) has an active review commitment.",
        "confidence": 0.78,
        "evidence_count": 3,
        "first_observed": "2026-01-28T11:00:00+00:00",
        "last_observed": "2026-03-01T10:00:00+00:00",
    },
    {
        "id": "mem-open-loop",
        "category": "Open loops",
        "statement": "USER committed to review PROJECT_B before Friday.",
        "confidence": 0.9,
        "evidence_count": 2,
        "first_observed": "2026-03-14T09:03:00+00:00",
        "last_observed": "2026-03-14T11:12:00+00:00",
    },
]

_STUB_WHY: dict[str, dict[str, Any]] = {
    "att-atlas-review": {
        "item_id": "att-atlas-review",
        "title": "Review Atlas proposal before Friday",
        "headline": "WHY ENIGMA THINKS THIS MATTERS",
        "evidence": [
            "Email: PERSON_A requested review.",
            "Email: USER said they would review before Friday.",
            "Calendar: Review meeting Friday at 15:00.",
        ],
        "inference": [
            "USER made a commitment to PERSON_A.",
            "No evidence of completion has been observed.",
            "The commitment appears due before the Friday review.",
        ],
        "decision": [
            "The commitment remains unresolved.",
            "Its deadline falls within the configured attention window.",
            "Surface as a high-priority item.",
        ],
        "why_now": [
            "The deadline is approaching.",
            "There is still enough time to act before the review.",
        ],
        "priority": 4,
        "confidence": 0.91,
        "reason_codes": ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
    },
    "att-maya-scheduling": {
        "item_id": "att-maya-scheduling",
        "title": "Follow up with Maya on scheduling",
        "headline": "WHY ENIGMA THINKS THIS MATTERS",
        "evidence": [
            "Email: PERSON_A proposed times that remain unanswered.",
            "Calendar: No matching hold on USER's schedule.",
        ],
        "inference": [
            "A scheduling follow-up with PERSON_A remains open.",
            "No evidence USER closed the thread.",
        ],
        "decision": [
            "The follow-up is unresolved.",
            "It falls inside the configured attention window.",
            "Surface as a medium-priority item.",
        ],
        "why_now": [
            "The thread is still waiting on USER.",
            "Surface now while the window to respond is open.",
        ],
        "priority": 3,
        "confidence": 0.72,
        "reason_codes": [
            "CROSS_SOURCE_MATCH",
            "FOLLOW_UP_REQUIRED",
            "UNRESOLVED_THREAD",
        ],
    },
}


class SpeedBody(BaseModel):
    speed: float = Field(ge=0.0, le=1000.0)


class MessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class AssistApproveBody(BaseModel):
    proposal_id: str


SemanticEventKind = Literal[
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
AgentWorkStatus = Literal[
    "DETECTED",
    "INVESTIGATING",
    "WAITING_EXTERNAL",
    "READY_FOR_USER",
    "EXECUTING",
    "VERIFYING",
    "HANDLED",
]
EffectStatus = Literal["PENDING_USER", "EXECUTING", "EXECUTED", "VERIFIED", "FAILED"]


@dataclass
class SemanticEvent:
    event_id: str
    kind: SemanticEventKind
    at: str
    subject_id: str | None = None
    work_id: str | None = None
    effect_id: str | None = None
    dependency_key: str | None = None
    caused_by: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    duplicate_of: str | None = None

    def public_view(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "at": self.at,
            "subject_id": self.subject_id,
            "work_id": self.work_id,
            "effect_id": self.effect_id,
            "dependency_key": self.dependency_key,
            "caused_by": list(self.caused_by),
            "payload": dict(self.payload),
            "duplicate_of": self.duplicate_of,
        }


@dataclass
class AgentEffectRecord:
    effect_id: str
    proposal_id: str
    work_id: str
    subject_id: str
    status: EffectStatus
    execution_id: str | None = None
    execution_count: int = 0
    verification_count: int = 0
    artifact_id: str | None = None
    artifact_kind: str | None = None

    def public_view(self) -> dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "proposal_id": self.proposal_id,
            "work_id": self.work_id,
            "subject_id": self.subject_id,
            "status": self.status,
            "execution_id": self.execution_id,
            "execution_count": self.execution_count,
            "verification_count": self.verification_count,
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
        }


@dataclass
class AgentWork:
    work_id: str
    subject_id: str
    title: str
    status: AgentWorkStatus
    causal_event_ids: list[str] = field(default_factory=list)
    dependency_key: str | None = None
    pending_proposal_id: str | None = None
    effect_id: str | None = None

    def public_view(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "subject_id": self.subject_id,
            "title": self.title,
            "status": self.status,
            "causal_event_ids": list(self.causal_event_ids),
            "dependency_key": self.dependency_key,
            "pending_proposal_id": self.pending_proposal_id,
            "effect_id": self.effect_id,
        }


@dataclass
class DemoSession:
    """In-process Demo clock session wired to Alex checkpoint projection."""

    scenario: str = "alex-v1"
    speed: float = 1.0
    checkpoint_id: str = _DEMO_CHECKPOINT
    conversation: list[dict[str, Any]] = field(default_factory=list)
    conversation_context: ConversationContext = field(default_factory=ConversationContext)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    action_log: list[dict[str, Any]] = field(default_factory=list)
    completed_item_ids: set[str] = field(default_factory=set)
    assist_advances: dict[str, NextActionView] = field(default_factory=dict)
    attestations: list[UserAttestation] = field(default_factory=list)
    pending_assists: dict[str, AssistPlan] = field(default_factory=dict)
    executed_assists: dict[str, dict[str, Any]] = field(default_factory=dict)
    semantic_events: list[SemanticEvent] = field(default_factory=list)
    processed_event_ids: dict[str, str] = field(default_factory=dict)
    agent_work: dict[str, AgentWork] = field(default_factory=dict)
    agent_work_by_subject: dict[str, str] = field(default_factory=dict)
    effect_records: dict[str, AgentEffectRecord] = field(default_factory=dict)
    effect_by_proposal: dict[str, str] = field(default_factory=dict)
    synthetic_services: SyntheticDemoServices = field(default_factory=SyntheticDemoServices)
    env: DemoEnvironment = field(init=False)
    _wall_anchor: datetime | None = field(default=None, init=False, repr=False)
    _last_attention_fingerprint: str | None = field(default=None, init=False, repr=False)
    _prior_checkpoint_id: str | None = field(default=None, init=False, repr=False)
    session_started: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        self._reseed_session()

    def _checkpoint_epoch(self) -> datetime:
        return load_checkpoint_snapshot(self.checkpoint_id).at

    def _reseed_session(self) -> None:
        epoch = self._checkpoint_epoch()
        clock = SimulationClock(initial=epoch)
        self.env = DemoEnvironment(scenario=self.scenario, clock=clock)
        self.speed = 1.0
        self.conversation = []
        self.conversation_context = ConversationContext()
        self.event_log = []
        self.action_log = []
        self.completed_item_ids = set()
        self.assist_advances = {}
        self.attestations = []
        self.pending_assists = {}
        self.executed_assists = {}
        self.semantic_events = []
        self.processed_event_ids = {}
        self.agent_work = {}
        self.agent_work_by_subject = {}
        self.effect_records = {}
        self.effect_by_proposal = {}
        self.synthetic_services = SyntheticDemoServices()
        self._wall_anchor = None
        self._last_attention_fingerprint = None
        self._prior_checkpoint_id = None
        self.session_started = datetime.now(tz=UTC)
        self._record_evaluation_event("checkpoint_loaded")

    def _attention_state(self):
        frozen = project_checkpoint(self.checkpoint_id).state
        return overlay_session_world(frozen, self.completed_item_ids, self.assist_advances)

    def _record_evaluation_event(self, kind: str) -> None:
        state = self._attention_state()
        self.event_log.append(
            {
                "kind": kind,
                "at": self.clock.now().isoformat(),
                "checkpoint_id": self.checkpoint_id,
                "presentation": state.presentation.model_dump(mode="json"),
                "needs_you_count": len(state.needs_you),
                "proactive_silence": state.presentation.proactive_silence,
            }
        )

    def jump_checkpoint(self, checkpoint_id: str) -> None:
        load_checkpoint_snapshot(checkpoint_id)
        if checkpoint_id != self.checkpoint_id:
            self._prior_checkpoint_id = self.checkpoint_id
        self.checkpoint_id = checkpoint_id
        self.clock.set_time(self._checkpoint_epoch())
        self._wall_anchor = None
        # C16: attested completion is session overlay, not checkpoint state.
        # Re-project from the new frozen snapshot; do not wipe completed_item_ids.
        self.assist_advances = {
            key: row
            for key, row in self.assist_advances.items()
            if key not in self.completed_item_ids
            and (row.source_candidate_id or "") not in self.completed_item_ids
        }
        self.pending_assists = {}
        self.executed_assists = {}
        self.synthetic_services.clear()
        reconcile_action_focus(self.conversation_context, self._attention_state())
        self._record_evaluation_event("checkpoint_jump")
        self._maybe_emit_attention_changed(proactive=True)

    def _prior_attention_state(self):
        if self._prior_checkpoint_id is None:
            return None
        return project_checkpoint(self._prior_checkpoint_id).state

    def _attention_fingerprint(self) -> str:
        state = self._attention_state()
        parts = [row.id for row in state.needs_you] + [row.id for row in state.context]
        return "|".join(parts)

    def _maybe_emit_attention_changed(self, *, proactive: bool) -> None:
        fingerprint = self._attention_fingerprint()
        if fingerprint == self._last_attention_fingerprint:
            return
        self._last_attention_fingerprint = fingerprint
        state = self._attention_state()
        if proactive and state.presentation.proactive_silence:
            self._record_evaluation_event("proactive_silence")
            return
        if proactive and state.needs_you:
            self.conversation.append(
                {
                    "kind": "attention_summary",
                    "at": self.clock.now().isoformat(),
                    "state": state.model_dump(mode="json"),
                    "text": format_attention_summary_text(state),
                }
            )
            self._record_evaluation_event("attention_surfaced")

    def sync_realtime(self) -> None:
        """Apply wall-clock × speed onto the simulation clock when playing."""
        if self.speed <= 0 or self.clock.paused:
            self._wall_anchor = None
            return
        wall = _demo_wall_now()
        if self._wall_anchor is None:
            self._wall_anchor = wall
            return
        elapsed = wall - self._wall_anchor
        if elapsed <= timedelta(0):
            return
        self.clock.advance(elapsed * self.speed)
        self._wall_anchor = wall

    def set_speed(self, speed: float) -> None:
        self.sync_realtime()
        self.speed = speed
        if speed == 0:
            self.clock.pause()
            self._wall_anchor = None
        else:
            self.clock.resume()
            self._wall_anchor = _demo_wall_now()

    def advance_step(self) -> None:
        self.sync_realtime()
        self.clock.advance(timedelta(hours=1))
        self._wall_anchor = _demo_wall_now()
        self._maybe_emit_attention_changed(proactive=False)

    def advance_day(self) -> None:
        self.sync_realtime()
        self.clock.advance_days(1)
        self._wall_anchor = _demo_wall_now()
        self._maybe_emit_attention_changed(proactive=False)

    def wipe_and_bootstrap_storage(self) -> Path:
        """Wipe the active scenario Demo root and write a fresh checkpoint.

        Refuses Private / Shadow roots (ADR-005). Never follows symlinks out of
        the demo tree (``reset_demo_storage`` unlinks symlinks instead).
        """
        root = storage_root_for(EnvironmentMode.DEMO, scenario=self.scenario)
        _assert_demo_reset_root(root, scenario_id=self.scenario)
        drop_demo_database(scenario=self.scenario)
        reset_demo_storage(root)
        return bootstrap_demo_storage(
            root,
            scenario=self.scenario,
            now=self._checkpoint_epoch(),
        )

    def reset(self) -> dict[str, Any]:
        """Full demo reset: wipe Demo storage for this scenario, then reseed."""
        storage_path = self.wipe_and_bootstrap_storage()
        self._reseed_session()
        payload = self.status_payload()
        payload["ok"] = True
        payload["reset"] = True
        payload["storage_wiped"] = True
        payload["storage_bootstrapped"] = True
        payload["engine_state"] = str(storage_path)
        return payload

    @property
    def clock(self) -> SimulationClock:
        clock = self.env.clock
        if not isinstance(clock, SimulationClock):
            raise TypeError("Demo session requires SimulationClock")
        return clock

    @property
    def chat_index(self) -> DemoChatIndex:
        return load_demo_chat_index(self.scenario, until=self.clock.now())

    def status_payload(self) -> dict[str, Any]:
        self.sync_realtime()
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
        state = self._attention_state() if active else None
        surfaced = len(state.needs_you) if state is not None else None
        suppressed = (
            state.can_wait_summary.total_suppressed if state and state.can_wait_summary else None
        )
        considered = (
            surfaced + suppressed
            if surfaced is not None and suppressed is not None
            else None
        )
        return {
            "active": active,
            "mode": mode.value,
            "banner": DEMO_BANNER_TEXT if active else "",
            "scenario": self.scenario if active else None,
            "simulated_time": self.clock.now().isoformat() if active else None,
            "checkpoint_id": self.checkpoint_id if active else None,
            "speed": self.speed if active else None,
            "paused": self.clock.paused if active else None,
            "storage_root": str(self.env.storage_root) if active else None,
            "ground_truth_visible": False,
            "signals_considered": considered,
            "surfaced_count": surfaced,
            "suppressed_count": suppressed,
            "noise_suppressed_count": suppressed,
        }

    def attention_state_payload(self) -> dict[str, Any]:
        self.sync_realtime()
        payload = self._attention_state().model_dump(mode="json")
        payload["simulated_time"] = self.clock.now().isoformat()
        return payload

    def attention_payload(self) -> dict[str, Any]:
        self.sync_realtime()
        state = self._attention_state()
        items = legacy_attention_items(state)
        suppressed = state.can_wait_summary.total_suppressed if state.can_wait_summary else 0
        surfaced = len(items)
        return {
            "items": items,
            "simulated_time": self.clock.now().isoformat(),
            "checkpoint_id": self.checkpoint_id,
            "signals_considered": surfaced + suppressed,
            "surfaced_count": surfaced,
            "suppressed_count": suppressed,
            "next_actions": [row.model_dump(mode="json") for row in state.next_actions],
            "context_count": len(state.context),
        }

    def suppressed_payload(self, reason: str | None = None) -> dict[str, Any]:
        """Developer-only inspector — never expose ScenarioSignalClass labels."""
        self.sync_realtime()
        items = list(_STUB_SUPPRESSED)
        if reason is not None:
            if reason not in _SUPPRESSION_FILTERS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown suppression filter {reason!r}",
                )
            items = [row for row in items if row["suppression_reason"] == reason]
        surfaced = len(self._attention_state().needs_you)
        suppressed = self._attention_state().can_wait_summary
        suppressed_count = suppressed.total_suppressed if suppressed else 0
        return {
            "developer_only": True,
            "filters": list(_SUPPRESSION_FILTERS),
            "filter": reason,
            "signals_considered": surfaced + suppressed_count,
            "surfaced_count": surfaced,
            "suppressed_count": suppressed_count,
            "sample_count": len(items),
            "items": items,
            "simulated_time": self.clock.now().isoformat(),
        }

    def apply_attention_action(
        self,
        item_id: str,
        action: Literal["done", "snooze"],
    ) -> dict[str, Any]:
        state = self._attention_state()
        known_ids = {row.id for row in state.needs_you} | {row.id for row in state.context}
        if item_id not in known_ids:
            raise HTTPException(status_code=404, detail=f"Unknown attention item {item_id}")
        self.action_log.append(
            {
                "item_id": item_id,
                "action": action,
                "at": self.clock.now().isoformat(),
            }
        )
        payload = self.attention_payload()
        return {
            "ok": True,
            "item_id": item_id,
            "action": action,
            "items": payload["items"],
            "surfaced_count": payload["surfaced_count"],
            "suppressed_count": payload["suppressed_count"],
        }

    def _forensic_provenance_payload(self) -> dict[str, Any]:
        mode = environment_mode_from_env()
        return session_forensic_provenance(
            environment=mode.value,
            session_started=self.session_started.isoformat(),
            scenario=self.scenario,
            checkpoint_id=self.checkpoint_id,
        )

    def conversation_payload(self) -> dict[str, Any]:
        self.sync_realtime()
        return {
            "items": list(self.conversation),
            "simulated_time": self.clock.now().isoformat(),
            "checkpoint_id": self.checkpoint_id,
            "forensic_provenance": self._forensic_provenance_payload(),
        }

    def events_payload(self) -> dict[str, Any]:
        return {
            "events": list(self.event_log[-50:]),
            "semantic_events": [row.public_view() for row in self.semantic_events[-100:]],
            "agent_work": [row.public_view() for row in self.agent_work.values()],
            "effects": [row.public_view() for row in self.effect_records.values()],
        }

    def _rebuild_event_spine_indexes(self) -> None:
        """Rebuild dedupe indexes from retained semantic events and work ledger.

        Supports process reconstruction when in-memory maps are lost but the
        append-only semantic event log and agent-work records survive.
        """
        self.processed_event_ids.clear()
        self.agent_work_by_subject.clear()
        for work in self.agent_work.values():
            self.agent_work_by_subject[work.subject_id] = work.work_id
        for event in self.semantic_events:
            if event.duplicate_of is not None:
                continue
            if event.kind not in {"source.event_detected", "world.dependency_arrived"}:
                continue
            if event.work_id is None:
                continue
            self.processed_event_ids[event.event_id] = event.work_id

    def _append_semantic_event(
        self,
        kind: SemanticEventKind,
        *,
        at: str,
        event_id: str | None = None,
        subject_id: str | None = None,
        work_id: str | None = None,
        effect_id: str | None = None,
        dependency_key: str | None = None,
        caused_by: tuple[str, ...] = (),
        payload: dict[str, Any] | None = None,
        duplicate_of: str | None = None,
    ) -> SemanticEvent:
        record = SemanticEvent(
            event_id=event_id or f"evt-{uuid4().hex[:12]}",
            kind=kind,
            at=at,
            subject_id=subject_id,
            work_id=work_id,
            effect_id=effect_id,
            dependency_key=dependency_key,
            caused_by=caused_by,
            payload=payload or {},
            duplicate_of=duplicate_of,
        )
        self.semantic_events.append(record)
        return record

    def _resolve_subject_title(self, subject_id: str) -> str:
        state = self._attention_state()
        for item in state.needs_you + state.context:
            if item.id == subject_id:
                return item.title
        for action in state.next_actions:
            if action.id == subject_id or action.source_candidate_id == subject_id:
                return action.title
        return subject_id

    def _ensure_agent_work(
        self,
        *,
        subject_id: str,
        at: str,
        cause_event_id: str,
        title: str | None = None,
    ) -> AgentWork:
        existing_id = self.agent_work_by_subject.get(subject_id)
        if existing_id is not None:
            work = self.agent_work[existing_id]
            if cause_event_id not in work.causal_event_ids:
                work.causal_event_ids.append(cause_event_id)
            return work
        work_id = f"work-{uuid4().hex[:12]}"
        work = AgentWork(
            work_id=work_id,
            subject_id=subject_id,
            title=title or self._resolve_subject_title(subject_id),
            status="DETECTED",
            causal_event_ids=[cause_event_id],
        )
        self.agent_work[work_id] = work
        self.agent_work_by_subject[subject_id] = work_id
        self._append_semantic_event(
            "work.created",
            at=at,
            subject_id=subject_id,
            work_id=work_id,
            caused_by=(cause_event_id,),
            payload={"status": work.status, "title": work.title},
        )
        return work

    def receive_source_event(
        self,
        *,
        event_id: str,
        subject_id: str,
        at: str | None = None,
        title: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AgentWork:
        stamp = at or self.clock.now().isoformat()
        duplicate = self.processed_event_ids.get(event_id)
        if duplicate is not None:
            work = self.agent_work[duplicate]
            self._append_semantic_event(
                "source.event_detected",
                at=stamp,
                event_id=f"{event_id}-duplicate-{len(self.semantic_events)}",
                subject_id=subject_id,
                work_id=work.work_id,
                payload=payload or {},
                duplicate_of=event_id,
            )
            return work
        incoming = self._append_semantic_event(
            "source.event_detected",
            at=stamp,
            event_id=event_id,
            subject_id=subject_id,
            payload=payload or {},
        )
        work = self._ensure_agent_work(
            subject_id=subject_id,
            at=stamp,
            cause_event_id=incoming.event_id,
            title=title,
        )
        self.processed_event_ids[event_id] = work.work_id
        return work

    def advance_agent_work(self, work_id: str, *, at: str | None = None) -> AgentWork:
        work = self.agent_work[work_id]
        work.status = "INVESTIGATING"
        self._append_semantic_event(
            "work.investigating",
            at=at or self.clock.now().isoformat(),
            subject_id=work.subject_id,
            work_id=work.work_id,
            caused_by=tuple(work.causal_event_ids[-1:]),
            payload={"status": work.status},
        )
        return work

    def wait_for_dependency(
        self,
        work_id: str,
        *,
        dependency_key: str,
        at: str | None = None,
    ) -> AgentWork:
        work = self.agent_work[work_id]
        work.status = "WAITING_EXTERNAL"
        work.dependency_key = dependency_key
        self._append_semantic_event(
            "work.waiting_external",
            at=at or self.clock.now().isoformat(),
            subject_id=work.subject_id,
            work_id=work.work_id,
            dependency_key=dependency_key,
            caused_by=tuple(work.causal_event_ids[-1:]),
            payload={"status": work.status},
        )
        return work

    def link_assist_to_work(
        self,
        *,
        proposal_id: str,
        subject_id: str,
        at: str | None = None,
    ) -> AgentWork:
        work = self._ensure_agent_work(
            subject_id=subject_id,
            at=at or self.clock.now().isoformat(),
            cause_event_id=f"proposal-{proposal_id}",
        )
        work.pending_proposal_id = proposal_id
        if work.status not in {"EXECUTING", "VERIFYING", "HANDLED"}:
            work.status = "READY_FOR_USER"
            self._append_semantic_event(
                "work.ready_for_user",
                at=at or self.clock.now().isoformat(),
                subject_id=work.subject_id,
                work_id=work.work_id,
                caused_by=tuple(work.causal_event_ids[-1:]),
                payload={"status": work.status, "proposal_id": proposal_id},
            )
        return work

    def receive_dependency_event(
        self,
        *,
        event_id: str,
        subject_id: str,
        dependency_key: str,
        proposal_id: str | None = None,
        at: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AgentWork:
        stamp = at or self.clock.now().isoformat()
        work = self._ensure_agent_work(
            subject_id=subject_id,
            at=stamp,
            cause_event_id=event_id,
        )
        if event_id in self.processed_event_ids:
            self._append_semantic_event(
                "world.dependency_arrived",
                at=stamp,
                event_id=f"{event_id}-duplicate-{len(self.semantic_events)}",
                subject_id=subject_id,
                work_id=work.work_id,
                dependency_key=dependency_key,
                payload=payload or {},
                duplicate_of=event_id,
            )
            return work
        dependency_event = self._append_semantic_event(
            "world.dependency_arrived",
            at=stamp,
            event_id=event_id,
            subject_id=subject_id,
            work_id=work.work_id,
            dependency_key=dependency_key,
            payload=payload or {},
        )
        self.processed_event_ids[event_id] = work.work_id
        if dependency_event.event_id not in work.causal_event_ids:
            work.causal_event_ids.append(dependency_event.event_id)
        if proposal_id is not None:
            work.pending_proposal_id = proposal_id
        dependency_matches = (
            work.dependency_key is not None and work.dependency_key == dependency_key
        )
        if (
            work.status == "WAITING_EXTERNAL"
            and work.effect_id is None
            and dependency_matches
        ):
            work.status = "READY_FOR_USER"
            self._append_semantic_event(
                "work.ready_for_user",
                at=stamp,
                subject_id=subject_id,
                work_id=work.work_id,
                dependency_key=dependency_key,
                caused_by=(dependency_event.event_id,),
                payload={
                    "status": work.status,
                    "proposal_id": work.pending_proposal_id,
                },
            )
        return work

    def _work_for_proposal(self, proposal_id: str, *, subject_id: str) -> AgentWork:
        effect_id = self.effect_by_proposal.get(proposal_id)
        if effect_id is not None:
            return self.agent_work[self.effect_records[effect_id].work_id]
        for work in self.agent_work.values():
            if work.pending_proposal_id == proposal_id:
                return work
        return self.link_assist_to_work(proposal_id=proposal_id, subject_id=subject_id)

    def _effect_for_plan(self, plan: AssistPlan, work: AgentWork) -> AgentEffectRecord:
        effect_id = self.effect_by_proposal.get(plan.proposal_id)
        if effect_id is not None:
            effect = self.effect_records[effect_id]
            work.effect_id = effect.effect_id
            return effect
        effect = AgentEffectRecord(
            effect_id=f"effect-{uuid4().hex[:12]}",
            proposal_id=plan.proposal_id,
            work_id=work.work_id,
            subject_id=plan.source_item_id,
            status="PENDING_USER",
        )
        self.effect_records[effect.effect_id] = effect
        self.effect_by_proposal[plan.proposal_id] = effect.effect_id
        work.effect_id = effect.effect_id
        return effect

    def start_assist_execution(self, proposal_id: str) -> AssistExecution:
        at = self.clock.now().isoformat()
        plan = self.pending_assists.get(proposal_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Unknown assist proposal {proposal_id}")
        work = self._work_for_proposal(proposal_id, subject_id=plan.source_item_id)
        work.pending_proposal_id = proposal_id
        work.status = "EXECUTING"
        approved = self._append_semantic_event(
            "conversation.user_approved_effect",
            at=at,
            subject_id=plan.source_item_id,
            work_id=work.work_id,
            caused_by=tuple(work.causal_event_ids[-1:]),
            payload={"proposal_id": proposal_id},
        )
        effect = self._effect_for_plan(plan, work)
        if effect.status in {"EXECUTED", "VERIFIED"} and effect.execution_id is not None:
            return AssistExecution(
                execution_id=effect.execution_id,
                artifact_kind="calendar_event"
                if effect.artifact_kind == "calendar_event"
                else "note",
                artifact_id=effect.artifact_id or "",
                payload={},
            )
        execution = execute_assist(plan, self.synthetic_services)
        effect.status = "EXECUTED"
        effect.execution_id = execution.execution_id
        effect.execution_count += 1
        effect.artifact_id = execution.artifact_id
        effect.artifact_kind = execution.artifact_kind
        work.status = "VERIFYING"
        self._append_semantic_event(
            "effect.executed",
            at=at,
            subject_id=plan.source_item_id,
            work_id=work.work_id,
            effect_id=effect.effect_id,
            caused_by=(approved.event_id,),
            payload={
                "proposal_id": proposal_id,
                "execution_id": execution.execution_id,
                "artifact_id": execution.artifact_id,
                "artifact_kind": execution.artifact_kind,
            },
        )
        return execution

    def verify_assist_effect(self, proposal_id: str, execution: AssistExecution) -> dict[str, Any]:
        at = self.clock.now().isoformat()
        plan = self.pending_assists.get(proposal_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Unknown assist proposal {proposal_id}")
        work = self._work_for_proposal(proposal_id, subject_id=plan.source_item_id)
        effect = self._effect_for_plan(plan, work)
        ok, message = verify_assist_execution(plan, self.synthetic_services, execution)
        effect.verification_count += 1
        if ok:
            effect.status = "VERIFIED"
            self._append_semantic_event(
                "effect.verified",
                at=at,
                subject_id=plan.source_item_id,
                work_id=work.work_id,
                effect_id=effect.effect_id,
                caused_by=(execution.execution_id,),
                payload={"proposal_id": proposal_id, "verified": True},
            )
            apply_verified_assist_effect(
                plan,
                completed_item_ids=self.completed_item_ids,
                advances=self.assist_advances,
            )
            work.status = "HANDLED"
            self._append_semantic_event(
                "work.handled",
                at=at,
                subject_id=plan.source_item_id,
                work_id=work.work_id,
                effect_id=effect.effect_id,
                caused_by=(execution.execution_id,),
                payload={"status": work.status},
            )
            self._last_attention_fingerprint = self._attention_fingerprint()
            reconcile_action_focus(self.conversation_context, self._attention_state())
        else:
            effect.status = "FAILED"
        result = assist_result_item(
            proposal_id=proposal_id,
            ok=ok,
            message=message,
            at=at,
        )
        self.executed_assists[proposal_id] = result
        self.pending_assists.pop(proposal_id, None)
        return result

    def handle_message(self, text: str) -> dict[str, Any]:
        self.sync_realtime()
        at = self.clock.now().isoformat()
        corr = f"corr-{uuid4().hex}"
        self.conversation.append(
            {"kind": "user_message", "text": text, "at": at, "correlation_id": corr}
        )
        state = self._attention_state()
        reconcile_action_focus(self.conversation_context, state)
        conversation_state = {
            "current_subject_id": self.conversation_context.current_subject_id,
            "current_subject_kind": self.conversation_context.current_subject_kind,
        }
        last_intent = self.conversation_context.last_intent

        if demo_llm_conversation_enabled():
            frozen = project_checkpoint(self.checkpoint_id).state
            tool_session = DemoToolSession(
                state=state,
                context=self.conversation_context,
                checkpoint_id=self.checkpoint_id,
                prior_state=self._prior_attention_state(),
                at=at,
                conversation=self.conversation,
                completed_item_ids=self.completed_item_ids,
                pending_assists=self.pending_assists,
                synthetic_services=self.synthetic_services,
                user_message=text,
                assist_advances=self.assist_advances,
                attestations=self.attestations,
                chat_index=self.chat_index,
                base_state=frozen,
            )
            orchestrated = run_orchestrator_turn(
                user_message=text,
                session=tool_session,
                correlation_id=corr,
            )
            turn_items = orchestrated.turn_items
            plan = orchestrated.assist_plan
            trace = orchestrated.llm_trace or build_intent_router_trace(
                user_message=text,
                conversation_state=conversation_state,
                last_intent=last_intent,
                turn_items=turn_items,
                correlation_id=corr,
            )
        else:
            turn_items, plan = build_intent_turn(
                text,
                state,
                at=at,
                checkpoint_id=self.checkpoint_id,
                prior_state=self._prior_attention_state(),
                conversation=self.conversation,
                completed_item_ids=self.completed_item_ids,
                conversation_context=self.conversation_context,
            )
            turn_items = [
                item if item.get("correlation_id") else {**item, "correlation_id": corr}
                for item in turn_items
            ]
            trace = build_intent_router_trace(
                user_message=text,
                conversation_state=conversation_state,
                last_intent=last_intent,
                turn_items=turn_items,
                correlation_id=corr,
            )

        if plan is not None:
            self.pending_assists[plan.proposal_id] = plan
            self.link_assist_to_work(
                proposal_id=plan.proposal_id,
                subject_id=plan.source_item_id,
                at=at,
            )

        mode = environment_mode_from_env()
        trace = attach_forensic_provenance(
            trace,
            environment=mode.value,
            session_started=self.session_started.isoformat(),
            scenario=self.scenario,
            checkpoint_id=self.checkpoint_id,
        )
        payload = trace.model_dump(mode="json") if isinstance(trace, LlmTrace) else trace
        if turn_items:
            turn_items[0] = {**turn_items[0], "llm_trace": payload}

        self.conversation.extend(turn_items)
        update_context_from_turn_items(self.conversation_context, turn_items)
        reconcile_action_focus(self.conversation_context, self._attention_state())
        return {
            "items": turn_items,
            "conversation": self.conversation_payload(),
            "llm_trace": payload,
            "debug": payload,
            "forensic_provenance": self._forensic_provenance_payload(),
        }

    def approve_assist(self, proposal_id: str) -> dict[str, Any]:
        self.sync_realtime()
        previous = self.executed_assists.get(proposal_id)
        if previous is not None:
            return previous
        execution = self.start_assist_execution(proposal_id)
        result = self.verify_assist_effect(proposal_id, execution)
        self.conversation.append(result)
        return result


_LOCK_TYPE = type(Lock())


def _require_demo() -> None:
    if environment_mode_from_env() is not EnvironmentMode.DEMO:
        raise HTTPException(
            status_code=409,
            detail="Demo timeline controls require ENIGMA_ENVIRONMENT_MODE=demo",
        )


def _assert_demo_reset_root(root: Path, *, scenario_id: str) -> None:
    """Refuse Private/Shadow roots; require a per-scenario Demo directory."""
    resolved = root.expanduser().resolve()
    try:
        assert_demo_storage_root(resolved, scenario_id=scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    for mode, label in (
        (EnvironmentMode.PRIVATE, "Private"),
        (EnvironmentMode.SHADOW, "Shadow"),
    ):
        foreign = storage_root_for(mode).expanduser().resolve()
        # Refuse when Demo root is Private/Shadow, nested under them, or when
        # Private/Shadow is nested under the Demo wipe target (misconfig).
        if (
            resolved == foreign
            or foreign in resolved.parents
            or resolved in foreign.parents
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Refusing to reset {label} storage root "
                    f"(ADR-005); got {resolved}"
                ),
            )


def _dispose_demo_db_engine(application: FastAPI) -> None:
    engine = getattr(application.state, "demo_db_engine", None)
    if engine is not None:
        engine.dispose()
        application.state.demo_db_engine = None


def _session_for(application: FastAPI) -> DemoSession:
    session = getattr(application.state, "demo_session", None)
    if not isinstance(session, DemoSession):
        session = DemoSession()
        application.state.demo_session = session
    return session


def _lock_for(application: FastAPI) -> Any:
    lock = getattr(application.state, "demo_session_lock", None)
    if not isinstance(lock, _LOCK_TYPE):
        lock = Lock()
        application.state.demo_session_lock = lock
    return lock


def install_demo_routes(application: FastAPI) -> None:
    """Register ``/demo/*`` banner, status, timeline, and UI stub routes.

    Timeline clock state lives on ``application.state`` (per app / process) and
    mutations are serialised with a lock so overlapping advances stay atomic
    within one worker.
    """

    application.state.demo_session = DemoSession()
    application.state.demo_session_lock = Lock()

    @application.get("/demo/banner")
    def demo_banner() -> dict[str, str | bool]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
        return {
            "active": active,
            "mode": mode.value,
            "text": DEMO_BANNER_TEXT if active else "",
        }

    @application.get("/demo/environment")
    def demo_environment(scenario: str = "alex-v1") -> dict[str, str | None]:
        mode = environment_mode_from_env()
        if mode is EnvironmentMode.DEMO:
            env = DemoEnvironment(scenario=scenario)
            return {
                "mode": env.mode.value,
                "scenario": env.scenario,
                "banner": env.banner_text,
                "storage_root": str(env.storage_root),
            }
        return {
            "mode": mode.value,
            "scenario": None,
            "banner": None,
            "storage_root": None,
        }

    @application.get("/demo/status")
    def demo_status() -> dict[str, Any]:
        with _lock_for(application):
            return _session_for(application).status_payload()

    @application.post("/demo/timeline/step")
    def demo_timeline_step() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            # Without D5 event queue, step advances one simulated hour.
            session.advance_step()
            return session.status_payload()

    @application.post("/demo/timeline/day")
    def demo_timeline_day() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            session.advance_day()
            return session.status_payload()

    @application.post("/demo/timeline/speed")
    def demo_timeline_speed(body: SpeedBody) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            session.set_speed(body.speed)
            return session.status_payload()

    @application.post("/demo/reset")
    def demo_reset() -> dict[str, Any]:
        """Wipe Demo storage for the active scenario and reseed a fresh run."""
        _require_demo()
        with _lock_for(application):
            _dispose_demo_db_engine(application)
            return _session_for(application).reset()

    @application.post("/demo/timeline/reset")
    def demo_timeline_reset() -> dict[str, Any]:
        """Alias of ``POST /demo/reset`` (clock + Demo storage wipe + bootstrap)."""
        _require_demo()
        with _lock_for(application):
            _dispose_demo_db_engine(application)
            return _session_for(application).reset()

    @application.get("/demo/attention/state")
    def demo_attention_state() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).attention_state_payload()

    @application.get("/demo/attention/{item_id}/qualification-debug")
    def demo_qualification_debug(item_id: str) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            try:
                debug = qualification_debug_payload(session.checkpoint_id, item_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=f"Unknown item {item_id}") from exc
            return debug.model_dump(mode="json")

    @application.get("/demo/checkpoints")
    def demo_checkpoints() -> dict[str, Any]:
        _require_demo()
        return {"checkpoints": list_demo_checkpoints()}

    @application.post("/demo/timeline/checkpoint/{checkpoint_id}")
    def demo_timeline_checkpoint(checkpoint_id: str) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            try:
                session.jump_checkpoint(checkpoint_id)
            except Exception as exc:  # noqa: BLE001 — surface bad checkpoint ids
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            payload = session.status_payload()
            payload["attention"] = session.attention_state_payload()
            payload["events"] = session.events_payload()["events"][-1:]
            return payload

    @application.get("/demo/conversation")
    def demo_conversation() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).conversation_payload()

    @application.post("/demo/conversation/message")
    def demo_conversation_message(body: MessageBody) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).handle_message(body.text)

    @application.get("/demo/events")
    def demo_events() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).events_payload()

    @application.post("/demo/assist/{proposal_id}/approve")
    def demo_assist_approve(proposal_id: str) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).approve_assist(proposal_id)

    @application.get("/demo/attention")
    def demo_attention() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).attention_payload()

    @application.post("/demo/attention/{item_id}/done")
    def demo_attention_done(item_id: str) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).apply_attention_action(item_id, "done")

    @application.post("/demo/attention/{item_id}/snooze")
    def demo_attention_snooze(item_id: str) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            return _session_for(application).apply_attention_action(item_id, "snooze")

    @application.get("/demo/memory")
    def demo_memory() -> dict[str, Any]:
        _require_demo()
        categories = sorted({m["category"] for m in _STUB_MEMORY})
        return {
            "categories": categories,
            "items": list(_STUB_MEMORY),
        }

    @application.get("/demo/suppressed")
    def demo_suppressed(reason: str | None = None) -> dict[str, Any]:
        """Developer-only suppression inspector (not product chrome)."""
        _require_demo()
        with _lock_for(application):
            return _session_for(application).suppressed_payload(reason)

    @application.get("/demo/why/{item_id}")
    def demo_why(item_id: str) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            payload = _STUB_WHY.get(item_id)
            if payload is not None:
                return payload
            try:
                debug = qualification_debug_payload(session.checkpoint_id, item_id)
            except KeyError as exc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown attention item {item_id}",
                ) from exc
            state = session._attention_state()
            item = next(
                (row for row in state.needs_you + state.context if row.id == item_id),
                None,
            )
            title = item.title if item else item_id
            return {
                "item_id": item_id,
                "title": title,
                "headline": "WHY ENIGMA HOLDS THIS",
                "evidence": item.evidence_ids if item else [],
                "inference": [
                    f"Composite score {debug.composite_score:.3f} vs surface threshold "
                    f"{debug.surface_threshold:.2f}.",
                    f"Policy decision: {debug.policy_decision}.",
                ],
                "decision": [
                    "Qualification is authoritative — not derived from rank or presentation.",
                ],
                "why_now": [item.explanation if item else "See qualification debug."],
                "confidence": debug.confidence,
                "reason_codes": debug.reason_codes,
            }
