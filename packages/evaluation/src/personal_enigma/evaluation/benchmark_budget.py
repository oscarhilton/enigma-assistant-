"""Budget ledger for the Reasoning Value Gate live Fireworks lane (R-L03)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from personal_enigma.reasoning.fireworks_transport import FireworksChatTransport
    from personal_enigma.reasoning.protocol import ReasoningResult
    from personal_enigma.transformation import TransformedContext

HARD_CAP_USD = 0.80
INPUT_PRICE_PER_M = 0.15
OUTPUT_PRICE_PER_M = 0.60

DEFAULT_AUDIT_DIR = Path("reports/reasoning-gate-live")
DEFAULT_AUDIT_FILENAME = "budget-audit.jsonl"


class BudgetCapExceededError(RuntimeError):
    """Raised when a projected live call would exceed the hard budget cap."""


def estimate_cost_usd(*, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token counts using Fireworks GPT-OSS-120B pricing."""
    return (
        input_tokens * INPUT_PRICE_PER_M + output_tokens * OUTPUT_PRICE_PER_M
    ) / 1_000_000


def estimate_input_tokens(*, prompt: str, context_summary: str, entity_count: int = 0) -> int:
    """Conservative pre-call input token estimate (word-based heuristic)."""
    words = len(prompt.split()) + len(context_summary.split()) + entity_count
    return max(1, words)


@dataclass
class BudgetRequestRecord:
    """One audited live request (no API keys — usage and cost only)."""

    timestamp: str
    checkpoint_id: str
    rep: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    cumulative_total_usd: float
    phase: str = "live"
    model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "checkpoint_id": self.checkpoint_id,
            "rep": self.rep,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cumulative_total_usd": self.cumulative_total_usd,
            "phase": self.phase,
            "model": self.model,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkBudgetLedger:
    """Tracks cumulative spend and refuses pessimistic over-cap projections."""

    hard_cap_usd: float = HARD_CAP_USD
    input_price_per_m: float = INPUT_PRICE_PER_M
    output_price_per_m: float = OUTPUT_PRICE_PER_M
    audit_dir: Path = field(default_factory=lambda: DEFAULT_AUDIT_DIR)
    audit_filename: str = DEFAULT_AUDIT_FILENAME
    cumulative_usd: float = 0.0
    records: list[BudgetRequestRecord] = field(default_factory=list)

    @property
    def audit_path(self) -> Path:
        return self.audit_dir / self.audit_filename

    def estimate_cost_usd(self, *, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_price_per_m + output_tokens * self.output_price_per_m
        ) / 1_000_000

    def projected_cost_usd(self, *, input_tokens: int, max_output_tokens: int) -> float:
        """Pessimistic pre-call estimate using max output tokens."""
        return self.estimate_cost_usd(
            input_tokens=input_tokens, output_tokens=max_output_tokens
        )

    def check_can_spend(self, *, input_tokens: int, max_output_tokens: int) -> float:
        """Refuse when cumulative + projected next call exceeds the hard cap."""
        projected = self.projected_cost_usd(
            input_tokens=input_tokens, max_output_tokens=max_output_tokens
        )
        if self.cumulative_usd + projected > self.hard_cap_usd:
            raise BudgetCapExceededError(
                f"budget cap {self.hard_cap_usd:.2f} USD would be exceeded: "
                f"cumulative={self.cumulative_usd:.4f} + projected={projected:.4f} "
                f"> cap (input_tokens={input_tokens}, max_output_tokens={max_output_tokens})"
            )
        return projected

    def record_request(
        self,
        *,
        checkpoint_id: str,
        rep: int,
        prompt_tokens: int,
        completion_tokens: int,
        phase: str = "live",
        model: str = "",
        metadata: dict[str, Any] | None = None,
        write_audit: bool = True,
    ) -> BudgetRequestRecord:
        cost = self.estimate_cost_usd(
            input_tokens=prompt_tokens, output_tokens=completion_tokens
        )
        self.cumulative_usd += cost
        record = BudgetRequestRecord(
            timestamp=datetime.now(tz=UTC).isoformat(),
            checkpoint_id=checkpoint_id,
            rep=rep,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=cost,
            cumulative_total_usd=self.cumulative_usd,
            phase=phase,
            model=model,
            metadata=metadata or {},
        )
        self.records.append(record)
        if write_audit:
            self.write_audit_record(record)
        return record

    def write_audit_record(self, record: BudgetRequestRecord) -> None:
        """Append one JSONL audit line (local only — never stores API keys)."""
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.as_dict(), sort_keys=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def remaining_usd(self) -> float:
        return max(0.0, self.hard_cap_usd - self.cumulative_usd)


class BudgetGatedFireworksTransport:
    """Fireworks transport with pessimistic pre-call budget enforcement."""

    def __init__(
        self,
        *,
        transport: FireworksChatTransport,
        ledger: BenchmarkBudgetLedger,
        phase: str = "live",
    ) -> None:
        self._transport = transport
        self._ledger = ledger
        self._phase = phase

    @property
    def ledger(self) -> BenchmarkBudgetLedger:
        return self._ledger

    def complete(
        self,
        *,
        model: str | None = None,
        prompt: str,
        context: TransformedContext,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
        budget_input_tokens: int | None = None,
    ) -> ReasoningResult:
        checkpoint_id = str(context.metadata.get("checkpoint_id", "unknown"))
        max_out = (
            max_output_tokens
            if max_output_tokens is not None
            else self._transport.max_output_tokens
        )
        input_tokens = (
            budget_input_tokens
            if budget_input_tokens is not None
            else estimate_input_tokens(
                prompt=prompt,
                context_summary=context.summary,
                entity_count=len(context.entities),
            )
        )
        self._ledger.check_can_spend(input_tokens=input_tokens, max_output_tokens=max_out)

        result = self._transport.complete(
            model=model,
            prompt=prompt,
            context=context,
            rep=rep,
            seed=seed,
            max_output_tokens=max_output_tokens,
        )
        usage = result.usage
        if usage is None:
            return result

        prompt_tokens = usage.prompt_tokens or input_tokens
        completion_tokens = usage.completion_tokens
        cost = self._ledger.estimate_cost_usd(
            input_tokens=prompt_tokens, output_tokens=completion_tokens
        )
        usage.estimated_cost_usd = cost
        self._ledger.record_request(
            checkpoint_id=checkpoint_id,
            rep=rep,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            phase=self._phase,
            model=result.model,
            metadata={"status": result.metadata.get("status", "")},
        )
        return result


__all__ = [
    "DEFAULT_AUDIT_DIR",
    "DEFAULT_AUDIT_FILENAME",
    "HARD_CAP_USD",
    "INPUT_PRICE_PER_M",
    "OUTPUT_PRICE_PER_M",
    "BenchmarkBudgetLedger",
    "BudgetCapExceededError",
    "BudgetGatedFireworksTransport",
    "BudgetRequestRecord",
    "estimate_cost_usd",
    "estimate_input_tokens",
]
