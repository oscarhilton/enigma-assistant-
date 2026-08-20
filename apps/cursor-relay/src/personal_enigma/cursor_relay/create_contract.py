"""Cursor create-agent contract: env name, named-env safety, dry-run plans, redaction."""

from __future__ import annotations

from typing import Any

from personal_enigma.cursor_relay.allowlist import DispatchTarget

# Allowlisted UUID → Cursor dashboard environment name for env.name serialization.
ENV_UUID_TO_NAME: dict[str, str] = {
    "1baeb513-9c77-11f1-ba66-0e7d0216e441": "enigma-assistant-",
}
CANONICAL_ENV_NAME = "enigma-assistant-"
NAMED_ENV_ALIASES = frozenset({CANONICAL_ENV_NAME, *ENV_UUID_TO_NAME.keys()})

# Allowlisted validation field keys only (truncated).
_VALIDATION_KEYS = frozenset({"code", "message", "field"})
_MAX_FIELD_LEN = 200

# Pending branch claim until status returns the Cursor-generated head.
PENDING_BRANCH = "pending"


def canonicalize_environment_name(environment: str) -> str:
    """Map allowlisted UUID to Cursor env name before serializing env.name."""

    value = environment.strip()
    return ENV_UUID_TO_NAME.get(value, value)


def is_named_cloud_environment(environment: str) -> bool:
    """True when the target uses the bound named cloud environment."""

    return canonicalize_environment_name(environment) == CANONICAL_ENV_NAME


def truncate_field(value: Any, *, limit: int = _MAX_FIELD_LEN) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def extract_validation_fields(payload: Any) -> list[dict[str, str]]:
    """Pull only code/message/field from Cursor error JSON (recursive, truncated)."""

    found: list[dict[str, str]] = []

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            entry = {
                k: truncate_field(obj[k])
                for k in _VALIDATION_KEYS
                if k in obj and obj[k] is not None
            }
            if entry:
                found.append(entry)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(payload)
    # Deduplicate while preserving order
    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict[str, str]] = []
    for item in found:
        key = tuple(sorted(item.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
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


def build_create_payload(
    *,
    prompt: str,
    target: DispatchTarget,
    name: Any = None,
    auto_create_pr: bool = False,
    ticket_path: Any = None,
    job_brief: dict[str, Any] | None = None,
    review_lane: bool = False,
) -> dict[str, Any]:
    """Build the exact Cursor create-agent body for a named cloud environment.

    Contract:
    - ``env.name`` is the canonical name (UUID mapped → ``enigma-assistant-``)
    - ``repos`` is never sent for named cloud environments
    - ``workOnCurrentBranch`` is never set (Cursor-generated feature branch)
    """

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

    env_name = canonicalize_environment_name(target.environment)
    text += (
        f"\n\nRelay branch intent: requested_head={target.head_branch}"
        + (f" base={target.base_branch}" if target.base_branch else "")
        + f" repository={target.repository}"
        + " (actual head is Cursor-generated until status returns it)"
    )

    payload: dict[str, Any] = {
        "prompt": {"text": text},
        "model": {"id": target.model},
        "name": name or f"relay:{target.head_branch}",
        "env": {"type": "cloud", "name": env_name},
        "autoCreatePR": auto_create_pr,
    }
    # Named cloud env: never repos, never workOnCurrentBranch.
    if is_named_cloud_environment(env_name):
        payload.pop("repos", None)
        payload.pop("workOnCurrentBranch", None)
    return payload
