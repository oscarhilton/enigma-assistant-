"""Product world switcher (P01 / ADR-040).

Alex Lab and My Enigma share one API process and one app shell. They never share
storage roots or HMAC keys.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.private_calendar_read import build_calendar_provenance
from personal_enigma.api.private_calendar_store import (
    CalendarReadAdapter,
    calendar_adapter_for_root,
)
from personal_enigma.api.private_calendar_sync import sync_apple_calendar_to_store
from personal_enigma.api.private_conversation import handle_private_message
from personal_enigma.simulation import (
    WorldId,
    WorldIsolationError,
    WorldRegistry,
    parse_world_id,
)

_LOCK_TYPE = type(Lock())

WORLD_REQUIRE_DETAIL = {
    WorldId.ALEX_LAB: "Alex Lab",
    WorldId.MY_ENIGMA: "My Enigma",
}


class SwitchBody(BaseModel):
    world: str = Field(min_length=1, max_length=32)


class MessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@dataclass
class PrivateWorldSession:
    """My Enigma session — calendar READ + SUPPORT (P03)."""

    storage_root: Path | None = None
    conversation: list[dict[str, Any]] = field(default_factory=list)
    conversation_context: ConversationContext = field(default_factory=ConversationContext)
    calendar_adapter: CalendarReadAdapter | None = None
    last_calendar_facts: list[dict[str, Any]] = field(default_factory=list)

    def bind_storage(self, storage_root: Path) -> None:
        self.storage_root = storage_root
        self.calendar_adapter = calendar_adapter_for_root(storage_root)

    def clear_world_derived(self) -> None:
        """ADR-040 — calendar-derived conversation state must not survive a switch."""
        self.conversation = []
        self.conversation_context = ConversationContext()
        self.last_calendar_facts = []

    def _adapter(self) -> CalendarReadAdapter:
        if self.calendar_adapter is None:
            root = self.storage_root or Path(os.environ.get("ENIGMA_PRIVATE_STORAGE_ROOT", "."))
            self.bind_storage(root)
        assert self.calendar_adapter is not None
        return self.calendar_adapter

    def attention_state_payload(self, *, now: str) -> dict[str, Any]:
        return {
            "simulated_time": now,
            "checkpoint_id": None,
            "needs_you": [],
            "context": [],
            "next_actions": [],
            "can_wait_summary": None,
            "presentation": {
                "chat_opening_count": 0,
                "notification_slot_count": 0,
                "proactive_silence": True,
            },
        }

    def conversation_payload(self) -> dict[str, Any]:
        return {"items": list(self.conversation)}

    def send_message(self, text: str, *, now: str) -> dict[str, Any]:
        payload = handle_private_message(
            text=text,
            at=now,
            adapter=self._adapter(),
            conversation=self.conversation,
            context=self.conversation_context,
        )
        self.conversation = payload["conversation"]["items"]
        self.last_calendar_facts = list(payload.get("calendar_facts_used") or [])
        return payload

    def calendar_provenance_payload(self) -> dict[str, Any]:
        return build_calendar_provenance(self.last_calendar_facts)


def _registry_home() -> Path | None:
    raw = os.environ.get("ENIGMA_HOME")
    return Path(raw) if raw else None


def _registry_for(application: FastAPI) -> WorldRegistry:
    registry = getattr(application.state, "world_registry", None)
    if isinstance(registry, WorldRegistry):
        return registry
    registry = WorldRegistry(home=_registry_home())
    application.state.world_registry = registry
    return registry


def _lock_for(application: FastAPI) -> Any:
    lock = getattr(application.state, "world_registry_lock", None)
    if not isinstance(lock, _LOCK_TYPE):
        lock = Lock()
        application.state.world_registry_lock = lock
    return lock


def _private_session_for(application: FastAPI) -> PrivateWorldSession:
    session = getattr(application.state, "private_world_session", None)
    if not isinstance(session, PrivateWorldSession):
        session = PrivateWorldSession()
        application.state.private_world_session = session
    return session


def _reset_private_session(application: FastAPI, *, storage_root: Path | None = None) -> None:
    session = PrivateWorldSession()
    if storage_root is not None:
        session.bind_storage(storage_root)
    application.state.private_world_session = session


def _require_world(application: FastAPI, expected: WorldId) -> None:
    registry = _registry_for(application)
    if registry.active_id is not expected:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{WORLD_REQUIRE_DETAIL[expected]} is not the active world "
                f"(active={registry.active_id.value})"
            ),
        )


def alex_lab_is_active(application: FastAPI) -> bool:
    """True when the product switcher has selected Alex Lab."""
    try:
        return _registry_for(application).active_id is WorldId.ALEX_LAB
    except WorldIsolationError:
        return False



_TOOL_INSPECT_LABELS: dict[str, str] = {
    "availability.check": "Checked your calendar",
    "availability.time_fit": "Checked your calendar",
    "agenda.get": "Checked your week",
    "briefing.read": "Checked your week",
    "calendar.agenda.get": "Checked your calendar",
    "attention.get_current": "Checked what needs you",
    "context.resolve_referent": "Matched this to the token inventory",
    "world.explain": "Checked why this matters",
    "attention.explain_why": "Checked why this matters",
    "world.get_changes": "Checked what changed",
    "world.get_blockers": "Checked what you're waiting on",
    "next_action.get": "Checked what's worth doing",
    "next_action.get_alternatives": "Looked for something else",
    "next_action.reject": "Noted you'd rather not",
    "referent.get_duration": "Checked how long this takes",
    "assist.propose": "Prepared an action",
    "assist.approve": "Approved",
}


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _inspect_labels_from_payload(payload: dict[str, Any]) -> list[str]:
    trace = payload.get("llm_trace")
    if not isinstance(trace, dict):
        return []
    labels: list[str] = []
    hops = list(trace.get("executed_tool_request") or []) + list(
        trace.get("tool_results") or []
    )
    for hop in hops:
        if not isinstance(hop, dict):
            continue
        name = hop.get("name")
        if not isinstance(name, str):
            continue
        label = _TOOL_INSPECT_LABELS.get(name)
        if label and label not in labels:
            labels.append(label)
    return labels


def _agent_work_event(
    *,
    phase: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels: list[str] = []
    semantic = "in-flight" if phase == "in_flight" else "complete"
    if payload:
        trace = payload.get("llm_trace")
        if isinstance(trace, dict):
            turn_outcome = trace.get("turn_outcome")
            if isinstance(turn_outcome, dict):
                label = turn_outcome.get("agent_work_label")
                if isinstance(label, str) and label:
                    labels = [label]
                    semantic = label
        if not labels:
            labels = _inspect_labels_from_payload(payload)
            if labels:
                semantic = labels[0]
    return {
        "exists": True,
        "phase": phase,
        "semantic_token": semantic,
        "inspect_target": None,
        "inspect_labels": labels,
    }


def _prose_deltas(payload: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for item in payload.get("items") or []:
        if isinstance(item, dict) and item.get("kind") == "enigma_message":
            text = item.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
    deltas: list[str] = []
    for text in texts:
        words = text.split(" ")
        for index, word in enumerate(words):
            deltas.append(word if index == len(words) - 1 else f"{word} ")
    return [delta for delta in deltas if delta]


def _json_safe_turn(payload: dict[str, Any]) -> dict[str, Any]:
    """Omit ConversationContext — dataclasses are not JSON-safe on SSE."""
    return {
        key: payload[key]
        for key in ("items", "conversation", "llm_trace", "calendar_facts_used")
        if key in payload
    }


def install_world_routes(application: FastAPI) -> None:
    """Register ``/worlds`` switcher and My Enigma calendar READ routes."""
    application.state.world_registry_lock = Lock()
    application.state.world_registry = WorldRegistry(home=_registry_home())
    application.state.private_world_session = PrivateWorldSession()

    @application.get("/worlds")
    def list_worlds() -> dict[str, Any]:
        with _lock_for(application):
            try:
                return _registry_for(application).public_view()
            except WorldIsolationError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/worlds/active")
    def active_world() -> dict[str, Any]:
        with _lock_for(application):
            registry = _registry_for(application)
            try:
                registry.assert_isolated(require_keys=True)
            except WorldIsolationError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            view = registry.active.public_view()
            view["active"] = True
            return view

    @application.post("/worlds/switch")
    def switch_world(body: SwitchBody) -> dict[str, Any]:
        try:
            world = parse_world_id(body.world)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _lock_for(application):
            registry = _registry_for(application)
            try:
                handle = registry.switch(world)
            except WorldIsolationError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            # ADR-040 / P03 freeze — world-derived private state clears on every switch.
            private_root = Path(handle.storage_root) if world is WorldId.MY_ENIGMA else None
            if world is WorldId.MY_ENIGMA:
                _reset_private_session(application, storage_root=private_root)
            else:
                _reset_private_session(application)
            return {"ok": True, "active": handle.public_view()}

    @application.post("/worlds/{world_id}/reset")
    def reset_world(world_id: str) -> dict[str, Any]:
        try:
            world = parse_world_id(world_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _lock_for(application):
            registry = _registry_for(application)
            try:
                handle = registry.reset(world)
            except WorldIsolationError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            return {"ok": True, "reset": True, "world": handle.public_view()}

    @application.get("/worlds/my_enigma/attention/state")
    def my_enigma_attention() -> dict[str, Any]:
        _require_world(application, WorldId.MY_ENIGMA)
        with _lock_for(application):
            registry = _registry_for(application)
            session = _private_session_for(application)
            if session.storage_root is None:
                session.bind_storage(Path(registry.active.storage_root))
            now = registry.active.clock.now().isoformat()
            return session.attention_state_payload(now=now)

    @application.get("/worlds/my_enigma/conversation")
    def my_enigma_conversation() -> dict[str, Any]:
        _require_world(application, WorldId.MY_ENIGMA)
        with _lock_for(application):
            return _private_session_for(application).conversation_payload()

    @application.post("/worlds/my_enigma/conversation/message")
    def my_enigma_message(body: MessageBody) -> dict[str, Any]:
        _require_world(application, WorldId.MY_ENIGMA)
        with _lock_for(application):
            registry = _registry_for(application)
            session = _private_session_for(application)
            if session.storage_root is None:
                session.bind_storage(Path(registry.active.storage_root))
            now = registry.active.clock.now().isoformat()
            return session.send_message(body.text, now=now)


    @application.post("/worlds/my_enigma/conversation/message/stream")
    def my_enigma_message_stream(body: MessageBody) -> StreamingResponse:
        """SSE: agent_work and prose are independent channels (UI2-02 / C35)."""
        _require_world(application, WorldId.MY_ENIGMA)

        def event_stream() -> Iterator[str]:
            try:
                yield _sse("agent_work", _agent_work_event(phase="in_flight"))
                with _lock_for(application):
                    registry = _registry_for(application)
                    session = _private_session_for(application)
                    if session.storage_root is None:
                        session.bind_storage(Path(registry.active.storage_root))
                    now = registry.active.clock.now().isoformat()
                    payload = session.send_message(body.text, now=now)
                yield _sse(
                    "agent_work",
                    _agent_work_event(phase="complete", payload=payload),
                )
                for delta in _prose_deltas(payload):
                    yield _sse("prose", {"delta": delta})
                yield _sse("turn_complete", _json_safe_turn(payload))
            except Exception as exc:
                yield _sse("error", {"message": str(exc)})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @application.get("/worlds/my_enigma/calendar/provenance")
    def my_enigma_calendar_provenance() -> dict[str, Any]:
        _require_world(application, WorldId.MY_ENIGMA)
        with _lock_for(application):
            return _private_session_for(application).calendar_provenance_payload()

    @application.post("/worlds/my_enigma/calendar/sync")
    async def my_enigma_calendar_sync() -> dict[str, Any]:
        """Operator-triggered Apple calendar sync (P03c). Not an Assistant tool."""
        _require_world(application, WorldId.MY_ENIGMA)
        with _lock_for(application):
            registry = _registry_for(application)
            session = _private_session_for(application)
            storage_root = Path(registry.active.storage_root)
            if session.storage_root is None:
                session.bind_storage(storage_root)
            try:
                result = await sync_apple_calendar_to_store(storage_root)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            return {
                "ok": True,
                "event_count": result.event_count,
                "calendar_ids": list(result.calendar_ids),
                "synced_at": result.synced_at,
                "storage_root": result.storage_root,
            }
