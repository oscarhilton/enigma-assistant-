"""Scale / noise metrics for Demo Mode evaluation (D07 amendment / D08e).

These measure *shape* of behaviour under volume — compression, suppression,
false alerts per 1k, and stub cost intensity — not premature SLOs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScaleMetrics:
    """Aggregate volume-aware metrics for one evaluation point."""

    message_count: int
    signals_considered: int
    items_surfaced: int
    background_count: int
    background_correctly_ignored: int
    background_false_alerts: int
    noise_count: int
    noise_false_alerts: int
    attention_compression_ratio: float
    background_suppression_rate: float
    noise_suppression_rate: float
    background_false_alerts_per_1k: float
    noise_false_alerts_per_1k: float
    false_alerts_per_1k: float
    remote_calls: int
    estimated_cost_usd: float
    cost_per_1k_messages: float
    remote_calls_per_1k: float
    remote_calls_per_1k_messages: float
    index_size_bytes: int | None = None
    ingest_time_ms: float | None = None
    retrieval_latency_ms: float | None = None
    recall_at_k: float | None = None
    precision: float | None = None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "message_count": self.message_count,
            "signals_considered": self.signals_considered,
            "items_surfaced": self.items_surfaced,
            "background_count": self.background_count,
            "background_correctly_ignored": self.background_correctly_ignored,
            "background_false_alerts": self.background_false_alerts,
            "noise_count": self.noise_count,
            "noise_false_alerts": self.noise_false_alerts,
            "attention_compression_ratio": self.attention_compression_ratio,
            "background_suppression_rate": self.background_suppression_rate,
            "noise_suppression_rate": self.noise_suppression_rate,
            "background_false_alerts_per_1k": self.background_false_alerts_per_1k,
            "noise_false_alerts_per_1k": self.noise_false_alerts_per_1k,
            "false_alerts_per_1k": self.false_alerts_per_1k,
            "remote_calls": self.remote_calls,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cost_per_1k_messages": self.cost_per_1k_messages,
            "remote_calls_per_1k": self.remote_calls_per_1k,
            "remote_calls_per_1k_messages": self.remote_calls_per_1k_messages,
            "index_size_bytes": self.index_size_bytes,
            "ingest_time_ms": self.ingest_time_ms,
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "recall_at_k": self.recall_at_k,
            "precision": self.precision,
        }


def attention_compression_ratio(
    *, signals_considered: int, items_surfaced: int
) -> float:
    """Signals considered : items surfaced (higher = more aggressive filtering)."""
    if items_surfaced <= 0:
        return float(signals_considered) if signals_considered > 0 else 0.0
    return signals_considered / items_surfaced


def background_suppression_rate(
    *, background_total: int, correctly_ignored: int
) -> float:
    """Background items correctly ignored / all background."""
    if background_total <= 0:
        return 1.0
    return max(0.0, min(1.0, correctly_ignored / background_total))


def false_alerts_per_1k(*, false_alerts: int, message_count: int) -> float:
    """Incorrect attention caused by background/noise, normalised per 1k messages."""
    if message_count <= 0:
        return 0.0
    return (false_alerts * 1000.0) / message_count


def cost_per_1k_messages(*, estimated_usd: float, message_count: int) -> float:
    """Stub cost intensity per 1k inbound messages."""
    if message_count <= 0:
        return 0.0
    return (estimated_usd * 1000.0) / message_count


def remote_calls_per_1k(*, remote_calls: int, message_count: int) -> float:
    if message_count <= 0:
        return 0.0
    return (remote_calls * 1000.0) / message_count


def compute_scale_metrics(
    *,
    message_count: int,
    signals_considered: int | None = None,
    items_surfaced: int,
    background_count: int = 0,
    background_false_alerts: int = 0,
    noise_count: int = 0,
    noise_false_alerts: int = 0,
    remote_calls: int = 0,
    estimated_cost_usd: float = 0.0,
    index_size_bytes: int | None = None,
    ingest_time_ms: float | None = None,
    retrieval_latency_ms: float | None = None,
    recall_at_k: float | None = None,
    precision: float | None = None,
) -> ScaleMetrics:
    """Derive compression / suppression / per-1k cost stubs for one N."""
    considered = message_count if signals_considered is None else signals_considered
    bg_ignored = max(0, background_count - background_false_alerts)
    noise_ignored = max(0, noise_count - noise_false_alerts)
    total_false = background_false_alerts + noise_false_alerts
    bg_per_1k = false_alerts_per_1k(
        false_alerts=background_false_alerts, message_count=message_count
    )
    noise_per_1k = false_alerts_per_1k(
        false_alerts=noise_false_alerts, message_count=message_count
    )
    combined_per_1k = false_alerts_per_1k(
        false_alerts=total_false, message_count=message_count
    )
    rpc_per_1k = remote_calls_per_1k(
        remote_calls=remote_calls, message_count=message_count
    )
    return ScaleMetrics(
        message_count=message_count,
        signals_considered=considered,
        items_surfaced=items_surfaced,
        background_count=background_count,
        background_correctly_ignored=bg_ignored,
        background_false_alerts=background_false_alerts,
        noise_count=noise_count,
        noise_false_alerts=noise_false_alerts,
        attention_compression_ratio=attention_compression_ratio(
            signals_considered=considered, items_surfaced=items_surfaced
        ),
        background_suppression_rate=background_suppression_rate(
            background_total=background_count, correctly_ignored=bg_ignored
        ),
        noise_suppression_rate=background_suppression_rate(
            background_total=noise_count, correctly_ignored=noise_ignored
        ),
        background_false_alerts_per_1k=bg_per_1k,
        noise_false_alerts_per_1k=noise_per_1k,
        false_alerts_per_1k=combined_per_1k,
        remote_calls=remote_calls,
        estimated_cost_usd=estimated_cost_usd,
        cost_per_1k_messages=cost_per_1k_messages(
            estimated_usd=estimated_cost_usd, message_count=message_count
        ),
        remote_calls_per_1k=rpc_per_1k,
        remote_calls_per_1k_messages=rpc_per_1k,
        index_size_bytes=index_size_bytes,
        ingest_time_ms=ingest_time_ms,
        retrieval_latency_ms=retrieval_latency_ms,
        recall_at_k=recall_at_k,
        precision=precision,
    )


def scale_metrics_from_dict(raw: dict[str, Any]) -> ScaleMetrics:
    """Rebuild metrics from a serialised ``as_dict`` payload."""
    return compute_scale_metrics(
        message_count=int(raw.get("message_count", raw.get("inbound_messages", 0))),
        signals_considered=int(raw.get("signals_considered", 0)),
        items_surfaced=int(raw.get("items_surfaced", 0)),
        background_count=int(
            raw.get("background_count", raw.get("background_total", 0))
        ),
        background_false_alerts=int(raw.get("background_false_alerts", 0)),
        noise_count=int(raw.get("noise_count", raw.get("noise_total", 0))),
        noise_false_alerts=int(raw.get("noise_false_alerts", 0)),
        remote_calls=int(raw.get("remote_calls", 0)),
        estimated_cost_usd=float(raw.get("estimated_cost_usd", 0.0)),
        index_size_bytes=(
            int(raw["index_size_bytes"])
            if raw.get("index_size_bytes") is not None
            else None
        ),
        ingest_time_ms=(
            float(raw["ingest_time_ms"])
            if raw.get("ingest_time_ms") is not None
            else None
        ),
        retrieval_latency_ms=(
            float(raw["retrieval_latency_ms"])
            if raw.get("retrieval_latency_ms") is not None
            else None
        ),
        recall_at_k=(
            float(raw["recall_at_k"]) if raw.get("recall_at_k") is not None else None
        ),
        precision=(
            float(raw["precision"]) if raw.get("precision") is not None else None
        ),
    )


__all__ = [
    "ScaleMetrics",
    "attention_compression_ratio",
    "background_suppression_rate",
    "compute_scale_metrics",
    "cost_per_1k_messages",
    "false_alerts_per_1k",
    "remote_calls_per_1k",
    "scale_metrics_from_dict",
]
