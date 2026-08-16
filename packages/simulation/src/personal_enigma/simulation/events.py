"""Simulation event types and emission records (D5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SimulationEvent(BaseModel):
    """A scheduled synthetic-world event awaiting emission."""

    id: str
    at: datetime
    type: str
    source: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class EmittedEvent(BaseModel):
    """Record of an event that has been emitted by the engine."""

    id: str
    at: datetime
    type: str
    source: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime
