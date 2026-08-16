"""Live Demo attention: alex-v1 synthetic sources → obligations → rank (D14).

Reuses existing packages only. Background streams are built once per session
reset so interactive day/step clicks stay cheap (demo profile, not D08e scale).
Remote reasoning stays off.

Surface policy (attention wind tunnel): calendar existence is not attention;
noise is not commitment; default view surfaces P4–P5 (P3 with timing).
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from personal_enigma.attention import (
    AttentionItem,
    AttentionKind,
    HeuristicAttentionEngine,
    filter_surfaced,
    parse_due_from_body,
    ui_priority_for_kind,
    why_now_glance_for_deadline,
)
from personal_enigma.attention.engine import KIND_PRIORITY
from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateReminder,
)
from personal_enigma.obligations import merge_sources_to_attention
from personal_enigma.simulation.corpus.background import (
    BackgroundBuildResult,
    build_background_stream,
)
from personal_enigma.simulation.scenario import ScenarioPackage, load_scenario
from personal_enigma.simulation.sources.calendar import SyntheticCalendarSource
from personal_enigma.simulation.sources.mail import SyntheticMailSource
from personal_enigma.simulation.sources.reminders import SyntheticReminderSource

_ATTENTION_NS = UUID("a14e0000-0000-4000-8000-000000000014")
_DUE_RE = re.compile(r"Due\s+(\S+)")

_KIND_REASON: dict[AttentionKind, str] = {
    AttentionKind.EXPLICIT_REMINDER: "EXPLICIT_REMINDER",
    AttentionKind.CALENDAR_OBLIGATION: "CALENDAR_OBLIGATION",
    AttentionKind.INFERRED_OBLIGATION: "INFERRED_OBLIGATION",
    AttentionKind.INFERRED_COMMITMENT: "INFERRED_COMMITMENT",
    AttentionKind.PENDING_REPLY: "PENDING_REPLY",
}


def repo_root_from(start: Path | None = None) -> Path:
    """Locate monorepo root that contains ``scenarios/``."""
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / "scenarios").is_dir() and (parent / "packages").is_dir():
            return parent
    raise FileNotFoundError(
        f"Could not locate repo root with scenarios/ (started from {here})"
    )


def resolve_scenario_path(scenario_id: str) -> Path:
    """Resolve ``scenarios/<id>`` via env override or repo walk."""
    override = os.environ.get("ENIGMA_SCENARIOS_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve() / scenario_id
        if candidate.is_dir():
            return candidate
    root = repo_root_from()
    path = root / "scenarios" / scenario_id
    if not path.is_dir():
        raise FileNotFoundError(f"Scenario package not found: {path}")
    return path


def load_demo_scenario(scenario_id: str = "alex-v1") -> ScenarioPackage:
    return load_scenario(resolve_scenario_path(scenario_id))


def background_profile_from_env() -> str:
    return os.environ.get("ENIGMA_DEMO_BACKGROUND_PROFILE", "demo").strip() or "demo"


def build_session_background(
    package: ScenarioPackage,
    *,
    profile: str | None = None,
) -> BackgroundBuildResult | None:
    """Cacheable background stream for the interactive demo profile."""
    name = profile if profile is not None else background_profile_from_env()
    if name in {"", "none", "off", "feature"}:
        return None
    return build_background_stream(package, profile=name)  # type: ignore[arg-type]


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


async def _source_items(source: Any) -> list[dict[str, Any]]:
    batch = await source.get_changes(None)
    return list(batch.items)


def _collapse_reminders(raw: list[dict[str, Any]]) -> list[PrivateReminder]:
    by_id: dict[str, PrivateReminder] = {}
    for item in raw:
        reminder = PrivateReminder.model_validate(item)
        by_id[reminder.id] = reminder
    return list(by_id.values())


def collect_domain_until(
    package: ScenarioPackage,
    *,
    until: datetime,
    background: BackgroundBuildResult | None,
) -> tuple[list[PrivateReminder], list[PrivateMessage], list[PrivateCalendarEvent]]:
    """Synthetic ingest up to ``until`` — no real Gmail/Apple connectors."""
    if background is not None:
        mail = SyntheticMailSource.for_scenario(
            package,
            include_background=True,
            background_stream=background.stream,
            until=until,
        )
    else:
        mail = SyntheticMailSource.for_scenario(
            package,
            include_background=False,
            until=until,
        )
    calendar = SyntheticCalendarSource(package, until=until)
    reminders = SyntheticReminderSource(package, until=until)

    mail_raw = _run(_source_items(mail))
    cal_raw = _run(_source_items(calendar))
    rem_raw = _run(_source_items(reminders))

    messages = [PrivateMessage.model_validate(row) for row in mail_raw]
    events = [PrivateCalendarEvent.model_validate(row) for row in cal_raw]
    rem_list = _collapse_reminders(rem_raw)
    return rem_list, messages, events


def attention_item_id(item: AttentionItem) -> str:
    key = "|".join(item.evidence_ids) if item.evidence_ids else item.title
    return f"att-{uuid5(_ATTENTION_NS, key).hex[:12]}"


def _when_from_body(body: str) -> str | None:
    match = _DUE_RE.search(body)
    if match is None:
        return None
    stamp = match.group(1).rstrip(";")
    try:
        due = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return f"Due {stamp}"
    return f"Due {due.date().isoformat()}"


def _why_now_glance(item: AttentionItem, *, now: datetime) -> str:
    due = parse_due_from_body(item.body)
    labeled = why_now_glance_for_deadline(due, now=now)
    if labeled is not None:
        return labeled
    if item.kind is AttentionKind.EXPLICIT_REMINDER:
        return "Open reminder"
    if item.kind is AttentionKind.CALENDAR_OBLIGATION:
        return "On your calendar"
    if item.kind is AttentionKind.PENDING_REPLY:
        return "Waiting on your reply"
    if item.kind is AttentionKind.INFERRED_COMMITMENT:
        return "Thread or follow-up"
    return "Open loop"


def _confidence_from_ranked(item: AttentionItem) -> float:
    base = KIND_PRIORITY[item.kind]
    # Raw obligation confidence was stored before rank; recover from clamped bonus.
    return max(0.0, min(1.0, float(item.score) - base))


def _attention_rank(item: AttentionItem, *, max_score: float) -> float:
    if max_score <= 0:
        return 0.0
    return max(0.0, min(1.0, float(item.score) / max_score))


def _evidence_lines(body: str) -> list[str]:
    parts = [p.strip() for p in body.split(";") if p.strip()]
    return parts or [body or "No structured evidence attached."]


def build_why_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Evidence → Inference → Decision → Why now? from live attention row."""
    evidence = _evidence_lines(str(row.get("body") or ""))
    title = str(row["title"])
    priority = int(row["priority"])
    kind = str(row["kind"])
    reason = _KIND_REASON.get(AttentionKind(kind), kind.upper())
    return {
        "item_id": row["id"],
        "title": title,
        "headline": "WHY ENIGMA THINKS THIS MATTERS",
        "evidence": evidence,
        "inference": [
            f"Signals were merged into an open item: {title}.",
            "No completion evidence has removed it from the attention set.",
        ],
        "decision": [
            "The item remains unresolved at the simulated clock.",
            f"Surface as a priority-{priority} {kind.replace('_', ' ')}.",
        ],
        "why_now": [
            str(row.get("why_now_glance") or "Within the configured attention window."),
            "Surface now while the simulated timeline still has room to act.",
        ],
        "priority": priority,
        "confidence": float(row["confidence"]),
        "reason_codes": [reason, "UNRESOLVED"],
    }


