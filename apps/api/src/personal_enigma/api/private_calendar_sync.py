"""Operator-triggered Apple calendar sync into My Enigma private store (P03c).

Application plumbing only — not an Assistant capability. READ/SUPPORT authority
unchanged; sync refreshes the evidence substrate under the private world root.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from personal_enigma.api.bridge.config import (
    DEFAULT_BRIDGE_BASE_URL,
    bridge_client_config_from_settings,
)
from personal_enigma.api.private_calendar_store import CalendarEventStore
from personal_enigma.domain import PrivateCalendarEvent
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import SyncCursor
from personal_enigma.ingestion.sources.apple_calendar import AppleCalendarSource

PILOT_SELECTION_FILENAME = "pilot_selection.json"


@dataclass(frozen=True, slots=True)
class AppleCalendarSyncResult:
    """Outcome of an operator-triggered Apple sync."""

    event_count: int
    calendar_ids: tuple[str, ...]
    synced_at: str
    storage_root: str


def pilot_calendar_ids_for_root(storage_root: Path) -> tuple[str, ...]:
    """Resolve explicit pilot calendar selection — env wins, then private config file."""
    env_raw = os.environ.get("ENIGMA_PILOT_APPLE_CALENDAR_IDS", "").strip()
    if env_raw:
        return tuple(cid.strip() for cid in env_raw.split(",") if cid.strip())

    config_path = storage_root / "calendar" / PILOT_SELECTION_FILENAME
    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            ids = raw.get("calendar_ids")
            if isinstance(ids, list):
                return tuple(str(row).strip() for row in ids if str(row).strip())
    return ()


def bridge_client_from_env() -> AppleBridgeClient:
    """Build a localhost-only bridge client from operator env (no Keychain I/O here)."""
    token = os.environ.get("ENIGMA_BRIDGE_TOKEN", "").strip() or None
    base_url = os.environ.get("ENIGMA_BRIDGE_BASE_URL", DEFAULT_BRIDGE_BASE_URL).strip()
    unix_socket = os.environ.get("ENIGMA_BRIDGE_UNIX_SOCKET", "").strip() or None
    config = bridge_client_config_from_settings(
        token=token,
        base_url=base_url,
        unix_socket=unix_socket,
    )
    return AppleBridgeClient(
        base_url=config.base_url,
        token=config.token,
        unix_socket=config.unix_socket,
    )


async def fetch_apple_calendar_events(
    client: AppleBridgeClient,
    calendar_ids: Sequence[str],
) -> list[PrivateCalendarEvent]:
    """Pull the current Apple calendar snapshot via M08 (full replace semantics)."""
    if not calendar_ids:
        raise AppleBridgeError(
            "No pilot calendar IDs configured "
            "(set ENIGMA_PILOT_APPLE_CALENDAR_IDS or calendar/pilot_selection.json)"
        )
    source = AppleCalendarSource(client, selected_calendar_ids=list(calendar_ids))
    events: list[PrivateCalendarEvent] = []
    cursor: SyncCursor | None = None
    while True:
        batch = await source.get_changes(cursor)
        for row in batch.items:
            try:
                events.append(PrivateCalendarEvent.model_validate(row))
            except ValidationError as exc:
                raise AppleBridgeError("Apple Bridge returned an invalid calendar event") from exc
        if batch.exhausted:
            break
        cursor = batch.next_cursor
        if cursor is None:
            break
    return events


async def sync_apple_calendar_to_store(storage_root: Path) -> AppleCalendarSyncResult:
    """Operator sync: M08 bridge → private `calendar/events.json` (Apple-only snapshot)."""
    calendar_ids = pilot_calendar_ids_for_root(storage_root)
    client = bridge_client_from_env()
    events = await fetch_apple_calendar_events(client, calendar_ids)
    store = CalendarEventStore(storage_root=storage_root)
    store.replace_all(events)
    synced_at = datetime.now(tz=UTC).isoformat()
    return AppleCalendarSyncResult(
        event_count=len(events),
        calendar_ids=calendar_ids,
        synced_at=synced_at,
        storage_root=str(storage_root),
    )


__all__ = [
    "AppleCalendarSyncResult",
    "bridge_client_from_env",
    "fetch_apple_calendar_events",
    "pilot_calendar_ids_for_root",
    "sync_apple_calendar_to_store",
]
