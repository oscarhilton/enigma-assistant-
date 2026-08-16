"""Demo Mode environment, timeline, and live attention routes (D1 + D10 + D13 + D14).

Attention is derived from alex-v1 synthetic sources through the obligations /
heuristic attention path. Memory browser stubs remain until a later ticket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from personal_enigma.api.routes.demo_attention import (
    background_profile_from_env,
    build_session_background,
    load_demo_scenario,
    refresh_attention_payloads,
)
from personal_enigma.simulation import (
    DEMO_BANNER_TEXT,
    DemoEnvironment,
    EnvironmentMode,
    ScenarioPackage,
    SimulationClock,
    environment_mode_from_env,
)
from personal_enigma.simulation.corpus.background import BackgroundBuildResult

# Fallback only if a scenario package has no start_at.
_DEMO_EPOCH = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)

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


class SpeedBody(BaseModel):
    speed: float = Field(ge=0.0, le=1000.0)


@dataclass
class DemoSession:
    """In-process Demo clock + live attention session for UI timeline controls.

    Attention is recomputed from the scenario package filtered by simulated
    ``until`` (D02 clock). SimulationEngine checkpoint I/O is intentionally
    skipped here so interactive Demo UI stays lightweight; eval/CLI still
    owns full engine replay.
    """

    scenario: str = "alex-v1"
    speed: float = 0.0
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    why_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    suppressed_count: int = 0
    action_log: list[dict[str, Any]] = field(default_factory=list)
    dismissed_ids: set[str] = field(default_factory=set)
    package: ScenarioPackage | None = None
    background: BackgroundBuildResult | None = None
    background_profile: str = field(default_factory=background_profile_from_env)
    env: DemoEnvironment = field(init=False)

    def __post_init__(self) -> None:
        self._bootstrap_empty()

    def _bootstrap_empty(self) -> None:
        """Lightweight session shell — scenario pipeline loads on first demo use."""
        clock = SimulationClock(initial=_DEMO_EPOCH)
        self.env = DemoEnvironment(scenario=self.scenario, clock=clock)
        self.package = None
        self.background = None
        self.speed = 0.0
        self.clock.pause()
        self.attention_items = []
        self.why_by_id = {}
        self.suppressed_count = 0
        self.action_log = []
        self.dismissed_ids = set()

    def ensure_pipeline(self) -> None:
        if self.package is None:
            self.reset()

    def reset(self) -> None:
        self.package = load_demo_scenario(self.scenario)
        initial = self.package.manifest.start_at or _DEMO_EPOCH
        clock = SimulationClock(initial=initial)
        clock.set_time(initial)
        clock.pause()
        self.env = DemoEnvironment(scenario=self.scenario, clock=clock)
        self.background_profile = background_profile_from_env()
        self.background = build_session_background(
            self.package,
            profile=self.background_profile,
        )
        # Start paused so operators use Next event/day or explicitly pick 1×–100×.
        self.speed = 0.0
        self.dismissed_ids = set()
        self.action_log = []
        self._refresh_attention()

    def _refresh_attention(self) -> None:
        if self.package is None:
            self.attention_items = []
            self.why_by_id = {}
            self.suppressed_count = 0
            return
        rows, why_by_id, suppressed = refresh_attention_payloads(
            self.package,
            until=self.clock.now(),
            background=self.background,
            dismissed_ids=self.dismissed_ids,
        )
        self.attention_items = rows
        self.why_by_id = why_by_id
        self.suppressed_count = suppressed

    @property
    def clock(self) -> SimulationClock:
        clock = self.env.clock
        if not isinstance(clock, SimulationClock):
            raise TypeError("Demo session requires SimulationClock")
        return clock

    def advance_step(self) -> None:
        """Advance one simulated hour.

        Uses ``set_time`` so manual Next-event / auto-play ticks still move
        the clock while speed is Pause (``clock.pause`` only freezes
        ``advance`` / ``advance_to``, not absolute jumps).
        """
        self.ensure_pipeline()
        self.clock.set_time(self.clock.now() + timedelta(hours=1))
        self._refresh_attention()

    def advance_day(self) -> None:
        """Advance one simulated day (works even while auto-play is paused)."""
        self.ensure_pipeline()
        self.clock.set_time(self.clock.now() + timedelta(days=1))
        self._refresh_attention()

    def status_payload(self) -> dict[str, Any]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
        if active:
            self.ensure_pipeline()
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
            "background_profile": self.background_profile if active else None,
            "live_attention": True if active else False,
        }

    def attention_payload(self) -> dict[str, Any]:
        self.ensure_pipeline()
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
            "live": True,
        }

    def why_payload(self, item_id: str) -> dict[str, Any]:
        self.ensure_pipeline()
        payload = self.why_by_id.get(item_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Unknown attention item {item_id}")
        return payload

    def apply_attention_action(
        self,
        item_id: str,
        action: Literal["done", "snooze"],
    ) -> dict[str, Any]:
        self.ensure_pipeline()
        remaining = [row for row in self.attention_items if row["id"] != item_id]
        if len(remaining) == len(self.attention_items):
            raise HTTPException(status_code=404, detail=f"Unknown attention item {item_id}")
        self.dismissed_ids.add(item_id)
        self.attention_items = remaining
        self.why_by_id.pop(item_id, None)
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
    """Register ``/demo/*`` banner, status, timeline, and live attention routes.

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
        with _lock_for(application):
            return _session_for(application).why_payload(item_id)
