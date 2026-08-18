"""Calendar READ queries for My Enigma — reduced facts, no booking claims (P03)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_enigma.api.demo_availability import (
    period_bounds,
    weekend_bounds,
)
from personal_enigma.api.private_calendar_store import CalendarReadAdapter, reduced_calendar_fact
from personal_enigma.domain import PrivateCalendarEvent

_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_WEEKDAY_RE = re.compile(
    r"\b(" + "|".join(_WEEKDAY_NAMES) + r")\b",
    re.IGNORECASE,
)
_DOING_TOMORROW_RE = re.compile(
    r"\bwhat(?:'s|'s| is| am i) (?:doing|on|in my calendar)(?:\s+for)?\s+tomorrow\b",
    re.IGNORECASE,
)
_COMING_UP_WEEKEND_RE = re.compile(
    r"\bwhat(?:'s|'s| is) (?:coming up|on)(?:\s+for)?\s+(?:this\s+)?weekend\b",
    re.IGNORECASE,
)
_AGENDA_TOMORROW_RE = re.compile(r"\btomorrow\b", re.IGNORECASE)
_AGENDA_WEEKEND_RE = re.compile(r"\b(?:this\s+)?weekend\b", re.IGNORECASE)
_FREE_DAY_RE = re.compile(r"\bam i (?:actually )?free\b", re.IGNORECASE)


def _parse_iso(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_clock(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%H:%M")


def weekday_bounds(reference: datetime, weekday: str) -> tuple[datetime, datetime]:
    """Upcoming named weekday 00:00–23:59 UTC (or today if still ahead)."""
    ref = reference.astimezone(UTC)
    target = weekday.strip().lower()
    if target not in _WEEKDAY_NAMES:
        raise ValueError(f"Unknown weekday {weekday!r}")
    target_idx = _WEEKDAY_NAMES.index(target)
    days_ahead = (target_idx - ref.weekday()) % 7
    if days_ahead == 0 and ref.hour >= 23 and ref.minute >= 59:
        days_ahead = 7
    day = (ref + timedelta(days=days_ahead)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = day.replace(hour=23, minute=59, second=59, microsecond=0)
    return day, end


def events_in_period(
    adapter: CalendarReadAdapter,
    period_start: datetime,
    period_end: datetime,
) -> list[dict[str, Any]]:
    rows = adapter.list_events()
    selected: list[PrivateCalendarEvent] = []
    for event in rows:
        start = _parse_iso(event.start_at)
        if period_start <= start <= period_end:
            selected.append(event)
    selected.sort(key=lambda row: row.start_at)
    return [reduced_calendar_fact(event) for event in selected]


def infer_private_calendar_period(text: str) -> str | None:
    """Private-world agenda / availability period from natural language."""
    if _DOING_TOMORROW_RE.search(text) or (
        _AGENDA_TOMORROW_RE.search(text) and "doing" in text.casefold()
    ):
        return "tomorrow"
    if _COMING_UP_WEEKEND_RE.search(text) or _AGENDA_WEEKEND_RE.search(text):
        return "this_weekend"
    if _FREE_DAY_RE.search(text):
        match = _WEEKDAY_RE.search(text)
        if match:
            return match.group(1).lower()
        if _AGENDA_TOMORROW_RE.search(text):
            return "tomorrow"
        if _AGENDA_WEEKEND_RE.search(text):
            return "this_weekend"
    return None


def period_window(reference: datetime, period: str | None) -> tuple[datetime, datetime]:
    if period in _WEEKDAY_NAMES:
        return weekday_bounds(reference, period)
    if period == "this_weekend":
        return weekend_bounds(reference)
    return period_bounds(reference, period)


def format_agenda_message(
    *,
    adapter: CalendarReadAdapter,
    reference: datetime,
    period: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    start, end = period_window(reference, period)
    events = events_in_period(adapter, start, end)
    label = (period or "this period").replace("_", " ")
    if period == "tomorrow":
        label = "tomorrow"
    elif period == "this_weekend":
        label = "this weekend"
    elif period in _WEEKDAY_NAMES:
        label = period.capitalize()

    if not events:
        return f"I don't see anything in your calendar {label}.", events

    parts: list[str] = []
    for event in events:
        start_at = _parse_iso(event["start_at"])
        end_at = _parse_iso(event["end_at"])
        if period in {"this_weekend", "this_week", "next_week"} or period in _WEEKDAY_NAMES:
            day = start_at.strftime("%A")
            parts.append(
                f"{day}: {event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
            )
        else:
            parts.append(
                f"{event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
            )
    body = "; ".join(parts)
    if period == "tomorrow":
        return f"Tomorrow: {body}.", events
    if period == "this_weekend":
        return f"This weekend: {body}.", events
    return f"{label.capitalize()}: {body}.", events


def format_private_availability_message(
    *,
    adapter: CalendarReadAdapter,
    reference: datetime,
    period: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    """Conservative occupancy — calendar hold is not a confirmed booking."""
    start, end = period_window(reference, period)
    events = events_in_period(adapter, start, end)

    if period in _WEEKDAY_NAMES:
        label = period.capitalize()
    elif period == "tomorrow":
        label = "Tomorrow"
    elif period == "this_weekend":
        label = "This weekend"
    elif period == "today":
        label = "Today"
    else:
        label = (period or "That window").replace("_", " ").capitalize()

    if not events:
        if period == "tomorrow":
            return "I don't see anything in your calendar tomorrow.", events
        if period == "this_weekend":
            return f"{label}: your calendar looks clear.", events
        return f"{label}: your calendar looks clear.", events

    parts: list[str] = []
    for event in events:
        start_at = _parse_iso(event["start_at"])
        end_at = _parse_iso(event["end_at"])
        if period in {"this_weekend", "this_week", "next_week"} or period in _WEEKDAY_NAMES:
            day = start_at.strftime("%A")
            parts.append(
                f"{day} has {event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
            )
        else:
            parts.append(
                f"{event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
            )

    body = "; ".join(parts)
    if period == "tomorrow":
        return f"Tomorrow: {body}.", events
    if period in _WEEKDAY_NAMES:
        return f"{label}: I see {parts[0]} on your calendar.", events
    return f"{label}: {body}.", events


def build_calendar_provenance(facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Why payload — lists reduced calendar facts used, never attendee emails."""
    return {
        "headline": "CALENDAR FACTS USED",
        "evidence": [row["id"] for row in facts],
        "inference": [
            "Calendar entries are read-only evidence — not confirmed bookings.",
            "Descriptions and attendee emails stay local; only title and time reached reasoning.",
        ],
        "facts": facts,
    }


__all__ = [
    "build_calendar_provenance",
    "events_in_period",
    "format_agenda_message",
    "format_private_availability_message",
    "infer_private_calendar_period",
    "period_window",
    "weekday_bounds",
]
