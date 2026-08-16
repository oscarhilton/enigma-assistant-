"""Default attention surface policy — candidates vs what interrupts now."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from personal_enigma.attention.deadline import parse_due_from_body, timing_warrants_surface
from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.protocol import AttentionItem

# Product default: Priority 2 stays a candidate (open loop / dormant);
# surface P5–P4, and P3 when timing warrants.
DEFAULT_SURFACE_MIN_PRIORITY = 4
TIMING_SURFACE_MIN_PRIORITY = 3

_KIND_PRIORITY_BAND: dict[AttentionKind, int] = {
    AttentionKind.EXPLICIT_REMINDER: 5,
    AttentionKind.INFERRED_OBLIGATION: 4,
    AttentionKind.CALENDAR_OBLIGATION: 3,
    AttentionKind.INFERRED_COMMITMENT: 2,
    AttentionKind.PENDING_REPLY: 2,
}


def ui_priority_for_kind(kind: AttentionKind) -> int:
    """Map attention kind → 1–5 UI priority band."""
    return _KIND_PRIORITY_BAND.get(kind, 2)


# Back-compat alias used by collect / tests.
kind_surface_priority = ui_priority_for_kind


def assign_surface_priority(item: AttentionItem) -> AttentionItem:
    """Copy item with ``priority`` filled from kind when unset / zero."""
    priority = item.priority if item.priority > 0 else ui_priority_for_kind(item.kind)
    if priority == item.priority:
        return item
    return item.model_copy(update={"priority": priority})


def should_surface(
    item: AttentionItem,
    *,
    now: datetime | None = None,
    min_priority: int = DEFAULT_SURFACE_MIN_PRIORITY,
    timing_min_priority: int = TIMING_SURFACE_MIN_PRIORITY,
) -> bool:
    """Return True if the item belongs on the default Attention view.

    Priority 2 never interrupts by default. Priority 3 surfaces only when
    timing warrants (approaching / due / overdue).
    """
    priority = item.priority if item.priority > 0 else ui_priority_for_kind(item.kind)
    if priority >= min_priority:
        return True
    if priority < timing_min_priority:
        return False
    if now is None:
        return False
    due = parse_due_from_body(item.body)
    return timing_warrants_surface(due, now=now)


def partition_surface(
    items: Sequence[AttentionItem],
    *,
    now: datetime | None = None,
    min_priority: int = DEFAULT_SURFACE_MIN_PRIORITY,
    timing_min_priority: int = TIMING_SURFACE_MIN_PRIORITY,
) -> tuple[list[AttentionItem], list[AttentionItem]]:
    """Split ranked candidates into (surfaced, held_back)."""
    surfaced: list[AttentionItem] = []
    held: list[AttentionItem] = []
    for raw in items:
        item = assign_surface_priority(raw)
        if should_surface(
            item,
            now=now,
            min_priority=min_priority,
            timing_min_priority=timing_min_priority,
        ):
            surfaced.append(item)
        else:
            held.append(item)
    return surfaced, held


def filter_surfaced(
    items: Sequence[AttentionItem],
    *,
    now: datetime | None = None,
    min_priority: int = DEFAULT_SURFACE_MIN_PRIORITY,
    timing_min_priority: int = TIMING_SURFACE_MIN_PRIORITY,
) -> list[AttentionItem]:
    """Return only items that belong on the default Attention view."""
    surfaced, _ = partition_surface(
        items,
        now=now,
        min_priority=min_priority,
        timing_min_priority=timing_min_priority,
    )
    return surfaced
