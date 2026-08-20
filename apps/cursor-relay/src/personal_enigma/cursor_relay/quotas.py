"""Concurrency and spend limits for create paths."""

from __future__ import annotations

from dataclasses import dataclass, field


class QuotaError(Exception):
    def __init__(self, message: str, *, code: str = "quota_exceeded") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class QuotaTracker:
    max_in_flight: int
    max_spend_units: float
    spend_per_create: float
    in_flight: int = 0
    spend_units: float = 0.0
    active_agent_ids: set[str] = field(default_factory=set)

    def check_create(self) -> None:
        if self.in_flight >= self.max_in_flight:
            raise QuotaError(
                f"Max in-flight agents exceeded ({self.in_flight}/{self.max_in_flight})",
                code="concurrency_exceeded",
            )
        projected = self.spend_units + self.spend_per_create
        if projected > self.max_spend_units:
            raise QuotaError(
                f"Spend cap exceeded (projected {projected} > {self.max_spend_units})",
                code="spend_exceeded",
            )

    def record_create(self, agent_id: str) -> None:
        self.check_create()
        self.in_flight += 1
        self.spend_units += self.spend_per_create
        self.active_agent_ids.add(agent_id)

    def record_complete(self, agent_id: str) -> None:
        if agent_id in self.active_agent_ids:
            self.active_agent_ids.discard(agent_id)
            self.in_flight = max(0, self.in_flight - 1)

    def snapshot(self) -> dict[str, float | int]:
        return {
            "in_flight": self.in_flight,
            "max_in_flight": self.max_in_flight,
            "spend_units": self.spend_units,
            "max_spend_units": self.max_spend_units,
        }
