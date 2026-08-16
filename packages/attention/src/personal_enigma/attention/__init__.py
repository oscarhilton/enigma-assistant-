"""Attention engine — local ranking of what actually matters."""

from personal_enigma.attention.classify import message_attention_kind
from personal_enigma.attention.collect import (
    collect_attention_items,
    items_from_calendar_events,
    items_from_messages,
    items_from_obligations,
    items_from_reminders,
)
from personal_enigma.attention.deadline import (
    DeadlinePhase,
    classify_deadline,
    deadline_why_now_glance,
    parse_due_from_body,
    why_now_glance_for_deadline,
)
from personal_enigma.attention.engine import (
    KIND_PRIORITY,
    WEAK_INFERRED_KINDS,
    HeuristicAttentionEngine,
    effective_score,
)
from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.noise import (
    looks_like_machine_noise,
    looks_like_newsletter,
    looks_like_package_notification,
)
from personal_enigma.attention.overdue import overdue_reminders
from personal_enigma.attention.protocol import AttentionEngine, AttentionItem
from personal_enigma.attention.surface import (
    DEFAULT_SURFACE_MIN_PRIORITY,
    TIMING_SURFACE_MIN_PRIORITY,
    assign_surface_priority,
    filter_surfaced,
    kind_surface_priority,
    partition_surface,
    should_surface,
    ui_priority_for_kind,
)

__all__ = [
    "DEFAULT_SURFACE_MIN_PRIORITY",
    "KIND_PRIORITY",
    "TIMING_SURFACE_MIN_PRIORITY",
    "WEAK_INFERRED_KINDS",
    "AttentionEngine",
    "AttentionItem",
    "AttentionKind",
    "DeadlinePhase",
    "HeuristicAttentionEngine",
    "assign_surface_priority",
    "classify_deadline",
    "collect_attention_items",
    "deadline_why_now_glance",
    "effective_score",
    "filter_surfaced",
    "items_from_calendar_events",
    "items_from_messages",
    "items_from_obligations",
    "items_from_reminders",
    "kind_surface_priority",
    "looks_like_machine_noise",
    "looks_like_newsletter",
    "looks_like_package_notification",
    "message_attention_kind",
    "overdue_reminders",
    "parse_due_from_body",
    "partition_surface",
    "should_surface",
    "ui_priority_for_kind",
    "why_now_glance_for_deadline",
]
