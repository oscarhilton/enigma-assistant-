"""Cursor create-agent contract: env name, named-env safety, dry-run plans, redaction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from personal_enigma.cursor_relay.allowlist import DispatchTarget

# Allowlisted UUID → Cursor *API registry* name for env.name serialization.
# IMPORTANT: this is the dashboard-registered Cloud Environment name that
# POST /v1/agents looks up — NOT the UUID, and NOT automatically equal to
# `.cursor/environment.json` "name" (repo-file config). Live environment-info
# for this UUID has reported name=null until the dashboard display name is set.
DEFAULT_ENV_UUID_TO_NAME: dict[str, str] = {
    "1baeb513-9c77-11f1-ba66-0e7d0216e441": "enigma-assistant-",
}
# Back-compat alias for tests / importers.
ENV_UUID_TO_NAME = DEFAULT_ENV_UUID_TO_NAME
CANONICAL_ENV_NAME = "enigma-assistant-"
NAMED_ENV_ALIASES = frozenset({CANONICAL_ENV_NAME, *DEFAULT_ENV_UUID_TO_NAME.keys()})

# Allowlisted validation field keys only (truncated + scrubbed).
_VALIDATION_KEYS = frozenset({"code", "message", "field"})
_MAX_FIELD_LEN = 200
_MAX_VALIDATION_ENTRIES = 5
_MAX_WALK_NODES = 200
_MAX_WALK_DEPTH = 16
_REDACTED = "[redacted]"

# Pending branch claim until status returns the Cursor-generated head.
PENDING_BRANCH = "pending"


def canonicalize_environment_name(
    environment: str,
    *,
    uuid_to_name: Mapping[str, str] | None = None,
) -> str:
    """Map allowlisted UUID to Cursor API registry name before serializing env.name.

    ``uuid_to_name`` defaults to ``DEFAULT_ENV_UUID_TO_NAME`` (overridable via
    ``RELAY_ENV_UUID_TO_NAME`` on the relay host). The resulting string must
    exist as a named cloud environment in the Cursor dashboard / API.
    """

    value = environment.strip()
    mapping = DEFAULT_ENV_UUID_TO_NAME if uuid_to_name is None else uuid_to_name
    return mapping.get(value, value)


def is_named_cloud_environment(
    environment: str,
    *,
    uuid_to_name: Mapping[str, str] | None = None,
    canonical_names: frozenset[str] | None = None,
) -> bool:
    """True when the target uses a bound named cloud environment."""

    resolved = canonicalize_environment_name(environment, uuid_to_name=uuid_to_name)
    names = (
        frozenset({CANONICAL_ENV_NAME, *DEFAULT_ENV_UUID_TO_NAME.values()})
        if canonical_names is None
        else canonical_names
    )
    return resolved in names


def is_cursor_env_not_found_validation(entries: list[dict[str, str]] | None) -> bool:
    """True when Cursor validation indicates unknown env.name registry lookup."""

    for item in entries or []:
        message = str(item.get("message") or "").lower()
        if "no cloud environment named" in message:
            return True
        field = str(item.get("field") or "").lower()
        if field in {"env.name", "env"} and "not found" in message:
            return True
    return False


def looks_secret_like(value: Any) -> bool:
    """True when a validation string looks like a credential or auth material."""

    lowered = str(value).lower()
    needles = (
        "bearer",
        "authorization",
        "api_key",
        "api-key",
        "token",
        "sk-",
        "key_",
    )
    return any(n in lowered for n in needles)


def scrub_validation_value(value: Any, *, limit: int = _MAX_FIELD_LEN) -> str:
    """Truncate allowlisted values; replace secret-like content entirely."""

    if looks_secret_like(value):
        return _REDACTED
    return truncate_field(value, limit=limit)


def truncate_field(value: Any, *, limit: int = _MAX_FIELD_LEN) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def extract_validation_fields(payload: Any) -> list[dict[str, str]]:
    """Pull only code/message/field from Cursor error JSON.

    Caps returned entries, bounds recursion/nodes, and scrubs secret-like values
    completely (never partially exposed).
    """

    found: list[dict[str, str]] = []
    nodes = 0

    def _walk(obj: Any, *, depth: int) -> None:
        nonlocal nodes
        if len(found) >= _MAX_VALIDATION_ENTRIES:
            return
        if depth > _MAX_WALK_DEPTH or nodes >= _MAX_WALK_NODES:
            return
        nodes += 1
        if isinstance(obj, dict):
            entry = {
                k: scrub_validation_value(obj[k])
                for k in _VALIDATION_KEYS
                if k in obj and obj[k] is not None
            }
            if entry:
                found.append(entry)
            if len(found) >= _MAX_VALIDATION_ENTRIES:
                return
            for v in obj.values():
                _walk(v, depth=depth + 1)
                if len(found) >= _MAX_VALIDATION_ENTRIES:
                    return
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, depth=depth + 1)
                if len(found) >= _MAX_VALIDATION_ENTRIES:
                    return

    _walk(payload, depth=0)
    return sanitize_validation_entries(found)


def sanitize_validation_entries(
    entries: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    """Cap + scrub an already-parsed validation list (handoff/audit/mock path)."""

    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict[str, str]] = []
    for item in entries or []:
        if not isinstance(item, dict):
            continue
        cleaned = {
            k: scrub_validation_value(item[k])
            for k in _VALIDATION_KEYS
            if k in item and item[k] is not None
        }
        if not cleaned:
            continue
        key = tuple(sorted(cleaned.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
        if len(unique) >= _MAX_VALIDATION_ENTRIES:
            break
    return unique


def redact_create_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact a create-agent request for dry-run plans / evidence."""

    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "prompt" and isinstance(value, dict):
            text = str(value.get("text") or "")
            out["prompt"] = {
                "text_chars": len(text),
                "text_sha256_8": _short_hash(text),
            }
        elif key in {"authorization", "api_key", "token", "cursor_api_key"}:
            continue
        else:
            out[key] = value
    return out


