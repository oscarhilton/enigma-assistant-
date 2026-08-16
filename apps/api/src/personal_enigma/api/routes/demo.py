"""Demo Mode environment, timeline, and UI support routes (D1 + D10 + D13).

Attention stubs use PRIVATE UI names on the dashboard (Maya, Atlas). Why stubs
may use MODEL VIEW pseudonyms (PERSON_A) so demos can contrast local vs remote.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
)

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
        self.reset()

    def reset(self) -> None:
        clock = SimulationClock(initial=_DEMO_EPOCH)
        self.env = DemoEnvironment(scenario=self.scenario, clock=clock)
        self.speed = 1.0
        self.attention_items = deepcopy(_STUB_ATTENTION_BASE)
        self.suppressed_count = _DEFAULT_SUPPRESSED
        self.action_log = []

    @property
    def clock(self) -> SimulationClock:
        clock = self.env.clock
        if not isinstance(clock, SimulationClock):
            raise TypeError("Demo session requires SimulationClock")
        return clock

    def status_payload(self) -> dict[str, Any]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
        # D10-style compression stats on status (surfaced vs suppressed / noise).
        surfaced = len(self.attention_items) if active else None
        suppressed = self.suppressed_count if active else None
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
        return {
            "items": items,
            "simulated_time": self.clock.now().isoformat(),
            "surfaced_count": len(items),
            "suppressed_count": self.suppressed_count,
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

    @application.post("/demo/timeline/reset")
    def demo_timeline_reset() -> dict[str, Any]:
        _require_demo()
        with _lock_for(application):
            session = _session_for(application)
            session.reset()
            return session.status_payload()

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

    @application.get("/demo/why/{item_id}")
    def demo_why(item_id: str) -> dict[str, Any]:
        _require_demo()
        payload = _STUB_WHY.get(item_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Unknown attention item {item_id}")
        return payload
