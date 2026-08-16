"""Write Demo Mode evaluation reports under ``reports/<run_id>/``."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_FILES = (
    "summary.json",
    "metrics.json",
    "failures.json",
    "timeline.json",
    "privacy.json",
    "cost.json",
    "SUMMARY.md",
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def write_report(
    report_dir: Path,
    *,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    failures: dict[str, Any],
    timeline: dict[str, Any],
    privacy: dict[str, Any],
    cost: dict[str, Any],
    markdown: str,
) -> Path:
    """Persist the Phase 2 report layout; returns ``report_dir``."""
    report_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "summary.json": summary,
        "metrics.json": metrics,
        "failures.json": failures,
        "timeline.json": timeline,
        "privacy.json": privacy,
        "cost.json": cost,
    }
    for name, payload in payloads.items():
        (report_dir / name).write_text(
            json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (report_dir / "SUMMARY.md").write_text(markdown, encoding="utf-8")
    return report_dir


def render_summary_markdown(
    *,
    run_id: str,
    scenario: str,
    status: str,
    attention: dict[str, Any],
    privacy: dict[str, Any],
    cost: dict[str, Any],
) -> str:
    lines = [
        f"# Evaluation report `{run_id}`",
        "",
        f"- Scenario: `{scenario}`",
        f"- Status: **{status}**",
        "",
        "## Attention",
        f"- Critical recall: {attention.get('critical_recall', 0):.3f}",
        f"- Precision: {attention.get('precision', 0):.3f}",
        f"- Duplicate rate: {attention.get('duplicate_rate', 0):.3f}",
        f"- Stale-alert rate: {attention.get('stale_alert_rate', 0):.3f}",
        "",
        "## Privacy",
        f"- Direct identifier leaks: {privacy.get('direct_identifier_leaks', 0)}",
        f"- Blocked requests: {privacy.get('blocked_requests', 0)}",
        "",
        "## Cost (stub)",
        f"- Total USD: {cost.get('total_usd', 0):.4f}",
        f"- Monthly equivalent: {cost.get('monthly_usd', 0):.4f}",
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "REPORT_FILES",
    "render_summary_markdown",
    "write_report",
]
