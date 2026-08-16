"""Shared helpers for synthetic DataSource adapters (D4)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage

NAMESPACE = UUID("6b1f0c2e-9a4d-4e8f-b7c1-2d3e4f5a6b7c")


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def stable_id(prefix: str, raw_id: str) -> str:
    return f"{prefix}:{uuid5(NAMESPACE, raw_id)}"


def events_for_source(
    events: Sequence[ScenarioEvent],
    *,
    source: str,
    until: datetime | None = None,
) -> list[ScenarioEvent]:
    selected = [e for e in events if e.source == source]
    if until is not None:
        selected = [e for e in selected if e.at <= until]
    return selected


def cursor_index(cursor: SyncCursor | None) -> int:
    if cursor is None or not cursor.value:
        return 0
    try:
        return int(cursor.value)
    except ValueError:
        return 0


def batch_from_items(
    items: list[dict[str, Any]],
    *,
    source_name: str,
    start: int,
) -> ChangeBatch:
    end = len(items)
    slice_items = items[start:end]
    cursor = SyncCursor(value=str(end), source=source_name)
    return ChangeBatch(items=slice_items, next_cursor=cursor, exhausted=True)


def package_events(package: ScenarioPackage | Iterable[ScenarioEvent]) -> list[ScenarioEvent]:
    if isinstance(package, ScenarioPackage):
        return list(package.events)
    return list(package)


__all__ = [
    "NAMESPACE",
    "_aware",
    "batch_from_items",
    "cursor_index",
    "events_for_source",
    "package_events",
    "stable_id",
]
