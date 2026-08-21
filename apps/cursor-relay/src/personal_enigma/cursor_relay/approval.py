"""Approval policy for write-capable MCP tools.

No silent main merges. Conductor jobs remain read-only unless the job brief
explicitly authorizes push / PR / merge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_enigma.cursor_relay.auth import AuthenticatedCaller


class ApprovalError(Exception):
    def __init__(self, message: str, *, code: str = "approval_denied") -> None:
        super().__init__(message)
        self.code = code


# Tool → minimum role required
TOOL_ROLES: dict[str, frozenset[str]] = {
    "status": frozenset({"reader", "dispatcher", "approver", "admin"}),
    "result": frozenset({"reader", "dispatcher", "approver", "admin"}),
    "dispatch": frozenset({"dispatcher", "admin"}),
    "follow_up": frozenset({"dispatcher", "admin"}),
    "request_review": frozenset({"approver", "admin"}),
    "cancel": frozenset({"approver", "admin"}),
}


@dataclass(frozen=True)
class JobBriefAuth:
    """Explicit authorizations carried in a job brief."""

    allow_push: bool = False
    allow_open_pr: bool = False
    allow_merge: bool = False
    dry_run: bool = True


def parse_job_brief_auth(job_brief: dict[str, Any] | None) -> JobBriefAuth:
    if not job_brief:
        return JobBriefAuth()
    auth = job_brief.get("authorization") or {}
    if not isinstance(auth, dict):
        return JobBriefAuth()
    return JobBriefAuth(
        allow_push=bool(auth.get("allow_push", False)),
        allow_open_pr=bool(auth.get("allow_open_pr", False)),
        allow_merge=bool(auth.get("allow_merge", False)),
        dry_run=bool(auth.get("dry_run", True)),
    )


def caller_may_invoke(caller: AuthenticatedCaller, tool: str) -> None:
    allowed = TOOL_ROLES.get(tool)
    if allowed is None:
        raise ApprovalError(f"Unknown tool: {tool}")
    if caller.has_role("admin"):
        return
    if not any(caller.has_role(role) for role in allowed):
        raise ApprovalError(
            f"Caller '{caller.caller_id}' lacks role for tool '{tool}' "
            f"(need one of {sorted(allowed)})"
        )


def enforce_write_policy(
    tool: str,
    *,
    caller: AuthenticatedCaller,
    job_brief: dict[str, Any] | None = None,
    auto_create_pr: bool = False,
    merge_requested: bool = False,
) -> JobBriefAuth:
    """Gate write tools. Silent main merges are always denied."""

    caller_may_invoke(caller, tool)
    brief = parse_job_brief_auth(job_brief)

    if merge_requested or brief.allow_merge:
        raise ApprovalError(
            "Merge to default branch is never permitted via the relay; "
            "require human merge after review",
            code="merge_forbidden",
        )

    if tool in {"dispatch", "request_review", "follow_up"}:
        if auto_create_pr and not brief.allow_open_pr:
            raise ApprovalError(
                "auto_create_pr requires job_brief.authorization.allow_open_pr=true",
                code="pr_not_authorized",
            )
        if not brief.dry_run and not (brief.allow_push or brief.allow_open_pr):
            # Non-dry-run create without push/PR auth is still allowed for
            # agent work on a feature branch, but document the boundary.
            pass

    if tool == "cancel":
        # cancel is approval-gated by role only
        pass

    return brief
