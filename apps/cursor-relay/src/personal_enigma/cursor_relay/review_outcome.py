"""Extract a structured review outcome from already-returned Cursor run data.

Cursor ``GET /v1/agents/{id}/runs/{runId}`` populates ``result`` (final assistant
reply text) on terminal runs. Review jobs are asked to emit a schema-valid
handoff; this module surfaces a concise verdict from that payload without a
second agent run or extra persistence.

Never copies raw result text onto the handoff (transcript / secret risk).
"""

from __future__ import annotations

import json
from typing import Any

from personal_enigma.cursor_relay.create_contract import scrub_validation_value

_TERMINAL = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})
_APPROVE = frozenset({"approve", "approved", "lgtm"})
_BLOCK = frozenset({"block", "blocked", "deny", "denied", "reject", "rejected"})
_MAX_ITEMS = 5
_MAX_LEN = 200


def extract_review_outcome(
    *,
    run: dict[str, Any] | None,
    agent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return extra observed_state fields, or ``{}`` when nothing structured exists."""

    run = run or {}
    agent = agent or {}
    lifecycle = str(run.get("status") or agent.get("status") or "")
    if lifecycle not in _TERMINAL:
        return {}

    text = _result_text(run, agent)
    if not text:
        return {}

    parsed = _parse_structured(text)
    verdict: str | None = None
    findings: list[str] = []
    risks: list[str] = []

    if isinstance(parsed, dict):
        verdict = _verdict_from_structured(parsed, agent=agent)
        findings = _findings_from_structured(parsed)
        risks = _capped_strings(parsed.get("residual_risks"))
    else:
        verdict = _normalize_verdict(text)

    extra: dict[str, Any] = {}
    if verdict is not None:
        extra["review_verdict"] = verdict
    if findings:
        extra["review_findings"] = findings
    if risks:
        extra["review_residual_risks"] = risks
    if extra:
        extra["review_result_source"] = "cursor_run_result"
    return extra


def _result_text(run: dict[str, Any], agent: dict[str, Any]) -> str | None:
    raw: Any = run.get("result")
    if isinstance(raw, dict):
        raw = raw.get("text") or raw.get("result")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    summary = agent.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return None


def _parse_structured(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    try:
        obj, _end = decoder.raw_decode(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        if start < 0:
            return None
        try:
            obj, _end = decoder.raw_decode(stripped[start:])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _verdict_from_structured(parsed: dict[str, Any], *, agent: dict[str, Any]) -> str | None:
    observed = parsed.get("observed_state")
    obs = observed if isinstance(observed, dict) else {}
    for candidate in (
        obs.get("review_verdict"),
        obs.get("verdict"),
        parsed.get("review_verdict"),
        parsed.get("verdict"),
        parsed.get("outcome"),
    ):
        verdict = _normalize_verdict(candidate)
        if verdict is not None:
            return verdict

    action = parsed.get("recommended_action")
    kind = ""
    if isinstance(action, dict):
        kind = str(action.get("kind") or "")
    if kind == "stop_needs_human":
        return "BLOCK"
    if kind == "no_action" and _looks_like_review(parsed, agent):
        return "APPROVE"
    return None


def _looks_like_review(parsed: dict[str, Any], agent: dict[str, Any]) -> bool:
    name = str(agent.get("name") or "").lower()
    if "review" in name:
        return True
    action = parsed.get("recommended_action")
    if isinstance(action, dict) and action.get("kind") == "request_review":
        return True
    observed = parsed.get("observed_state")
    if isinstance(observed, dict) and observed.get("relay_tool") == "request_review":
        return True
    return False


def _findings_from_structured(parsed: dict[str, Any]) -> list[str]:
    evidence = parsed.get("evidence")
    if not isinstance(evidence, list):
        return []
    out: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        summary = item.get("summary")
        if isinstance(summary, str) and summary.strip():
            out.append(summary.strip())
        if len(out) >= _MAX_ITEMS:
            break
    return _capped_strings(out)


def _capped_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        if item is None:
            continue
        cleaned = scrub_validation_value(item, limit=_MAX_LEN)
        if cleaned and cleaned != "[redacted]":
            out.append(cleaned)
        if len(out) >= _MAX_ITEMS:
            break
    return out


def _normalize_verdict(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip().split()[0].strip(".,:;()[]{}\"'") if str(value).strip() else ""
    lowered = token.lower()
    if lowered in _APPROVE:
        return "APPROVE"
    if lowered in _BLOCK:
        return "BLOCK"
    return None
