"""Demo availability answers from checkpoint calendar evidence — no invented facts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from personal_enigma.attention.projection import AttentionState
from personal_enigma.fixtures.demo_checkpoints import load_checkpoint_snapshot

# Alex-v1 calendar evidence referenced in arm-a checkpoints (from scenario timeline).
ALEX_V1_CALENDAR_EVIDENCE: dict[str, dict[str, str]] = {
    "cal-brunch-parents": {
        "title": "Brunch with Elena's parents",
        "start_at": "2026-01-24T11:00:00+00:00",
        "end_at": "2026-01-24T13:00:00+00:00",
    },
    "cal-token-review": {
        "title": "Token inventory review",
        "start_at": "2026-01-21T14:00:00+00:00",
        "end_at": "2026-01-21T15:00:00+00:00",
    },
    "cal-standup-w3": {
        "title": "Team standup",
        "start_at": "2026-01-22T09:00:00+00:00",
        "end_at": "2026-01-22T09:15:00+00:00",
    },
}


def _parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_clock(value: datetime) -> str:
    local = value.astimezone(UTC)
    return local.strftime("%H:%M")


def later_today_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    start = ref
    end = ref.replace(hour=23, minute=59, second=59, microsecond=0)
    return start, end


def today_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    end = ref.replace(hour=23, minute=59, second=59, microsecond=0)
    return start, end


def this_afternoon_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    noon = ref.replace(hour=12, minute=0, second=0, microsecond=0)
    start = max(ref, noon)
    end = ref.replace(hour=18, minute=0, second=0, microsecond=0)
    return start, end


def this_evening_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    six_pm = ref.replace(hour=18, minute=0, second=0, microsecond=0)
    start = max(ref, six_pm)
    end = ref.replace(hour=23, minute=59, second=59, microsecond=0)
    return start, end


def tomorrow_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    next_day = (ref + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = next_day.replace(hour=23, minute=59, second=59, microsecond=0)
    return next_day, end


def after_tomorrow_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    day = (ref + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = day.replace(hour=23, minute=59, second=59, microsecond=0)
    return day, end


def this_week_bounds(reference: datetime) -> tuple[datetime, datetime]:
    """Monday 00:00 UTC through end of Sunday for the reference week."""
    ref = reference.astimezone(UTC)
    monday = (ref - timedelta(days=ref.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sunday_end = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday_end


def next_week_bounds(reference: datetime) -> tuple[datetime, datetime]:
    """Following Monday 00:00 UTC through end of the next Sunday."""
    this_start, _ = this_week_bounds(reference)
    next_monday = this_start + timedelta(days=7)
    next_sunday_end = next_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return next_monday, next_sunday_end


def weekend_bounds(reference: datetime) -> tuple[datetime, datetime]:
    """Upcoming Saturday 00:00 UTC through end of Sunday."""
    ref = reference.astimezone(UTC)
    days_until_sat = (5 - ref.weekday()) % 7
    if days_until_sat == 0 and ref.hour >= 23 and ref.minute >= 59:
        days_until_sat = 7
    saturday = (ref + timedelta(days=days_until_sat)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sunday_end = saturday + timedelta(days=1, hours=23, minutes=59, seconds=59)
    return saturday, sunday_end


def friday_night_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference.astimezone(UTC)
    days_until_fri = (4 - ref.weekday()) % 7
    if days_until_fri == 0 and ref.hour >= 21:
        days_until_fri = 7
    friday = (ref + timedelta(days=days_until_fri)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    friday_end = friday.replace(hour=23, minute=59, second=59, microsecond=0)
    return friday, friday_end


def saturday_bounds(reference: datetime) -> tuple[datetime, datetime]:
    start, _ = weekend_bounds(reference)
    end = start.replace(hour=23, minute=59, second=59, microsecond=0)
    return start, end


def period_bounds(
    reference: datetime,
    period: str | None,
) -> tuple[datetime, datetime]:
    if period == "later_today":
        return later_today_bounds(reference)
    if period == "today":
        return today_bounds(reference)
    if period == "this_afternoon":
        return this_afternoon_bounds(reference)
    if period == "this_evening":
        return this_evening_bounds(reference)
    if period == "tomorrow":
        return tomorrow_bounds(reference)
    if period == "after_tomorrow":
        return after_tomorrow_bounds(reference)
    if period == "this_week":
        return this_week_bounds(reference)
    if period == "next_week":
        return next_week_bounds(reference)
    if period == "friday_night":
        return friday_night_bounds(reference)
    if period == "saturday":
        return saturday_bounds(reference)
    return weekend_bounds(reference)


_RELATIVE_PERIOD_LABELS: dict[str, str] = {
    "today": "today",
    "later_today": "later today",
    "this_afternoon": "this afternoon",
    "this_evening": "this evening",
    "tomorrow": "tomorrow",
    "after_tomorrow": "the day after tomorrow",
    "this_week": "this week",
    "next_week": "next week",
}


def evidence_ids_in_checkpoint(checkpoint_id: str) -> set[str]:
    snapshot = load_checkpoint_snapshot(checkpoint_id)
    ids: set[str] = set()
    for candidate in snapshot.candidate_set:
        ids.update(candidate.evidence_ids)
    for candidate in snapshot.suppressed_candidates:
        ids.update(candidate.evidence_ids)
    return ids


def calendar_events_in_period(
    checkpoint_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[dict[str, str]]:
    evidence = evidence_ids_in_checkpoint(checkpoint_id)
    events: list[dict[str, str]] = []
    for evidence_id in sorted(evidence):
        row = ALEX_V1_CALENDAR_EVIDENCE.get(evidence_id)
        if row is None:
            continue
        start = _parse_iso(row["start_at"])
        if period_start <= start <= period_end:
            events.append({"evidence_id": evidence_id, **row})
    events.sort(key=lambda row: row["start_at"])
    return events


def _open_booking_obligations(
    state: AttentionState,
    calendar_evidence_ids: set[str],
) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for item in (*state.needs_you, *state.context):
        overlap = set(item.evidence_ids) & calendar_evidence_ids
        if not overlap:
            continue
        if "book" in item.title.lower() and item.id not in seen:
            seen.add(item.id)
            titles.append(item.title)
    return titles


def format_availability_message(
    *,
    state: AttentionState,
    checkpoint_id: str,
    reference: datetime,
    period: str | None,
) -> str:
    start, end = period_bounds(reference, period)
    events = calendar_events_in_period(checkpoint_id, start, end)
    cal_ids = {row["evidence_id"] for row in events}
    bookings = _open_booking_obligations(state, cal_ids)

    relative_label = _RELATIVE_PERIOD_LABELS.get(period or "")
    if relative_label:
        if not events:
            return f"I don't see anything in your calendar {relative_label}."
        relative_parts: list[str] = []
        for event in events:
            start_at = _parse_iso(event["start_at"])
            end_at = _parse_iso(event["end_at"])
            if period in {"this_week", "next_week"}:
                day = start_at.strftime("%A")
                relative_parts.append(
                    f"{day}: {event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
                )
            else:
                relative_parts.append(
                    f"{event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
                )
        body = "; ".join(relative_parts)
        if bookings:
            booking_hint = bookings[0]
            if "book" in booking_hint.lower():
                body = f"{body} — {booking_hint} is still open"
        return f"{relative_label.capitalize()}: {body}."

    if period == "friday_night":
        label = "Friday night"
    elif period == "saturday":
        label = "Saturday"
    elif period == "this_week":
        label = "This week"
    else:
        label = "This weekend"

    if not events:
        return f"{label}: your calendar looks clear."

    parts: list[str] = []
    for event in events:
        start_at = _parse_iso(event["start_at"])
        end_at = _parse_iso(event["end_at"])
        day = start_at.strftime("%A")
        parts.append(
            f"{day} has {event['title']}, {_format_clock(start_at)}–{_format_clock(end_at)}"
        )

    body = "; ".join(parts)
    if bookings:
        booking_hint = bookings[0]
        if "book" in booking_hint.lower():
            body = f"{body} — {booking_hint} is still open"
    if label == "This weekend" and len(events) == 1:
        event_day = _parse_iso(events[0]["start_at"]).strftime("%A")
        other_day = "Sunday" if event_day == "Saturday" else "Saturday"
        if other_day.lower() not in body.lower():
            body = f"{body}. {other_day} looks clear"

    return f"{label}: {body}."


def minutes_until_next_commitment(
    checkpoint_id: str,
    reference: datetime,
    *,
    period: str = "later_today",
) -> tuple[int | None, str | None]:
    """Conservative free minutes before the next calendar event in *period*."""
    start, end = period_bounds(reference, period)
    events = calendar_events_in_period(checkpoint_id, start, end)
    if not events:
        return None, None
    first = events[0]
    start_at = _parse_iso(first["start_at"])
    ref = reference.astimezone(UTC)
    if start_at <= ref:
        return 0, first["title"]
    delta = start_at - ref
    return max(0, int(delta.total_seconds() // 60)), first["title"]


def format_time_fit_message(
    *,
    state: AttentionState,
    checkpoint_id: str,
    reference: datetime,
    task_minutes: int,
    task_title: str | None = None,
    period: str = "later_today",
) -> str:
    free_minutes, next_title = minutes_until_next_commitment(
        checkpoint_id,
        reference,
        period=period,
    )
    task_label = task_title or "This"
    window = _RELATIVE_PERIOD_LABELS.get(period)
    if window is None:
        window = "Saturday" if period == "saturday" else "later today"
    if free_minutes is None:
        return (
            f"I don't see anything blocking you {window}. "
            f"{task_label} should take around {task_minutes} minutes."
        )
    if free_minutes == 0:
        return (
            f"You've got a commitment now ({next_title}). "
            f"{task_label} should take around {task_minutes} minutes."
        )
    return (
        f"You've got about {free_minutes} minutes free before {next_title}. "
        f"{task_label} should take around {task_minutes} minutes."
    )


def build_availability_turn(
    state: AttentionState,
    *,
    checkpoint_id: str,
    at: str,
    period: str | None = None,
) -> list[dict[str, Any]]:
    reference = _parse_iso(at)
    text = format_availability_message(
        state=state,
        checkpoint_id=checkpoint_id,
        reference=reference,
        period=period,
    )
    return [{"kind": "enigma_message", "text": text, "at": at}]


__all__ = [
    "ALEX_V1_CALENDAR_EVIDENCE",
    "after_tomorrow_bounds",
    "build_availability_turn",
    "calendar_events_in_period",
    "format_availability_message",
    "format_time_fit_message",
    "later_today_bounds",
    "minutes_until_next_commitment",
    "next_week_bounds",
    "period_bounds",
    "this_afternoon_bounds",
    "this_evening_bounds",
    "this_week_bounds",
    "tomorrow_bounds",
    "weekend_bounds",
]
