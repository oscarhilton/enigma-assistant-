"""Simulation event stub (D5 owns the engine)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SimulationEvent(BaseModel):
    """A scheduled synthetic-world event awaiting emission."""

    id: str
    at: datetime
    type: str
    payload: dict[str, object] = Field(default_factory=dict)
