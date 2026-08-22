"""Regression tests: existing-PR targeting + permission / stale-workspace guards."""

from __future__ import annotations

import json

import httpx
import pytest
from tokens import DISPATCHER_CALLER

from personal_enigma.cursor_relay.allowlist import DispatchTarget
from personal_enigma.cursor_relay.config import RelayConfig
from personal_enigma.cursor_relay.create_contract import build_create_payload, redact_create_payload
from personal_enigma.cursor_relay.cursor_client import MockCursorClient, _safe_http_error
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.pr_target import (
    HttpGitHubPrResolver,
    MockGitHubPrResolver,
    PrTargetError,
    ResolvedPrHead,
    is_cursor_pr_permission_failure,
    parse_github_pr_url,
    validate_existing_pr_head,
)
from personal_enigma.cursor_relay.relay import RelayService

ENV_UUID = "1baeb513-9c77-11f1-ba66-0e7d0216e441"
PR_URL = "https://github.com/oscarhilton/enigma-assistant-/pull/136"
PR_HEAD = "cursor/sprint2-relay-pr-target-47cd"
FORBIDDEN_PR_URL = "https://github.com/oscarhilton/enigma-assistant-/pull/999"


def _target() -> DispatchTarget:
    return DispatchTarget(
        repository="oscarhilton/enigma-assistant-",
        environment=ENV_UUID,
        head_branch="ticket/kernel-01-turn-kernel",
        model="composer-2",
        base_branch="main",
    )


def test_parse_github_pr_url_normalizes() -> None:
    parsed = parse_github_pr_url(
        "https://www.github.com/oscarhilton/enigma-assistant-/pull/136/"
    )
    assert parsed.normalized_url == PR_URL
    assert parsed.number == 136
    assert parsed.repository == "oscarhilton/enigma-assistant-"


def test_existing_pr_payload_uses_native_prurl_not_named_env() -> None:
    payload = build_create_payload(
        prompt="fix the open PR",
        target=_target(),
        name="relay:pr-fix",
        auto_create_pr=True,  # must be forced off for existing PR
        pr_url=PR_URL,
    )
    assert "env" not in payload
    assert payload["workOnCurrentBranch"] is True
    assert payload["autoCreatePR"] is False
    assert payload["repos"] == [
        {
            "url": "https://github.com/oscarhilton/enigma-assistant-",
            "prUrl": PR_URL,
        }
    ]
    # Branch identity must not be smuggled via startingRef.
    assert "startingRef" not in payload["repos"][0]


