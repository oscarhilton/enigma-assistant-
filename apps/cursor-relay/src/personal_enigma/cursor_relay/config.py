"""Relay configuration loaded from process environment (never from agent VMs)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

DEFAULT_REPOSITORIES = frozenset({"oscarhilton/enigma-assistant-"})
DEFAULT_ENVIRONMENTS = frozenset(
    {
        "1baeb513-9c77-11f1-ba66-0e7d0216e441",
        "enigma-assistant-",
    }
)
DEFAULT_BRANCH_PREFIXES = ("ticket/", "cursor/", "agent/")
DEFAULT_MODELS = frozenset(
    {
        "composer-2",
        "composer-2.5",
        "claude-4-sonnet-thinking",
        "claude-4.5-sonnet-thinking",
        "gpt-5.2",
    }
)
FORBIDDEN_HEAD_BRANCHES = frozenset({"main", "master"})
# Stacked PR bases may be main/master or an allowlisted feature-branch prefix.
DEFAULT_ALLOWED_BASE_BRANCHES = frozenset({"main", "master"})


@dataclass(frozen=True)
class CallerRecord:
    """Authenticated caller mapped from a relay bearer token."""

    caller_id: str
    roles: frozenset[str]
    display_name: str | None = None


@dataclass
class RelayConfig:
    """Server-side relay settings.

    ``cursor_api_key`` is optional so unit tests can inject a mock Cursor client
    without ever touching a real key. Production must set ``CURSOR_API_KEY``.
    """

    cursor_api_key: str | None = None
    cursor_api_base: str = "https://api.cursor.com"
    caller_tokens: dict[str, CallerRecord] = field(default_factory=dict)
    allowed_repositories: frozenset[str] = field(default_factory=lambda: DEFAULT_REPOSITORIES)
    allowed_environments: frozenset[str] = field(default_factory=lambda: DEFAULT_ENVIRONMENTS)
    allowed_branch_prefixes: tuple[str, ...] = DEFAULT_BRANCH_PREFIXES
    allowed_models: frozenset[str] = field(default_factory=lambda: DEFAULT_MODELS)
    forbidden_head_branches: frozenset[str] = field(default_factory=lambda: FORBIDDEN_HEAD_BRANCHES)
    allowed_base_branches: frozenset[str] = field(
        default_factory=lambda: DEFAULT_ALLOWED_BASE_BRANCHES
    )
    max_in_flight: int = 3
    max_spend_units: float = 50.0
    spend_per_create: float = 1.0
    audit_path: str | None = None
    handoff_schema_path: str | None = None
    # In-memory idempotency/quotas are process-local. Multi-replica requires
    # RELAY_SINGLE_INSTANCE=0 and RELAY_SHARED_STORE_URL (guarded at load).
    single_instance: bool = True
    shared_store_url: str | None = None


def _parse_caller_tokens(raw: str | None) -> dict[str, CallerRecord]:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        msg = "RELAY_AUTH_TOKENS must be a JSON object mapping token → caller"
        raise ValueError(msg)
    out: dict[str, CallerRecord] = {}
    for token, entry in data.items():
        if not isinstance(entry, dict):
            msg = f"Caller entry for token must be an object, got {type(entry)}"
            raise ValueError(msg)
        caller_id = str(entry["caller_id"])
        roles = frozenset(str(r) for r in entry.get("roles", []))
        display_name = entry.get("display_name")
        out[str(token)] = CallerRecord(
            caller_id=caller_id,
            roles=roles,
            display_name=str(display_name) if display_name else None,
        )
    return out


def _csv_set(raw: str | None, default: frozenset[str]) -> frozenset[str]:
    if raw is None or raw.strip() == "":
        return default
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _csv_tuple(raw: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None or raw.strip() == "":
        return default
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def load_config_from_env(environ: dict[str, str] | None = None) -> RelayConfig:
    """Load relay config from process env. Never reads Cloud Agent secret stores."""

    env: dict[str, str] = dict(os.environ if environ is None else environ)
    # Reject ChatGPT credentials masquerading as Cursor config.
    for banned in ("CHATGPT_API_KEY", "OPENAI_CHATGPT_TOKEN", "CHATGPT_SESSION"):
        if banned in env and "CURSOR_API_KEY" not in env:
            # Presence alone is fine; using them as Cursor auth is not.
            pass
        if env.get("CURSOR_API_KEY") and env.get("CURSOR_API_KEY") == env.get(banned):
            msg = "ChatGPT credentials must not be used as CURSOR_API_KEY"
            raise ValueError(msg)

    key = env.get("CURSOR_API_KEY") or None
    single_raw = env.get("RELAY_SINGLE_INSTANCE", "1").strip().lower()
    single_instance = single_raw not in {"0", "false", "no"}
    shared_store = env.get("RELAY_SHARED_STORE_URL") or None
    if not single_instance and not shared_store:
        msg = (
            "RELAY_SINGLE_INSTANCE=0 requires RELAY_SHARED_STORE_URL; "
            "in-memory idempotency/quotas are unsafe across replicas"
        )
        raise ValueError(msg)

    return RelayConfig(
        cursor_api_key=key,
        cursor_api_base=env.get("CURSOR_API_BASE", "https://api.cursor.com").rstrip("/"),
        caller_tokens=_parse_caller_tokens(env.get("RELAY_AUTH_TOKENS")),
        allowed_repositories=_csv_set(env.get("RELAY_ALLOWED_REPOS"), DEFAULT_REPOSITORIES),
        allowed_environments=_csv_set(env.get("RELAY_ALLOWED_ENVIRONMENTS"), DEFAULT_ENVIRONMENTS),
        allowed_branch_prefixes=_csv_tuple(
            env.get("RELAY_ALLOWED_BRANCH_PREFIXES"), DEFAULT_BRANCH_PREFIXES
        ),
        allowed_models=_csv_set(env.get("RELAY_ALLOWED_MODELS"), DEFAULT_MODELS),
        allowed_base_branches=_csv_set(
            env.get("RELAY_ALLOWED_BASE_BRANCHES"), DEFAULT_ALLOWED_BASE_BRANCHES
        ),
        max_in_flight=int(env.get("RELAY_MAX_IN_FLIGHT", "3")),
        max_spend_units=float(env.get("RELAY_MAX_SPEND_UNITS", "50")),
        spend_per_create=float(env.get("RELAY_SPEND_PER_CREATE", "1")),
        audit_path=env.get("RELAY_AUDIT_PATH"),
        handoff_schema_path=env.get("RELAY_HANDOFF_SCHEMA_PATH"),
        single_instance=single_instance,
        shared_store_url=shared_store,
    )


def config_public_dict(cfg: RelayConfig) -> dict[str, Any]:
    """Serialize config for docs/status without leaking secrets."""

    return {
        "cursor_api_base": cfg.cursor_api_base,
        "cursor_api_key_configured": bool(cfg.cursor_api_key),
        "allowed_repositories": sorted(cfg.allowed_repositories),
        "allowed_environments": sorted(cfg.allowed_environments),
        "allowed_branch_prefixes": list(cfg.allowed_branch_prefixes),
        "allowed_models": sorted(cfg.allowed_models),
        "max_in_flight": cfg.max_in_flight,
        "max_spend_units": cfg.max_spend_units,
        "caller_count": len(cfg.caller_tokens),
        "allowed_base_branches": sorted(cfg.allowed_base_branches),
        "single_instance": cfg.single_instance,
        "shared_store_configured": bool(cfg.shared_store_url),
    }
