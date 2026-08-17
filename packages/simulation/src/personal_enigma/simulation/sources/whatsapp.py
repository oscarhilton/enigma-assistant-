"""Synthetic WhatsApp DataSource — scenario events → PrivateChatMessage (D19).

Adapters stop at the source layer. World-model items are derived downstream.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from personal_enigma.domain import PrivateChatMessage, PrivatePersonRef
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources import (
    _aware,
    batch_from_items,
    cursor_index,
    events_for_source,
    package_events,
    stable_id,
)

_CHAT_EVENT_TYPES = frozenset(
    {"whatsapp.receive", "whatsapp.send", "whatsapp.reaction"}
)


def _ref(
    value: Any,
    *,
    name: str | None = None,
    phone: str | None = None,
) -> PrivatePersonRef | None:
    if isinstance(value, dict):
        return PrivatePersonRef(
            display_name=value.get("display_name") or value.get("name") or name,
            email=value.get("email"),
            phone=value.get("phone") or phone,
            provider_id=value.get("provider_id") or value.get("id"),
        )
    if value is None and not name and not phone:
        return None
    text = None if value is None else str(value)
    looks_phone = bool(text and text[:1] in {"+", "0"} and any(ch.isdigit() for ch in text))
    return PrivatePersonRef(
        display_name=name if not looks_phone else name,
        phone=phone or (text if looks_phone else None),
        provider_id=None if looks_phone else text,
    )


def _refs(value: Any) -> list[PrivatePersonRef]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[PrivatePersonRef] = []
        for item in value:
            ref = _ref(item)
            if ref is not None:
                out.append(ref)
        return out
    ref = _ref(value)
    return [ref] if ref is not None else []


def _kind_for(
    event: ScenarioEvent, payload: dict[str, Any]
) -> Literal["text", "reaction", "system"]:
    raw = str(payload.get("kind") or "")
    if raw in {"text", "reaction", "system"}:
        return raw  # type: ignore[return-value]
    if event.type == "whatsapp.reaction" or payload.get("reaction_emoji"):
        return "reaction"
    return "text"


def message_from_event(event: ScenarioEvent) -> PrivateChatMessage:
    payload = dict(event.payload)
    raw_id = str(payload.get("id") or event.id)
    chat_id = str(payload.get("chat_id") or payload.get("thread_id") or raw_id)
    return PrivateChatMessage(
        id=stable_id("wa", raw_id),
        provider="whatsapp",
        provider_message_id=raw_id,
        chat_id=chat_id,
        thread_id=payload.get("thread_id") or chat_id,
        from_person=_ref(
            payload.get("from"),
            name=payload.get("from_name"),
            phone=payload.get("from_phone"),
        ),
        to=_refs(payload.get("to")),
        body_text=payload.get("body_text") or payload.get("body"),
        sent_at=_aware(payload.get("sent_at") or event.at),
        is_group=bool(payload.get("is_group", False)),
        chat_title=payload.get("chat_title"),
        kind=_kind_for(event, payload),
        reaction_emoji=payload.get("reaction_emoji"),
        reply_to_id=payload.get("reply_to_id"),
    )


class SyntheticWhatsAppSource:
    """Demo-only WhatsApp adapter — never reads Private storage or credentials."""

    source_name = "synthetic_whatsapp"

    def __init__(
        self,
        events: ScenarioPackage | Sequence[ScenarioEvent],
        *,
        until: datetime | None = None,
    ) -> None:
        self._events = events_for_source(
            package_events(events),
            source="whatsapp",
            until=until,
        )

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        items = [
            message_from_event(event).model_dump(mode="json")
            for event in self._events
            if event.type in _CHAT_EVENT_TYPES
        ]
        return batch_from_items(
            items, source_name=self.source_name, start=cursor_index(cursor)
        )
