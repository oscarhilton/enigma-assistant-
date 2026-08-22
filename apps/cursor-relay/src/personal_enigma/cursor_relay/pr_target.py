"""Existing-PR targeting — native Cursor repos[].prUrl semantics.

Removes the "busboy" pattern of reconstructing PR/branch identity from a
stale long-lived agent workspace. Prefer GitHub PR URL + workOnCurrentBranch.
"""

from __future__ import annotations

import os
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


@dataclass(frozen=True)
class ResolvedPrHead:
    """Resolved PR head identity from GitHub.

    `repo_full_name` is required so the relay can reject fork/untrusted heads
    before using `ref` for allowlist checks.
    """

    ref: str
    repo_full_name: str
    repo_is_fork: bool | None = None


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


_PR_PERMISSION_FIELDS = frozenset({"createpullrequest", "autocreatepr"})


def is_cursor_pr_permission_failure(
    entries: list[dict[str, str]] | None = None,
    *,
    message: str = "",
    http_status: int | None = None,
) -> bool:
    """True when Cursor/GitHub rejected PR creation due to host/app permissions."""

    for item in entries or []:
        field_val = str(item.get("field", "")).strip().lower()
        if field_val in _PR_PERMISSION_FIELDS:
            return True

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

    def resolve_head(self, pr: ParsedPrUrl) -> ResolvedPrHead: ...


@dataclass
class MockGitHubPrResolver:
    """Test double mapping normalized PR URLs to head branch names."""

    heads: dict[str, str | ResolvedPrHead] = field(default_factory=dict)

    def resolve_head(self, pr: ParsedPrUrl) -> ResolvedPrHead:
        item = self.heads.get(pr.normalized_url)
        if not item:
            msg = f"No mock GitHub head configured for {pr.normalized_url}"
            raise PrTargetError(msg, code="pr_head_unresolved")
        if isinstance(item, ResolvedPrHead):
            return item
        # Default: same-repository head, matching `pr_url` repo.
        return ResolvedPrHead(ref=str(item), repo_full_name=pr.repository, repo_is_fork=False)


class HttpGitHubPrResolver:
    """Resolve PR head via GitHub REST API.

    Uses ``RELAY_GITHUB_TOKEN`` or ``GITHUB_TOKEN`` from relay host env when set
    (server-side only — never MCP args). Unauthenticated access works for public
    repos; private repos require a token on the relay host.
    """

    def __init__(self, *, token: str | None = None) -> None:
        if token is not None:
            self._token = token.strip() or None
        else:
            self._token = (
                os.environ.get("RELAY_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
            )
            self._token = self._token.strip() if self._token else None

    def _request_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def resolve_head(self, pr: ParsedPrUrl) -> ResolvedPrHead:
        url = f"https://api.github.com/repos/{pr.owner}/{pr.repo}/pulls/{pr.number}"
        try:
            response = httpx.get(
                url,
                headers=self._request_headers(),
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                hint = (
                    " (set RELAY_GITHUB_TOKEN on relay host for private repos)"
                    if not self._token
                    else ""
                )
                msg = f"GitHub pull request not found: {pr.normalized_url}{hint}"
                raise PrTargetError(msg, code="pr_not_found") from exc
            msg = f"Unable to resolve GitHub PR head (HTTP {status})"
            raise PrTargetError(msg, code="pr_head_unresolved") from exc
        except httpx.HTTPError as exc:
            msg = "Unable to resolve GitHub PR head (transport error)"
            raise PrTargetError(msg, code="pr_head_unresolved") from exc

        data = response.json()
        head = data.get("head") or {}
        head_ref = head.get("ref")
        if not head_ref or not str(head_ref).strip():
            msg = f"GitHub PR head ref missing for {pr.normalized_url}"
            raise PrTargetError(msg, code="pr_head_unresolved")
        head_repo = head.get("repo") or {}
        head_repo_full_name = head_repo.get("full_name")
        if not head_repo_full_name or not str(head_repo_full_name).strip():
            msg = f"GitHub PR head repository missing for {pr.normalized_url}"
            raise PrTargetError(msg, code="pr_head_unresolved")
        fork_val = head_repo.get("fork")
        repo_is_fork: bool | None = fork_val if isinstance(fork_val, bool) else None
        return ResolvedPrHead(
            ref=str(head_ref).strip(),
            repo_full_name=str(head_repo_full_name).strip(),
            repo_is_fork=repo_is_fork,
        )


def validate_existing_pr_head(
    config: RelayConfig,
    *,
    parsed: ParsedPrUrl,
    resolver: GitHubPrResolver,
) -> str:
    """Resolve GitHub PR head and run it through the relay branch allowlist."""

    resolved = resolver.resolve_head(parsed)
    expected_repo = normalize_repository(parsed.repository)
    actual_repo = normalize_repository(resolved.repo_full_name)
    if actual_repo != expected_repo:
        fork_hint = ""
        if resolved.repo_is_fork is True:
            fork_hint = " (fork)"
        msg = (
            "Refusing PR target: GitHub PR head repository "
            f"'{actual_repo}'{fork_hint} does not match expected '{expected_repo}'"
        )
        raise PrTargetError(msg, code="pr_head_repo_mismatch")
    head = resolved.ref
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
