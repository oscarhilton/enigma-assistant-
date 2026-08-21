"""Existing-PR targeting — native Cursor repos[].prUrl semantics.

Removes the "busboy" pattern of reconstructing PR/branch identity from a
stale long-lived agent workspace. Prefer GitHub PR URL + workOnCurrentBranch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from personal_enigma.cursor_relay.allowlist import (
    AllowlistError,
    check_head_branch,
    normalize_repository,
)
from personal_enigma.cursor_relay.config import RelayConfig

# Cursor-minted feature branches (CLOUD-03 mock / live auto heads).
_STALE_AUTO_HEAD = re.compile(r"^cursor/auto-", re.IGNORECASE)

_PR_PATH = re.compile(
    r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)/?$",
    re.IGNORECASE,
)


class PrTargetError(Exception):
    """Invalid PR target or stale-workspace create attempt."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParsedPrUrl:
    owner: str
    repo: str
    number: int
    normalized_url: str

    @property
    def repository(self) -> str:
        return f"{self.owner}/{self.repo}"


def parse_github_pr_url(pr_url: str) -> ParsedPrUrl:
    """Parse and normalize a GitHub pull request URL."""

    raw = (pr_url or "").strip()
    if not raw:
        raise PrTargetError(
            "pr_url is required when targeting an existing PR",
            code="invalid_pr_url",
        )
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
        "github.com",
        "www.github.com",
    }:
        raise PrTargetError(
            "pr_url must be an https://github.com/{owner}/{repo}/pull/{n} URL",
            code="invalid_pr_url",
        )
    match = _PR_PATH.match(parsed.path or "")
    if match is None:
        raise PrTargetError(
            "pr_url path must be /{owner}/{repo}/pull/{number}",
            code="invalid_pr_url",
        )
    owner = match.group("owner")
    repo = match.group("repo")
    number = int(match.group("number"))
    normalized = f"https://github.com/{owner}/{repo}/pull/{number}"
    return ParsedPrUrl(owner=owner, repo=repo, number=number, normalized_url=normalized)


def github_https_repo_url(repository: str) -> str:
    """Build https://github.com/{owner}/{repo} from an allowlisted repository id."""

    normalized = normalize_repository(repository)
    return f"https://github.com/{normalized}"


def assert_pr_matches_repository(pr: ParsedPrUrl, repository: str) -> None:
    """Fail closed when pr_url repo does not match the dispatch repository."""

    expected = normalize_repository(repository)
    actual = normalize_repository(pr.repository)
    if actual != expected:
        raise PrTargetError(
            f"pr_url repository '{actual}' does not match dispatch repository '{expected}'",
            code="pr_repo_mismatch",
        )


def looks_like_stale_cursor_workspace_head(head_branch: str) -> bool:
    """True for Cursor-auto minted heads that must not stand in for PR identity."""

    head = (head_branch or "").strip()
    return bool(_STALE_AUTO_HEAD.match(head))


def assert_create_branch_identity(
    *,
    head_branch: str,
    pr_url: str | None,
) -> None:
    """Block create-agent busboy: auto heads without native PR URL targeting.

    Greenfield ticket/cursor/agent heads remain allowed. Cursor ``auto-*`` heads
    without ``pr_url`` are treated as stale-workspace reconstruction attempts.
    """

    if pr_url and str(pr_url).strip():
        return
    if looks_like_stale_cursor_workspace_head(head_branch):
        raise PrTargetError(
            "Refusing create against Cursor auto head without pr_url — "
            "pass pr_url (native existing-PR target) or an allowlisted ticket head",
            code="stale_workspace_branch",
        )


_PR_PERMISSION_NEEDLES = (
    "createpullrequest",
    "create_pull_request",
    "create pull request",
    "pullrequest.create",
    "not authorized to open",
    "lacks permission to create pull request",
    "permission to create pull request",
    "pull request creation failed",
)

_PR_CONTEXT_TERMS = (
    "pull request",
    "pullrequest",
    "createpullrequest",
    "create pull request",
)


