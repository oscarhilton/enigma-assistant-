"""Kinds of attention signals distinguished by the engine."""

from enum import StrEnum


class AttentionKind(StrEnum):
    INFERRED_OBLIGATION = "inferred_obligation"
    EXPLICIT_REMINDER = "explicit_reminder"
    INFERRED_COMMITMENT = "inferred_commitment"
    CALENDAR_OBLIGATION = "calendar_obligation"
