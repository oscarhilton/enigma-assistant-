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
    """Authenticated caller identity (relay-host config only — never MCP args)."""

    caller_id: str
    roles: frozenset[str]
    display_name: str | None = None


@dataclass
class RelayConfig:
    """Server-side relay settings.

    ``cursor_api_key`` is optional so unit tests can inject a mock Cursor client
    without ever touching a real key. Production must set ``CURSOR_API_KEY``.

    ``tunnel_caller`` is the fixed single-user identity for the Secure MCP
    Tunnel pilot (``RELAY_TUNNEL_CALLER``). Multi-user deployments require
    MCP OAuth — not model-visible bearer tokens.
    """

    cursor_api_key: str | None = None
    cursor_api_base: str = "https://api.cursor.com"
    tunnel_caller: CallerRecord | None = None
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
    # UUID → Cursor API registry env.name (dashboard name). Overridable via
    # RELAY_ENV_UUID_TO_NAME JSON object on the relay host.
    env_uuid_to_name: dict[str, str] = field(default_factory=dict)


def _parse_tunnel_caller(raw: str | None) -> CallerRecord | None:
    if not raw or not raw.strip():
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        msg = "RELAY_TUNNEL_CALLER must be a JSON object {caller_id, roles}"
        raise ValueError(msg)
    caller_id = data.get("caller_id")
    if not caller_id or not str(caller_id).strip():
        msg = "RELAY_TUNNEL_CALLER.caller_id is required"
        raise ValueError(msg)
    roles_raw = data.get("roles", [])
    if not isinstance(roles_raw, list):
        msg = "RELAY_TUNNEL_CALLER.roles must be a JSON array"
        raise ValueError(msg)
    roles = frozenset(str(r) for r in roles_raw)
    if not roles:
        msg = "RELAY_TUNNEL_CALLER.roles must be non-empty"
        raise ValueError(msg)
    display_name = data.get("display_name")
    return CallerRecord(
        caller_id=str(caller_id).strip(),
        roles=roles,
        display_name=str(display_name) if display_name else None,
    )


def _csv_set(raw: str | None, default: frozenset[str]) -> frozenset[str]:
    if raw is None or raw.strip() == "":
        return default
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _csv_tuple(raw: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None or raw.strip() == "":
        return default
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _parse_env_uuid_to_name(raw: str | None) -> dict[str, str]:
    """Parse RELAY_ENV_UUID_TO_NAME JSON; default to create_contract map."""

    from personal_enigma.cursor_relay.create_contract import DEFAULT_ENV_UUID_TO_NAME

    if raw is None or not raw.strip():
        return dict(DEFAULT_ENV_UUID_TO_NAME)
    data = json.loads(raw)
    if not isinstance(data, dict):
        msg = "RELAY_ENV_UUID_TO_NAME must be a JSON object {uuid: api_env_name}"
        raise ValueError(msg)
    out: dict[str, str] = {}
    for key, value in data.items():
        if not str(key).strip() or not str(value).strip():
            msg = "RELAY_ENV_UUID_TO_NAME entries must be non-empty strings"
            raise ValueError(msg)
        out[str(key).strip()] = str(value).strip()
    if not out:
        msg = "RELAY_ENV_UUID_TO_NAME must be non-empty when set"
        raise ValueError(msg)
    return out


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

    # Legacy RELAY_AUTH_TOKENS must not be used as a model-visible secret map.
    # Secure MCP Tunnel uses RELAY_TUNNEL_CALLER only.
    if env.get("RELAY_AUTH_TOKENS") and not env.get("RELAY_TUNNEL_CALLER"):
        # Fail closed: operators must migrate to tunnel caller (no bearer in MCP).
        msg = (
            "RELAY_AUTH_TOKENS is retired for the Secure MCP Tunnel pilot; "
            "set RELAY_TUNNEL_CALLER instead (multi-user requires MCP OAuth)"
        )
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
        tunnel_caller=_parse_tunnel_caller(env.get("RELAY_TUNNEL_CALLER")),
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
        env_uuid_to_name=_parse_env_uuid_to_name(env.get("RELAY_ENV_UUID_TO_NAME")),
    )


def config_public_dict(cfg: RelayConfig) -> dict[str, Any]:
    """Serialize config for docs/status without leaking secrets."""

    return {
        "cursor_api_base": cfg.cursor_api_base,
        "cursor_api_key_configured": bool(cfg.cursor_api_key),
        "tunnel_caller_configured": cfg.tunnel_caller is not None,
        "tunnel_caller_id": cfg.tunnel_caller.caller_id if cfg.tunnel_caller else None,
        "tunnel_roles": sorted(cfg.tunnel_caller.roles) if cfg.tunnel_caller else [],
        "allowed_repositories": sorted(cfg.allowed_repositories),
        "allowed_environments": sorted(cfg.allowed_environments),
        "allowed_branch_prefixes": list(cfg.allowed_branch_prefixes),
        "allowed_models": sorted(cfg.allowed_models),
        "max_in_flight": cfg.max_in_flight,
        "max_spend_units": cfg.max_spend_units,
        "allowed_base_branches": sorted(cfg.allowed_base_branches),
        "single_instance": cfg.single_instance,
        "shared_store_configured": bool(cfg.shared_store_url),
        "env_uuid_to_name": dict(sorted(cfg.env_uuid_to_name.items())),
    }