def refresh_attention_payloads(
    package: ScenarioPackage,
    *,
    until: datetime,
    background: BackgroundBuildResult | None,
    dismissed_ids: set[str] | frozenset[str] = frozenset(),
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], int]:
    """Return UI attention rows, why-by-id, and suppressed count."""
    reminders, messages, events = collect_domain_until(
        package,
        until=until,
        background=background,
    )
    raw_items = merge_sources_to_attention(
        reminders=reminders,
        messages=messages,
        calendar_events=events,
        now=until,
    )
    ranked = HeuristicAttentionEngine(remote_llm_enabled=False).rank(raw_items)
    # Default Attention view: P4–P5 (P3 with timing); P2 stays candidate-only.
    surfaced_items = filter_surfaced(ranked, now=until)
    max_score = max((float(item.score) for item in surfaced_items), default=1.0)

    rows: list[dict[str, Any]] = []
    why_by_id: dict[str, dict[str, Any]] = {}
    for item in surfaced_items:
        item_id = attention_item_id(item)
        if item_id in dismissed_ids:
            continue
        when = _when_from_body(item.body)
        glance = _why_now_glance(item, now=until)
        priority = ui_priority_for_kind(item.kind)
        row = {
            "id": item_id,
            "title": item.title,
            "when": when,
            "why_now_glance": glance,
            # Card stays short; full evidence dump lives on Why.
            "body": item.title,
            "kind": item.kind.value,
            "priority": item.priority or priority,
            "confidence": round(_confidence_from_ranked(item), 4),
            "attention_rank": round(_attention_rank(item, max_score=max_score), 4),
            "evidence_ids": list(item.evidence_ids),
        }
        rows.append(row)
        why_by_id[item_id] = build_why_payload({**row, "body": item.body})

    considered = (
        sum(1 for r in reminders if not r.is_completed)
        + len(messages)
        + len(events)
    )
    suppressed = max(0, considered - len(rows))
    return rows, why_by_id, suppressed
