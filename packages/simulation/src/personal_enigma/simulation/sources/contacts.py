"""Synthetic contacts DataSource — scenario events → PrivatePerson (D4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid5

from personal_enigma.domain import PrivatePerson
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.sources import (
    NAMESPACE,
    as_str_list,
    batch_from_items,
    cursor_index,
    events_for_source,
    package_events,
    stable_id,
)


def person_from_event(event: ScenarioEvent) -> PrivatePerson:
    payload = event.payload
    raw_id = str(payload.get("id") or event.id)
    emails = as_str_list(payload.get("email_addresses"))
    if payload.get("email"):
        emails = [str(payload["email"]), *emails]
    phones = as_str_list(payload.get("phone_numbers"))
    if payload.get("phone"):
        phones = [str(payload["phone"]), *phones]
    return PrivatePerson(
        id=uuid5(NAMESPACE, raw_id),
        display_name=payload.get("display_name") or payload.get("name"),
        aliases=as_str_list(payload.get("aliases")),
        email_addresses=emails,
        phone_numbers=phones,
        organisations=as_str_list(payload.get("organisations")),
        provider_ids={"synthetic": stable_id("contact", raw_id)},
    )


class SyntheticContactsSource:
    """Demo-only contacts adapter — never reads Private storage or credentials."""

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
