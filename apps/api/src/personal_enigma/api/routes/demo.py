"""Demo Mode environment, timeline, and UI support routes (D1 + D10 + D13).

Attention stubs use PRIVATE UI names on the dashboard (Maya, Atlas). Why stubs
may use MODEL VIEW pseudonyms (PERSON_A) so demos can contrast local vs remote.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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

# Fixed epoch so UI smoke tests are deterministic without D5 event engine.
_DEMO_EPOCH = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

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


@dataclass
class DemoSession:
    """In-process Demo clock session for UI timeline controls (pre-D5 engine)."""

    scenario: str = "alex-v1"
    speed: float = 1.0
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    suppressed_count: int = _DEFAULT_SUPPRESSED
    action_log: list[dict[str, Any]] = field(default_factory=list)
    env: DemoEnvironment = field(init=False)

    def __post_init__(self) -> None:
        # Session start reseeds in-memory state only — do not wipe on-disk demo
        # storage until an explicit reset control is invoked.
        self._reseed_session()

    def _reseed_session(self) -> None:
        clock = SimulationClock(initial=_DEMO_EPOCH)
        self.env = DemoEnvironment(scenario=self.scenario, clock=clock)
        self.speed = 1.0
        self.attention_items = deepcopy(_STUB_ATTENTION_BASE)
        self.suppressed_count = _DEFAULT_SUPPRESSED
        self.action_log = []

    def wipe_and_bootstrap_storage(self) -> Path:
        """Wipe the active scenario Demo root and write a fresh checkpoint.

        Refuses Private / Shadow roots (ADR-005). Never follows symlinks out of
        the demo tree (``reset_demo_storage`` unlinks symlinks instead).
        """
        root = storage_root_for(EnvironmentMode.DEMO, scenario=self.scenario)
        _assert_demo_reset_root(root, scenario_id=self.scenario)
        reset_demo_storage(root)
        return bootstrap_demo_storage(
            root,
            scenario=self.scenario,
            now=_DEMO_EPOCH,
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

    def status_payload(self) -> dict[str, Any]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
        # D10 compression stats: signals considered vs surfaced / suppressed.
        surfaced = len(self.attention_items) if active else None
        suppressed = self.suppressed_count if active else None
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
            "speed": self.speed if active else None,
            "paused": self.clock.paused if active else None,
            "storage_root": str(self.env.storage_root) if active else None,
            "ground_truth_visible": False,
            "signals_considered": considered,
            "surfaced_count": surfaced,
            "suppressed_count": suppressed,
            "noise_suppressed_count": suppressed,
        }

    def attention_payload(self) -> dict[str, Any]:
        items = sorted(
            self.attention_items,
            key=lambda row: float(row["attention_rank"]),
            reverse=True,
        )
        surfaced = len(items)
        return {
            "items": items,
            "simulated_time": self.clock.now().isoformat(),
            "signals_considered": surfaced + self.suppressed_count,
            "surfaced_count": surfaced,
            "suppressed_count": self.suppressed_count,
        }

    def suppressed_payload(self, reason: str | None = None) -> dict[str, Any]:
        """Developer-only inspector — never expose ScenarioSignalClass labels."""
        items = list(_STUB_SUPPRESSED)
        if reason is not None:
            if reason not in _SUPPRESSION_FILTERS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown suppression filter {reason!r}",
                )
            items = [row for row in items if row["suppression_reason"] == reason]
        surfaced = len(self.attention_items)
        return {
            "developer_only": True,
            "filters": list(_SUPPRESSION_FILTERS),
            "filter": reason,
            "signals_considered": surfaced + self.suppressed_count,
            "surfaced_count": surfaced,
            "suppressed_count": self.suppressed_count,
            "sample_count": len(items),
            "items": items,
            "simulated_time": self.clock.now().isoformat(),
        }

    def apply_attention_action(
        self,
        item_id: str,
        action: Literal["done", "snooze"],
    ) -> dict[str, Any]:
        remaining = [row for row in self.attention_items if row["id"] != item_id]
        if len(remaining) == len(self.attention_items):
            raise HTTPException(status_code=404, detail=f"Unknown attention item {item_id}")
        self.attention_items = remaining
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
            session.clock.advance(timedelta(hours=1))
            return session.status_payload()

    @application.post("/demo/timeline/day")
    def demo_timeline_day() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            session.clock.advance_days(1)
            return session.status_payload()

    @application.post("/demo/timeline/speed")
    def demo_timeline_speed(body: SpeedBody) -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            session.speed = body.speed
            if body.speed == 0:
                session.clock.pause()
            else:
                session.clock.resume()
            return session.status_payload()

    @application.post("/demo/reset")
    def demo_reset() -> dict[str, Any]:
        """Wipe Demo storage for the active scenario and reseed a fresh run."""
        _require_demo()
        with _lock_for(application):
            return _session_for(application).reset()

    @application.post("/demo/timeline/reset")
    def demo_timeline_reset() -> dict[str, Any]:
        """Alias of ``POST /demo/reset`` (clock + Demo storage wipe + bootstrap)."""
        _require_demo()
        with _lock_for(application):
            return _session_for(application).reset()

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
        payload = _STUB_WHY.get(item_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Unknown attention item {item_id}")
        return payload
