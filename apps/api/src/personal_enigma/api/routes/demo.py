"""Demo Mode environment, timeline, and UI support routes (D1 + D10)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

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

_STUB_ATTENTION: list[dict[str, Any]] = [
    {
        "id": "att-atlas-review",
        "title": "Review Atlas proposal before Friday",
        "body": "Open loop from a prior commitment; deadline approaching.",
        "kind": "commitment",
        "score": 0.91,
        "reason_codes": ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
    },
    {
        "id": "att-follow-up",
        "title": "Follow up with PERSON_A on scheduling",
        "body": "Cross-source thread still unresolved.",
        "kind": "follow_up",
        "score": 0.72,
        "reason_codes": ["FOLLOW_UP_RECEIVED"],
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
            "Calendar: Review meeting Friday 15:00.",
        ],
        "inference": ["An unresolved commitment exists."],
        "decision": [
            "Deadline approaching within useful action window.",
            "Priority score: 0.91",
        ],
        "reason_codes": ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
    },
    "att-follow-up": {
        "item_id": "att-follow-up",
        "title": "Follow up with PERSON_A on scheduling",
        "headline": "WHY ENIGMA THINKS THIS MATTERS",
        "evidence": ["Cross-source thread still unresolved."],
        "inference": ["A follow-up remains open."],
        "decision": ["Surfaced at moderate priority."],
        "reason_codes": ["FOLLOW_UP_RECEIVED"],
    },
}


class SpeedBody(BaseModel):
    speed: float = Field(ge=0.0, le=1000.0)


@dataclass
class DemoSession:
    """In-process Demo clock session for UI timeline controls (pre-D5 engine)."""

    scenario: str = "alex-v1"
    speed: float = 1.0
    env: DemoEnvironment = field(init=False)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        clock = SimulationClock(initial=_DEMO_EPOCH)
        self.env = DemoEnvironment(scenario=self.scenario, clock=clock)
        self.speed = 1.0

    @property
    def clock(self) -> SimulationClock:
        clock = self.env.clock
        if not isinstance(clock, SimulationClock):
            raise TypeError("Demo session requires SimulationClock")
        return clock

    def status_payload(self) -> dict[str, Any]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
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
        }


_SESSION = DemoSession()
_SESSION_LOCK = Lock()


def _require_demo() -> None:
    if environment_mode_from_env() is not EnvironmentMode.DEMO:
        raise HTTPException(
            status_code=409,
            detail="Demo timeline controls require ENIGMA_ENVIRONMENT_MODE=demo",
        )


def install_demo_routes(application: FastAPI) -> None:
    """Register ``/demo/*`` banner, status, timeline, and UI stub routes.

    Timeline state is process-global for local Demo UI (one shared clock).
    Mutations are serialised with ``_SESSION_LOCK``. Multi-worker deployments
    each keep an independent clock — intentional for this pre-D5 stub.
    """

    application.state.demo_session = _SESSION
    application.state.demo_session_lock = _SESSION_LOCK

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
        with _SESSION_LOCK:
            return _SESSION.status_payload()

    @application.post("/demo/timeline/step")
    def demo_timeline_step() -> dict[str, Any]:
        _require_demo()
        # Without D5 event queue, step advances one simulated hour.
        with _SESSION_LOCK:
            _SESSION.clock.advance(timedelta(hours=1))
            return _SESSION.status_payload()

    @application.post("/demo/timeline/day")
    def demo_timeline_day() -> dict[str, Any]:
        _require_demo()
        with _SESSION_LOCK:
            _SESSION.clock.advance_days(1)
            return _SESSION.status_payload()

    @application.post("/demo/timeline/speed")
    def demo_timeline_speed(body: SpeedBody) -> dict[str, Any]:
        _require_demo()
        with _SESSION_LOCK:
            _SESSION.speed = body.speed
            if body.speed == 0:
                _SESSION.clock.pause()
            else:
                _SESSION.clock.resume()
            return _SESSION.status_payload()

    @application.post("/demo/timeline/reset")
    def demo_timeline_reset() -> dict[str, Any]:
        _require_demo()
        with _SESSION_LOCK:
            _SESSION.reset()
            return _SESSION.status_payload()

    @application.get("/demo/attention")
    def demo_attention() -> dict[str, Any]:
        _require_demo()
        with _SESSION_LOCK:
            simulated_time = _SESSION.clock.now().isoformat()
        return {
            "items": list(_STUB_ATTENTION),
            "simulated_time": simulated_time,
        }

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