def test_pr_url_repo_mismatch_denied(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "pr-mismatch-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/kernel-01-turn-kernel",
            "pr_url": "https://github.com/other/other-repo/pull/1",
            "prompt": "nope",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    rationale = result["recommended_action"]["rationale"]
    assert "pr_repo_mismatch" in rationale or "does not match" in rationale


def test_stale_auto_head_without_pr_url_denied(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    """Busboy protection: cursor/auto-* is not durable PR identity."""

    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "stale-auto-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "cursor/auto-0007",
            "prompt": "continue stale workspace",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    rationale = result["recommended_action"]["rationale"]
    assert "stale_workspace_branch" in rationale or "auto head" in rationale.lower()


def test_stale_auto_head_allowed_with_pr_url(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "stale-with-pr-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "cursor/auto-0007",
            "pr_url": PR_URL,
            "prompt": "work on existing PR",
            "auto_create_pr": True,
            "job_brief": {
                "authorization": {
                    "dry_run": True,
                }
            },
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    observed = result["observed_state"]
    assert observed["target_mode"] == "existing_pr"
    assert observed["pr_url"] == PR_URL
    assert observed["branch_identity_source"] == "github_pr_head"
    assert observed["github_pr_head"] == PR_HEAD
    assert observed["branch"] == "pending"
    plan = observed["create_request_plan"]
    assert "env" not in plan
    assert plan["workOnCurrentBranch"] is True
    assert plan["autoCreatePR"] is False
    assert plan["repos"][0]["prUrl"] == PR_URL


def test_is_cursor_pr_permission_failure_detects_create_pull_request() -> None:
    assert is_cursor_pr_permission_failure(
        [
            {
                "code": "forbidden",
                "message": "Resource not accessible by integration",
                "field": "createPullRequest",
            }
        ]
    )
    assert is_cursor_pr_permission_failure(
        message="GitHub App lacks permission to create pull request",
        http_status=403,
    )
    assert not is_cursor_pr_permission_failure(
        [{"message": "No cloud environment named enigma-assistant- was found."}]
    )
    assert not is_cursor_pr_permission_failure(
        message="Resource not accessible by integration",
        http_status=403,
    )
    assert not is_cursor_pr_permission_failure(
        message="Insufficient permissions to create repository",
        http_status=403,
    )
    assert is_cursor_pr_permission_failure(
        [
            {
                "code": "forbidden",
                "message": "Resource not accessible by integration",
                "field": "autoCreatePR",
            }
        ]
    )


def test_http_github_resolver_sends_token_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url: str, *, headers: dict[str, str], timeout: float) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = headers
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "head": {
                    "ref": "cursor/sprint2-relay-pr-target-47cd",
                    "repo": {
                        "full_name": "oscarhilton/enigma-assistant-",
                        "fork": False,
                    },
                }
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    resolver = HttpGitHubPrResolver(token="ghp_test_token")
    parsed = parse_github_pr_url(PR_URL)
    resolved = resolver.resolve_head(parsed)
    assert resolved.ref == PR_HEAD
    assert resolved.repo_full_name == "oscarhilton/enigma-assistant-"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer ghp_test_token"


def test_http_403_pr_permission_maps_to_host_blocker() -> None:
    request = httpx.Request("POST", "https://api.cursor.com/v1/agents")
    response = httpx.Response(
        403,
        request=request,
        json={
            "message": "Resource not accessible by integration",
            "code": "forbidden",
            "field": "createPullRequest",
        },
    )
    exc = httpx.HTTPStatusError("denied", request=request, response=response)
    err = _safe_http_error(exc)
    assert err.code == "host_permission_blocker"
    assert "not a branch identity failure" in str(err).lower()
    assert "createPullRequest" in json.dumps(err.validation)


def test_mock_create_pr_permission_surfaces_host_blocker(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    mock_cursor.fail_next = "http_403_pr_permission"
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "perm-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/cloud-pr-perm",
            "prompt": "open pr",
            "auto_create_pr": True,
            "job_brief": {
                "authorization": {
                    "dry_run": False,
                    "allow_push": True,
                    "allow_open_pr": True,
                }
            },
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    rationale = result["recommended_action"]["rationale"]
    assert "host_permission_blocker" in rationale
    assert "branch" not in rationale.lower() or "not a branch" in rationale.lower()


def test_forbidden_github_pr_head_denied(
    service: RelayService,
    mock_cursor: MockCursorClient,
    relay_config: RelayConfig,
) -> None:
    github = MockGitHubPrResolver(
        heads={FORBIDDEN_PR_URL: "main"},
    )
    svc = RelayService(relay_config, cursor=mock_cursor, github=github)
    result = svc.invoke(
        "dispatch",
        {
            "idempotency_key": "forbidden-pr-head-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/kernel-01-turn-kernel",
            "pr_url": FORBIDDEN_PR_URL,
            "prompt": "attempt forbidden PR head",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    rationale = result["recommended_action"]["rationale"]
    assert "forbidden" in rationale.lower() or "allowlist" in rationale.lower()


def test_validate_existing_pr_head_allowlists_resolved_branch(
    relay_config: RelayConfig,
) -> None:
    parsed = parse_github_pr_url(PR_URL)
    github = MockGitHubPrResolver(heads={PR_URL: PR_HEAD})
    assert (
        validate_existing_pr_head(relay_config, parsed=parsed, resolver=github)
        == PR_HEAD
    )


def test_validate_existing_pr_head_rejects_untrusted_fork_head_repo(
    relay_config: RelayConfig,
) -> None:
    parsed = parse_github_pr_url(PR_URL)
    github = MockGitHubPrResolver(
        heads={
            PR_URL: ResolvedPrHead(
                ref=PR_HEAD,
                repo_full_name="evilcorp/enigma-assistant-",
                repo_is_fork=True,
            )
        }
    )
    with pytest.raises(PrTargetError) as excinfo:
        validate_existing_pr_head(relay_config, parsed=parsed, resolver=github)
    assert excinfo.value.code == "pr_head_repo_mismatch"


def test_redact_preserves_pr_target_shape() -> None:
    payload = build_create_payload(prompt="x" * 40, target=_target(), pr_url=PR_URL)
    redacted = redact_create_payload(payload)
    assert redacted["repos"][0]["prUrl"] == PR_URL
    assert "text" not in redacted["prompt"]
