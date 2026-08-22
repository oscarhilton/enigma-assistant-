"""Data classification for Private vault persistence (ADR-022)."""

from __future__ import annotations

from enum import StrEnum


class DataClass(StrEnum):
    """At-rest classification enforced at the storage API boundary."""

    SECRET = "secret"
    PRIVATE_RAW = "private_raw"
    PRIVATE_DERIVED = "private_derived"
    REMOTE_SAFE = "remote_safe"
    PUBLIC = "public"
