"""Synthetic mail DataSource — scenario events → PrivateMessage (D4).

Supports multi-stream merge (canonical | corpus background | generated noise)
without exposing evaluator ``signal_class`` on emitted messages.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from personal_enigma.domain import PrivateMessage, PrivatePersonRef
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.corpus.streams import (
    CanonicalScenarioStream,
    MailStream,
    merge_stream_events,
    strip_evaluator_keys,
)
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources import (
    _aware,
    as_str_list,
    batch_from_items,
    cursor_index,
    events_for_source,
    package_events,
    stable_id,
)


def _ref(email: str | None, name: str | None = None) -> PrivatePersonRef | None:
    if not email and not name:
        return None
    return PrivatePersonRef(display_name=name, email=email)


def _refs(value: Any) -> list[PrivatePersonRef]:
    if value is None:
        return []
    if isinstance(value, str):
        return [PrivatePersonRef(email=value)]
    if isinstance(value, list):
        out: list[PrivatePersonRef] = []
        for item in value:
            if isinstance(item, str):
                out.append(PrivatePersonRef(email=item))
            elif isinstance(item, dict):
                out.append(
                    PrivatePersonRef(
                        display_name=item.get("display_name"),
                        email=item.get("email"),
                    )
                )
        return out
    return []


def message_from_event(event: ScenarioEvent) -> PrivateMessage:
    payload = strip_evaluator_keys(dict(event.payload))
    raw_id = str(payload.get("id") or event.id)
    return PrivateMessage(
        id=stable_id("mail", raw_id),
        provider="gmail",
        provider_message_id=raw_id,
        thread_id=payload.get("thread_id"),
        subject=payload.get("subject"),
        snippet=payload.get("snippet"),
        body_text=payload.get("body_text") or payload.get("body"),
        from_person=_ref(payload.get("from"), payload.get("from_name")),
        to=_refs(payload.get("to")),
        cc=_refs(payload.get("cc")),
        sent_at=_aware(
            payload.get("sent_at") or (event.at if event.type == "email.send" else None)
        ),
        received_at=_aware(
            payload.get("received_at")
            or (event.at if event.type == "email.receive" else None)
        ),
        labels=as_str_list(payload.get("labels")),
    )


class SyntheticMailSource:
    """Demo-only mail adapter — never reads Private storage or credentials."""

    source_name = "synthetic_mail"

    def __init__(
        self,
        events: ScenarioPackage | Sequence[ScenarioEvent] | None = None,
        *,
        streams: Sequence[MailStream] | None = None,
        until: datetime | None = None,
    ) -> None:
        if streams is not None:
            self._events = [
                e
                for e in merge_stream_events(streams)
                if until is None or e.at <= until
            ]
        elif events is not None:
            self._events = events_for_source(
                package_events(events),
                source="mail",
                until=until,
            )
        else:
            self._events = []

    @classmethod
    def for_scenario(
        cls,
        package: ScenarioPackage,
        *,
        profile: str | None = "demo",
        include_background: bool = True,
        until: datetime | None = None,
        background_stream: MailStream | None = None,
    ) -> SyntheticMailSource:
        """Merge canonical scenario mail with optional background chronologically.

        Background ``signal_class`` / ``source_class`` never appear on emitted
        messages — only ordinary mail fields reach Enigma.
        """
        streams: list[MailStream] = [CanonicalScenarioStream(events=package, until=until)]
        if include_background:
            if background_stream is not None:
                streams.append(background_stream)
            else:
                from personal_enigma.simulation.corpus.background import (
                    build_background_stream,
                )

                built = build_background_stream(package, profile=profile)  # type: ignore[arg-type]
                streams.append(built.stream)
        return cls(streams=streams, until=until)

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        items = [
            message_from_event(event).model_dump(mode="json")
            for event in self._events
            if event.type in {"email.receive", "email.send"}
        ]
        # Defence in depth: strip any evaluator keys that slipped into dumps.
        items = [strip_evaluator_keys(item) for item in items]
        return batch_from_items(items, source_name=self.source_name, start=cursor_index(cursor))