def is_cursor_pr_permission_failure(
    entries: list[dict[str, str]] | None = None,
    *,
    message: str = "",
    http_status: int | None = None,
) -> bool:
    """True when Cursor/GitHub rejected PR creation due to host/app permissions."""

    chunks: list[str] = [message.lower()]
    for item in entries or []:
        for key in ("message", "code", "field"):
            if key in item and item[key] is not None:
                chunks.append(str(item[key]).lower())
    blob = " ".join(chunks)
    if any(n in blob for n in _PR_PERMISSION_NEEDLES):
        return True
    if "resource not accessible by integration" in blob and any(
        n in blob for n in _PR_CONTEXT_TERMS
    ):
        return True
    if http_status == 403 and any(n in blob for n in _PR_CONTEXT_TERMS):
        return True
    return False


class GitHubPrResolver(Protocol):
    """Resolve the live GitHub head ref for an existing pull request."""

    def resolve_head_branch(self, pr: ParsedPrUrl) -> str: ...


@dataclass
class MockGitHubPrResolver:
    """Test double mapping normalized PR URLs to head branch names."""

    heads: dict[str, str] = field(default_factory=dict)

    def resolve_head_branch(self, pr: ParsedPrUrl) -> str:
        head = self.heads.get(pr.normalized_url)
        if not head:
            msg = f"No mock GitHub head configured for {pr.normalized_url}"
            raise PrTargetError(msg, code="pr_head_unresolved")
        return head


class HttpGitHubPrResolver:
    """Resolve PR head via the public GitHub REST API (no token for public repos)."""

    def resolve_head_branch(self, pr: ParsedPrUrl) -> str:
        url = f"https://api.github.com/repos/{pr.owner}/{pr.repo}/pulls/{pr.number}"
        try:
            response = httpx.get(
                url,
                headers={"Accept": "application/vnd.github+json"},
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                msg = f"GitHub pull request not found: {pr.normalized_url}"
                raise PrTargetError(msg, code="pr_not_found") from exc
            msg = f"Unable to resolve GitHub PR head (HTTP {status})"
            raise PrTargetError(msg, code="pr_head_unresolved") from exc
        except httpx.HTTPError as exc:
            msg = "Unable to resolve GitHub PR head (transport error)"
            raise PrTargetError(msg, code="pr_head_unresolved") from exc

        data = response.json()
        head_ref = (data.get("head") or {}).get("ref")
        if not head_ref or not str(head_ref).strip():
            msg = f"GitHub PR head ref missing for {pr.normalized_url}"
            raise PrTargetError(msg, code="pr_head_unresolved")
        return str(head_ref).strip()


def validate_existing_pr_head(
    config: RelayConfig,
    *,
    parsed: ParsedPrUrl,
    resolver: GitHubPrResolver,
) -> str:
    """Resolve GitHub PR head and run it through the relay branch allowlist."""

    head = resolver.resolve_head_branch(parsed)
    try:
        return check_head_branch(config, head)
    except AllowlistError as exc:
        raise PrTargetError(str(exc), code=exc.code) from exc


def classify_cursor_error_code(
    *,
    http_status: int | None,
    validation: list[dict[str, str]] | None,
    message: str = "",
) -> str | None:
    """Return a specific relay error code, or None to keep the generic mapping."""

    from personal_enigma.cursor_relay.create_contract import (
        is_cursor_env_not_found_validation,
    )

    if is_cursor_pr_permission_failure(
        validation, message=message, http_status=http_status
    ):
        return "host_permission_blocker"
    if http_status == 400 and is_cursor_env_not_found_validation(validation):
        return "cursor_env_not_found"
    return None


def as_allowlist_error(exc: PrTargetError) -> AllowlistError:
    """Map PrTargetError into AllowlistError for relay deny path (dimension=pr_target)."""

    err = AllowlistError(str(exc), dimension="pr_target")
    err.code = exc.code
    return err


def pr_target_observed_fields(
    pr: ParsedPrUrl,
    *,
    github_pr_head: str | None = None,
) -> dict[str, Any]:
    """Handoff observed_state fields for existing-PR creates."""

    fields: dict[str, Any] = {
        "target_mode": "existing_pr",
        "pr_url": pr.normalized_url,
        "pr_number": pr.number,
        "branch_identity_source": "github_pr_head",
    }
    if github_pr_head:
        fields["github_pr_head"] = github_pr_head
    return fields