def _short_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _apply_optional_model(payload: dict[str, Any], model: str | None) -> dict[str, Any]:
    """Include model.id only when the conductor explicitly chose a model."""

    if model:
        payload["model"] = {"id": model}
    return payload


def build_create_payload(
    *,
    prompt: str,
    target: DispatchTarget,
    name: Any = None,
    auto_create_pr: bool = False,
    ticket_path: Any = None,
    job_brief: dict[str, Any] | None = None,
    review_lane: bool = False,
    uuid_to_name: Mapping[str, str] | None = None,
    pr_url: str | None = None,
) -> dict[str, Any]:
    """Build the Cursor create-agent body.

    Modes:
    - **existing_pr** (``pr_url`` set): native ``repos[].prUrl`` +
      ``workOnCurrentBranch=true``; no ``env`` (mutually exclusive with named env).
      ``autoCreatePR`` is forced false — the PR already exists.
    - **named_env** (default): ``env.name`` registry name; never ``repos`` /
      ``workOnCurrentBranch`` (Cursor-generated feature branch).
    """

    from personal_enigma.cursor_relay.pr_target import (
        assert_pr_matches_repository,
        github_https_repo_url,
        parse_github_pr_url,
    )

    text = prompt
    if ticket_path:
        text = f"Ticket: {ticket_path}\n\n{text}"
    if review_lane:
        text = "[REVIEW LANE — do not merge, do not push to main/master]\n" + text
    if job_brief:
        auth = job_brief.get("authorization") or {}
        text += (
            "\n\nJob brief authorization: "
            f"dry_run={auth.get('dry_run', True)} "
            f"allow_push={auth.get('allow_push', False)} "
            f"allow_open_pr={auth.get('allow_open_pr', False)} "
            f"allow_merge=false (relay enforced)."
        )

    mapping = DEFAULT_ENV_UUID_TO_NAME if uuid_to_name is None else uuid_to_name
    env_name = canonicalize_environment_name(target.environment, uuid_to_name=mapping)

    if pr_url and str(pr_url).strip():
        parsed = parse_github_pr_url(str(pr_url))
        assert_pr_matches_repository(parsed, target.repository)
        text += (
            f"\n\nRelay PR target: pr_url={parsed.normalized_url} "
            f"requested_head_intent={target.head_branch} "
            f"repository={target.repository} "
            "(branch identity from GitHub PR head; workOnCurrentBranch=true)"
        )
        return _apply_optional_model(
            {
                "prompt": {"text": text},
                "name": name or f"relay:pr-{parsed.number}",
                "repos": [
                    {
                        "url": github_https_repo_url(target.repository),
                        "prUrl": parsed.normalized_url,
                    }
                ],
                "workOnCurrentBranch": True,
                # Existing PR — never open a second busboy PR.
                "autoCreatePR": False,
            },
            target.model,
        )

    text += (
        f"\n\nRelay branch intent: requested_head={target.head_branch}"
        + (f" base={target.base_branch}" if target.base_branch else "")
        + f" repository={target.repository}"
        + " (actual head is Cursor-generated until status returns it)"
    )

    payload: dict[str, Any] = _apply_optional_model(
        {
            "prompt": {"text": text},
            "name": name or f"relay:{target.head_branch}",
            "env": {"type": "cloud", "name": env_name},
            "autoCreatePR": auto_create_pr,
        },
        target.model,
    )
    # Named cloud env: never repos, never workOnCurrentBranch.
    canonical_names = frozenset({*mapping.values(), CANONICAL_ENV_NAME})
    if is_named_cloud_environment(
        env_name, uuid_to_name=mapping, canonical_names=canonical_names
    ):
        payload.pop("repos", None)
        payload.pop("workOnCurrentBranch", None)
    return payload
