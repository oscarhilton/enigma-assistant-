"""Build and validate conductor-shaped handoff documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# Default schema path relative to monorepo root when running from workspace.
_REPO_SCHEMA = (
    Path(__file__).resolve().parents[5] / "docs" / "cloud-agents" / "handoff-schema.json"
)


def load_handoff_schema(path: str | Path | None = None) -> dict[str, Any]:
    schema_path = Path(path) if path else _REPO_SCHEMA
    with schema_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        msg = "handoff schema must be a JSON object"
        raise TypeError(msg)
    return data


def validate_handoff(doc: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    sch = schema if schema is not None else load_handoff_schema()
    Draft202012Validator(sch).validate(doc)


def make_handoff(
    *,
    branch: str,
    ticket_ids: list[str],
    rationale: str,
    action_kind: str,
    scope: str = "infra_only",
    worktree_clean: bool = True,
    open_prs: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    tests: list[dict[str, Any]] | None = None,
    residual_risks: list[str] | None = None,
    requires_oscar: bool = False,
    oscar_reasons: list[str] | None = None,
    pr_base: str | None = None,
    pr_head: str | None = None,
    extra_observed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observed: dict[str, Any] = {
        "branch": branch,
        "worktree_clean": worktree_clean,
        "ticket_ids": ticket_ids,
        "open_prs": open_prs or [],
    }
    if extra_observed:
        observed.update(extra_observed)

    action: dict[str, Any] = {"kind": action_kind, "rationale": rationale, "branch": branch}
    if pr_base:
        action["pr_base"] = pr_base
    if pr_head:
        action["pr_head"] = pr_head

    doc: dict[str, Any] = {
        "observed_state": observed,
        "evidence": evidence
        or [{"kind": "note", "summary": "Relay structured handoff (no raw transcript)"}],
        "scope_classification": scope,
        "recommended_action": action,
        "tests": tests or [],
        "residual_risks": residual_risks or [],
        "requires_oscar": {
            "required": requires_oscar,
            "reasons": oscar_reasons or [],
        },
    }
    validate_handoff(doc)
    return doc


def denial_handoff(
    *,
    tool: str,
    reason: str,
    code: str,
    branch: str = "unknown",
    ticket_ids: list[str] | None = None,
    validation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    extra: dict[str, Any] = {"relay_denial_code": code}
    if validation:
        extra["cursor_validation"] = validation
    return make_handoff(
        branch=branch,
        ticket_ids=ticket_ids or ["CLOUD-02"],
        rationale=f"Denied {tool}: {reason} ({code})",
        action_kind="stop_needs_human",
        scope="infra_only",
        residual_risks=[f"relay_denial:{code}"],
        requires_oscar=True,
        oscar_reasons=[reason],
        evidence=[
            {
                "kind": "note",
                "summary": f"Relay denied tool '{tool}' with code {code}",
            }
        ],
        extra_observed=extra,
    )


def success_handoff_for_tool(
    *,
    tool: str,
    agent_id: str | None,
    run_id: str | None,
    branch: str,
    ticket_ids: list[str],
    summary: str,
    action_kind: str = "no_action",
    open_prs: list[dict[str, Any]] | None = None,
    extra_observed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observed_extra = {
        "relay_tool": tool,
        "agent_id": agent_id,
        "run_id": run_id,
    }
    if extra_observed:
        observed_extra.update(extra_observed)
    return make_handoff(
        branch=branch,
        ticket_ids=ticket_ids,
        rationale=summary,
        action_kind=action_kind,
        scope="infra_only",
        open_prs=open_prs,
        evidence=[
            {
                "kind": "note",
                "summary": summary,
                "ref": agent_id or "",
            }
        ],
        extra_observed=observed_extra,
    )


def strip_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure default responses never include secret material."""

    banned_keys = {
        "cursor_api_key",
        "authorization",
        "api_key",
        "token",
        "chatgpt_session",
        "chatgpt_api_key",
    }

    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items() if k.lower() not in banned_keys}
        if isinstance(obj, list):
            return [_walk(x) for x in obj]
        if isinstance(obj, str):
            lowered = obj.lower()
            if "sk-cur" in lowered or lowered.startswith("key_"):
                return "[redacted]"
            return obj
        return obj

    result = _walk(payload)
    if not isinstance(result, dict):
        msg = "strip_secrets expected dict payload"
        raise TypeError(msg)
    return result
