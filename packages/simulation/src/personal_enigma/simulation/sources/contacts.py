"""Synthetic contacts DataSource — scenario events → PrivatePerson (D4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid5

from personal_enigma.domain import PrivatePerson
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources._base import (
    NAMESPACE,
    batch_from_items,
    cursor_index,
    events_for_source,
    package_events,
    stable_id,
)


def person_from_event(event: ScenarioEvent) -> PrivatePerson:
    payload = event.payload
    raw_id = str(payload.get("id") or event.id)
    emails = payload.get("email_addresses") or []
    if payload.get("email"):
        emails = [payload["email"], *emails]
    phones = payload.get("phone_numbers") or []
    if payload.get("phone"):
        phones = [payload["phone"], *phones]
    return PrivatePerson(
        id=uuid5(NAMESPACE, raw_id),
        display_name=payload.get("display_name") or payload.get("name"),
        aliases=list(payload.get("aliases") or []),
        email_addresses=[str(e) for e in emails],
        phone_numbers=[str(p) for p in phones],
        organisations=list(payload.get("organisations") or []),
        provider_ids={"synthetic": stable_id("contact", raw_id)},
    )


class SyntheticContactsSource:
    source_name = "synthetic_contacts"

    def __init__(
        self,
        events: ScenarioPackage | Sequence[ScenarioEvent],
        *,
        until: datetime | None = None,
    ) -> None:
        self._events = events_for_source(
            package_events(events),
            source="contacts",
            until=until,
        )

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        items = [
            person_from_event(event).model_dump(mode="json")
            for event in self._events
            if event.type == "contact.upsert"
        ]
        return batch_from_items(items, source_name=self.source_name, start=cursor_index(cursor))
