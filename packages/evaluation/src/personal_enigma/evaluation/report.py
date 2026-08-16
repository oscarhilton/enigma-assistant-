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
    suppression: dict[str, Any] | None = None,
    scale: dict[str, Any] | None = None,
    storyline: dict[str, Any] | None = None,
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
        (
            "- Cost per simulated month: "
            f"{cost.get('cost_per_simulated_month', cost.get('monthly_usd', 0)):.4f}"
        ),
        "",
    ]
    if suppression:
        bg_rate = suppression.get("background_suppression_rate", 0)
        fa_rate = suppression.get("background_false_alerts_per_1000", 0)
        compression = suppression.get("attention_compression_ratio", 0)
        lines.extend(
            [
                "## Noise suppression",
                f"- Background suppression rate: {bg_rate:.3f}",
                f"- Background false alerts / 1k: {fa_rate:.3f}",
                f"- Attention compression ratio: {compression:.1f} : 1",
                "",
            ]
        )
    if scale:
        remote_rate = scale.get(
            "remote_reasoning_rate_per_1k",
            scale.get("remote_calls_per_1k", 0),
        )
        lines.extend(
            [
                "## Scale stubs",
                f"- Remote reasoning rate / 1k: {remote_rate:.3f}",
                f"- Cost per 1k messages: {scale.get('cost_per_1k_messages', 0):.4f}",
                "",
            ]
        )
    if storyline:
        lines.extend(
            [
                "## Storyline recall under noise (A/B)",
                f"- Spine critical recall: {storyline.get('spine_critical_recall', 0):.3f}",
                f"- With background: {storyline.get('with_background_critical_recall', 0):.3f}",
                f"- Drop: {storyline.get('drop', 0):.3f} (max {storyline.get('max_drop', 0):.3f})",
                f"- Passed: {storyline.get('passed', False)}",
                "",
            ]
        )
    return "\n".join(lines)


__all__ = [
    "REPORT_FILES",
    "render_summary_markdown",
    "write_report",
]
