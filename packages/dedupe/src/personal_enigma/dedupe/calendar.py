"""Dedupe PrivateCalendarEvent lists across providers (ticket M12)."""

from __future__ import annotations

from datetime import datetime

from personal_enigma.domain import PrivateCalendarEvent, PrivatePersonRef


def _normalize_title(title: str) -> str:
    return " ".join(title.casefold().split())


def _times_close(left: datetime, right: datetime, *, seconds: int = 120) -> bool:
    return abs((left - right).total_seconds()) <= seconds


def _email_key(ref: PrivatePersonRef | None) -> str | None:
    if ref is None or not ref.email:
        return None
    return ref.email.casefold().strip()


def _name_key(ref: PrivatePersonRef | None) -> str | None:
    if ref is None or not ref.display_name:
        return None
    return " ".join(ref.display_name.casefold().split())


def _organiser_compatible(left: PrivateCalendarEvent, right: PrivateCalendarEvent) -> bool:
    """Organiser emails must agree when both present; names are a soft fallback."""
    left_email = _email_key(left.organiser)
    right_email = _email_key(right.organiser)
    if left_email and right_email:
        return left_email == right_email
    left_name = _name_key(left.organiser)
    right_name = _name_key(right.organiser)
    if left_name and right_name:
        return left_name == right_name
    # Missing organiser on either side does not block a title/time match.
    return True


def _same_provider_event(left: PrivateCalendarEvent, right: PrivateCalendarEvent) -> bool:
    return (
        left.provider == right.provider
        and left.provider_event_id == right.provider_event_id
        and (left.calendar_id or "") == (right.calendar_id or "")
    )


def _heuristic_match(left: PrivateCalendarEvent, right: PrivateCalendarEvent) -> bool:
    if _normalize_title(left.title) != _normalize_title(right.title):
        return False
    if not _times_close(left.start_at, right.start_at):
        return False
    if not _times_close(left.end_at, right.end_at):
        return False
    if left.all_day != right.all_day:
        return False
    return _organiser_compatible(left, right)


def _events_match(left: PrivateCalendarEvent, right: PrivateCalendarEvent) -> bool:
    if _same_provider_event(left, right):
        return True
    return _heuristic_match(left, right)


def _richness(event: PrivateCalendarEvent) -> tuple[int, int, int, int]:
    """Prefer the more informative copy when collapsing duplicates."""
    return (
        len(event.attendees),
        1 if event.description else 0,
        1 if event.location else 0,
        1 if event.organiser and (event.organiser.email or event.organiser.display_name) else 0,
    )


def _prefer_canonical(
    left: PrivateCalendarEvent, right: PrivateCalendarEvent
) -> PrivateCalendarEvent:
    if _richness(right) > _richness(left):
        return right
    if _richness(right) < _richness(left):
        return left
    # Stable tie-break: prefer google_calendar over apple_calendar, then id.
    if left.provider != right.provider:
        return left if left.provider == "google_calendar" else right
    return left if left.id <= right.id else right


def dedupe_calendar_events(events: list[PrivateCalendarEvent]) -> list[PrivateCalendarEvent]:
    """Return a single canonical event per real-world meeting.

    Matching signals (see docs/architecture/deduplication.md):

    - same provider + provider_event_id (+ calendar_id)
    - normalised title
    - start / end within a short window
    - organiser email / display name when both sides have one
    """
    if not events:
        return []

    # Union-find over matching pairs, preserving first-seen order of clusters.
    parents = list(range(len(events)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        # Keep the earlier root so output order follows first occurrence.
        if root_left < root_right:
            parents[root_right] = root_left
        else:
            parents[root_left] = root_right

    # Bucket by normalised title + coarse start minute to avoid O(n²) over all pairs.
    buckets: dict[tuple[str, int], list[int]] = {}
    for i, event in enumerate(events):
        key = (_normalize_title(event.title), int(event.start_at.timestamp()) // 120)
        buckets.setdefault(key, []).append(i)

    for indices in buckets.values():
        for pos, i in enumerate(indices):
            left = events[i]
            for j in indices[pos + 1 :]:
                if _events_match(left, events[j]):
                    union(i, j)
    # Same-provider id matches can cross title buckets; compare provider keys separately.
    by_provider: dict[tuple[str, str, str], list[int]] = {}
    for i, event in enumerate(events):
        key = (event.provider, event.provider_event_id, event.calendar_id or "")
        by_provider.setdefault(key, []).append(i)
    for indices in by_provider.values():
        if len(indices) < 2:
            continue
        root = indices[0]
        for j in indices[1:]:
            union(root, j)

    clusters: dict[int, list[PrivateCalendarEvent]] = {}
    order: list[int] = []
    for index, event in enumerate(events):
        root = find(index)
        if root not in clusters:
            clusters[root] = []
            order.append(root)
        clusters[root].append(event)

    canonical: list[PrivateCalendarEvent] = []
    for root in order:
        group = clusters[root]
        chosen = group[0]
        for candidate in group[1:]:
            chosen = _prefer_canonical(chosen, candidate)
        canonical.append(chosen)
    return canonical


def calendar_evidence_from_event(event: PrivateCalendarEvent) -> dict[str, str | None]:
    """Map a canonical event to attention-facing evidence (provider-agnostic)."""
    return {
        "kind": "calendar",
        "event_id": event.id,
        "title": event.title,
    }
