"""Product world switcher (P01 / ADR-040).

Alex Lab and My Enigma share one API process and one app shell. They never share
storage roots or HMAC keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
    """Quiet My Enigma conversation until C08 / P03 connect real sources."""

    conversation: list[dict[str, Any]] = field(default_factory=list)

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
        self.conversation.append({"kind": "user_message", "text": text, "at": now})
        reply = {
            "kind": "enigma_message",
            "text": (
                "This is My Enigma. No private sources are connected yet, "
                "so there is nothing in this world to inspect."
            ),
            "at": now,
        }
        self.conversation.append(reply)
        return {"items": [reply], "conversation": self.conversation_payload()}


def _registry_home() -> Path | None:
    raw = os.environ.get("ENIGMA_HOME")
    return Path(raw) if raw else None


def _registry_for(application: FastAPI) -> WorldRegistry:
    registry = getattr(application.state, "world_registry", None)
    if not isinstance(registry, WorldRegistry):
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


def install_world_routes(application: FastAPI) -> None:
    """Register ``/worlds`` switcher and quiet My Enigma conversation stubs."""
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
            now = registry.active.clock.now().isoformat()
            return _private_session_for(application).attention_state_payload(now=now)

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
            now = registry.active.clock.now().isoformat()
            return _private_session_for(application).send_message(body.text, now=now)
