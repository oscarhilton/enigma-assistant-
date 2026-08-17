"""Attention engine — local ranking of what actually matters."""

from personal_enigma.attention.collect import (
    collect_attention_items,
    items_from_calendar_events,
    items_from_messages,
    items_from_obligations,
    items_from_reminders,
)
from personal_enigma.attention.engine import (
    KIND_PRIORITY,
    WEAK_INFERRED_KINDS,
    HeuristicAttentionEngine,
    effective_score,
)
from personal_enigma.attention.interruption_policy import (
    CandidatePolicyFacts,
    InterruptionMode,
    PolicyJudgement,
    SemanticFeatures,
    decide_interruption,
    interruption_mode_for_instant,
)
from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.overdue import overdue_reminders
from personal_enigma.attention.protocol import AttentionEngine, AttentionItem

__all__ = [
    "CandidatePolicyFacts",
    "InterruptionMode",
    "PolicyJudgement",
    "SemanticFeatures",
    "decide_interruption",
    "interruption_mode_for_instant",
    "KIND_PRIORITY",
    "WEAK_INFERRED_KINDS",
    "AttentionEngine",
    "AttentionItem",
    "AttentionKind",
    "HeuristicAttentionEngine",
    "collect_attention_items",
    "effective_score",
    "items_from_calendar_events",
    "items_from_messages",
    "items_from_obligations",
    "items_from_reminders",
    "overdue_reminders",
]
