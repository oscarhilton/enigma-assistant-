"""MCP tool handlers: dispatch, status, follow_up, request_review, cancel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from personal_enigma.cursor_relay.allowlist import AllowlistError, validate_dispatch_target
from personal_enigma.cursor_relay.approval import (
    ApprovalError,
    enforce_write_policy,
    parse_job_brief_auth,
)
from personal_enigma.cursor_relay.audit import AuditLog, hash_prompt
from personal_enigma.cursor_relay.auth import AuthenticatedCaller
from personal_enigma.cursor_relay.config import RelayConfig, config_public_dict
from personal_enigma.cursor_relay.create_contract import (
    DEFAULT_ENV_UUID_TO_NAME,
    PENDING_BRANCH,
    build_create_payload,
    canonicalize_environment_name,
    redact_create_payload,
)
from personal_enigma.cursor_relay.cursor_client import (
    CursorApiError,
    CursorClient,
    HttpCursorClient,
    MockCursorClient,
)
from personal_enigma.cursor_relay.handoff import (
    denial_handoff,
    strip_secrets,
    success_handoff_for_tool,
)
from personal_enigma.cursor_relay.idempotency import IdempotencyError, IdempotencyStore
from personal_enigma.cursor_relay.quotas import QuotaError, QuotaTracker

MCP_TOOLS = ("dispatch", "status", "follow_up", "request_review", "cancel")


class RelayService:
    """Authenticated relay implementing the CLOUD-02 MCP surface."""

    def __init__(
        self,
        config: RelayConfig,
        *,
        cursor: CursorClient | None = None,
        audit: AuditLog | None = None,
        idempotency: IdempotencyStore | None = None,
        quotas: QuotaTracker | None = None,
    ) -> None:
        self.config = config
        if cursor is not None:
            self.cursor = cursor
        elif config.cursor_api_key:
            self.cursor = HttpCursorClient(
                api_key=config.cursor_api_key,
                base_url=config.cursor_api_base,
            )
        else:
            # Safe default for local/unit use — never invent a real key.
            self.cursor = MockCursorClient()
        self.audit = audit or AuditLog(
            path=Path(config.audit_path) if config.audit_path else None
        )
        self.idempotency = idempotency or IdempotencyStore()
        self.quotas = quotas or QuotaTracker(
            max_in_flight=config.max_in_flight,
            max_spend_units=config.max_spend_units,
            spend_per_create=config.spend_per_create,
        )

    def _env_uuid_to_name(self) -> dict[str, str]:
        """Active UUID→API registry name map (host override or defaults)."""

        return self.config.env_uuid_to_name or dict(DEFAULT_ENV_UUID_TO_NAME)

    def invoke(
        self,
        tool: str,
        params: dict[str, Any] | None = None,
        *,
        caller: AuthenticatedCaller | None = None,
    ) -> dict[str, Any]:
        """Invoke a relay tool with an internally injected caller identity.

        The public MCP surface never accepts bearer tokens. Callers are either
        the Secure MCP Tunnel identity from relay-host config (injected by
        ``McpStdioServer``) or an explicit ``AuthenticatedCaller`` in tests /
        trusted in-process callers. Missing caller is anonymous denial —
        including for ``status``.
        """

        params = dict(params or {})
        if caller is None:
            self.audit.emit(
                tool=tool,
                caller_id="anonymous",
                decision="deny",
                detail="No authenticated caller at trusted transport boundary",
                extra={"code": "unauthenticated"},
            )
            return strip_secrets(
                denial_handoff(
                    tool=tool,
                    reason="No authenticated caller at trusted transport boundary",
                    code="unauthenticated",
                )
            )

        if tool not in MCP_TOOLS:
            return self._deny(caller, tool, f"Unknown tool '{tool}'", "unknown_tool", params)

        try:
            if tool == "dispatch":
                result = self._dispatch(caller, params)
            elif tool == "status":
                result = self._status(caller, params)
            elif tool == "follow_up":
                result = self._follow_up(caller, params)
            elif tool == "request_review":
                result = self._request_review(caller, params)
            elif tool == "cancel":
                result = self._cancel(caller, params)
            else:  # pragma: no cover
                result = self._deny(caller, tool, "unreachable", "unknown_tool", params)
        except (ApprovalError, AllowlistError, IdempotencyError, QuotaError, CursorApiError) as exc:
            code = getattr(exc, "code", "denied")
            validation = getattr(exc, "validation", None)
            return self._deny(
                caller,
                tool,
                str(exc),
                code,
                params,
                validation=validation if isinstance(validation, list) else None,
            )
        except KeyError as exc:
            return self._deny(
                caller, tool, f"Missing required field: {exc}", "invalid_params", params
            )
        except Exception as exc:  # noqa: BLE001 — last-resort schema-valid failure
            # Never leak secrets via exception strings.
            safe = "Relay internal error"
            detail = type(exc).__name__
            return self._deny(
                caller, tool, f"{safe} ({detail})", "relay_internal_error", params
            )

        return strip_secrets(result)

    def _deny(
        self,
        caller: AuthenticatedCaller,
        tool: str,
        reason: str,
        code: str,
        params: dict[str, Any],
        *,
        validation: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        self.audit.emit(
            tool=tool,
            caller_id=caller.caller_id,
            decision="deny",
            detail=reason,
            idempotency_key=params.get("idempotency_key"),
            extra={"code": code, "validation": validation or []},
        )
        return strip_secrets(
            denial_handoff(
                tool=tool,
                reason=reason,
                code=code,
                branch=str(params.get("head_branch") or params.get("branch") or "unknown"),
                ticket_ids=_ticket_ids(params),
                validation=validation,
            )
        )

    def _dispatch(self, caller: AuthenticatedCaller, params: dict[str, Any]) -> dict[str, Any]:
        key = self.idempotency.require_key("dispatch", params.get("idempotency_key"))
        cached = self.idempotency.get("dispatch", key)
        if cached is not None:
            self.audit.emit(
                tool="dispatch",
                caller_id=caller.caller_id,
                decision="idempotent_replay",
                agent_id=(cached.get("observed_state") or {}).get("agent_id"),
                run_id=(cached.get("observed_state") or {}).get("run_id"),
                idempotency_key=key,
            )
            return cached

        brief = params.get("job_brief")
        if brief is not None and not isinstance(brief, dict):
            msg = "job_brief must be an object"
            raise ApprovalError(msg, code="invalid_params")

        brief_auth = enforce_write_policy(
            "dispatch",
            caller=caller,
            job_brief=brief if isinstance(brief, dict) else None,
            auto_create_pr=bool(params.get("auto_create_pr", False)),
            merge_requested=bool(params.get("merge", False)),
        )

        target = validate_dispatch_target(
            self.config,
            repository=str(params["repository"]),
            environment=str(params["environment"]),
            head_branch=str(params["head_branch"]),
            model=str(params.get("model") or "composer-2"),
            base_branch=str(params["base_branch"]) if params.get("base_branch") else None,
        )

        prompt = str(params.get("prompt") or params.get("ticket_path") or "")
        if not prompt.strip():
            raise ApprovalError("prompt or ticket_path is required", code="invalid_params")

        ph = hash_prompt(prompt)
        mapping = self._env_uuid_to_name()
        payload = build_create_payload(
            prompt=prompt,
            target=target,
            name=params.get("name"),
            auto_create_pr=bool(params.get("auto_create_pr", False)),
            ticket_path=params.get("ticket_path"),
            job_brief=brief if isinstance(brief, dict) else None,
            uuid_to_name=mapping,
        )
        env_name = canonicalize_environment_name(target.environment, uuid_to_name=mapping)
        redacted_plan = redact_create_payload(payload)

        # Genuine dry_run: validate + redacted plan only — never POST /v1/agents.
        if brief_auth.dry_run:
            handoff = success_handoff_for_tool(
                tool="dispatch",
                agent_id=None,
                run_id=None,
                branch=PENDING_BRANCH,
                ticket_ids=_ticket_ids(params),
                summary="Dry-run: create-agent plan validated (no POST /v1/agents)",
                action_kind="no_action",
                extra_observed={
                    "dry_run": True,
                    "mutating": False,
                    "requested_head_branch": target.head_branch,
                    "actual_head_branch": None,
                    "repository": target.repository,
                    "environment": env_name,
                    "environment_input": target.environment,
                    "model": target.model,
                    "prompt_hash": ph,
                    "create_request_plan": redacted_plan,
                },
            )
            self.idempotency.put("dispatch", key, handoff)
            self.audit.emit(
                tool="dispatch",
                caller_id=caller.caller_id,
                decision="allow",
                prompt_hash=ph,
                usage={},
                idempotency_key=key,
                extra={"dry_run": True, "allowlist": "pass"},
            )
            return handoff

        self.quotas.check_create()
        ref = self.cursor.create_agent(payload)
        self.quotas.record_create(ref.agent_id)

        handoff = success_handoff_for_tool(
            tool="dispatch",
            agent_id=ref.agent_id,
            run_id=ref.run_id,
            branch=PENDING_BRANCH,
            ticket_ids=_ticket_ids(params),
            summary=f"Dispatched agent {ref.agent_id} run {ref.run_id}",
            action_kind="no_action",
            extra_observed={
                "dry_run": False,
                "mutating": True,
                "requested_head_branch": target.head_branch,
                "actual_head_branch": None,
                "repository": target.repository,
                "environment": env_name,
                "environment_input": target.environment,
                "model": target.model,
                "agent_url": ref.url,
                "prompt_hash": ph,
                "create_request_plan": redacted_plan,
            },
        )
        self.idempotency.put("dispatch", key, handoff)
        self.audit.emit(
            tool="dispatch",
            caller_id=caller.caller_id,
            decision="allow",
            agent_id=ref.agent_id,
            run_id=ref.run_id,
            prompt_hash=ph,
            usage={"spend_units": self.quotas.spend_per_create},
            idempotency_key=key,
            extra={"allowlist": "pass", "quotas": self.quotas.snapshot()},
        )
        return handoff

    def _status(self, caller: AuthenticatedCaller, params: dict[str, Any]) -> dict[str, Any]:
        enforce_write_policy("status", caller=caller)
        agent_id = str(params["agent_id"])
        agent = self.cursor.get_agent(agent_id)
        run_id = str(params.get("run_id") or agent.get("latestRunId") or "")
        run: dict[str, Any] = {}
        if run_id:
            run = self.cursor.get_run(agent_id, run_id)

        # Never return raw transcripts — only lifecycle metadata.
        status = run.get("status") or agent.get("status") or "UNKNOWN"
        branches = ((run.get("git") or {}).get("branches")) or []
        prs = []
        for entry in branches:
            if entry.get("prUrl"):
                prs.append(
                    {
                        "number": _pr_number(entry.get("prUrl")),
                        "base": str(params.get("base_branch") or "main"),
                        "head": entry.get("branch") or "",
                    }
                )

        # Actual head only when Cursor status returns it — never the requester's claim alone.
        actual_head = branches[0].get("branch") if branches else None
        requested = params.get("head_branch")
        head = str(actual_head or PENDING_BRANCH)
        handoff = success_handoff_for_tool(
            tool="status",
            agent_id=agent_id,
            run_id=run_id or None,
            branch=head,
            ticket_ids=_ticket_ids(params),
            summary=f"Agent {agent_id} status={status}",
            action_kind="no_action",
            open_prs=prs,
            extra_observed={
                "lifecycle_status": status,
                "agent_url": agent.get("url"),
                "requested_head_branch": requested,
                "actual_head_branch": actual_head,
                "config": config_public_dict(self.config),
            },
        )
        self.audit.emit(
            tool="status",
            caller_id=caller.caller_id,
            decision="allow",
            agent_id=agent_id,
            run_id=run_id or None,
            usage={},
        )
        return handoff

    def _follow_up(self, caller: AuthenticatedCaller, params: dict[str, Any]) -> dict[str, Any]:
        # follow_up creates work — treat as write-capable; require idempotency when creating.
        key = self.idempotency.require_key("follow_up", params.get("idempotency_key"))
        cached = self.idempotency.get("follow_up", key)
        if cached is not None:
            return cached

        brief = params.get("job_brief")
        enforce_write_policy(
            "follow_up",
            caller=caller,
            job_brief=brief if isinstance(brief, dict) else None,
            merge_requested=bool(params.get("merge", False)),
        )
        agent_id = str(params["agent_id"])
        prompt = str(params["prompt"])
        ph = hash_prompt(prompt)
        self.quotas.check_create()

        ref = self.cursor.create_run(agent_id, {"prompt": {"text": prompt}})
        # follow_up creates a run on an existing agent — count toward spend, not new in-flight agent
        self.quotas.spend_units += self.quotas.spend_per_create

        handoff = success_handoff_for_tool(
            tool="follow_up",
            agent_id=agent_id,
            run_id=ref.run_id,
            branch=str(params.get("head_branch") or "unknown"),
            ticket_ids=_ticket_ids(params),
            summary=f"Follow-up run {ref.run_id} on agent {agent_id}",
            extra_observed={"prompt_hash": ph},
        )
        self.idempotency.put("follow_up", key, handoff)
        self.audit.emit(
            tool="follow_up",
            caller_id=caller.caller_id,
            decision="allow",
            agent_id=agent_id,
            run_id=ref.run_id,
            prompt_hash=ph,
            usage={"spend_units": self.quotas.spend_per_create},
            idempotency_key=key,
        )
        return handoff

    def _request_review(
        self, caller: AuthenticatedCaller, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Request structured review without merging.

        When ``create_run`` is true (default) or ``agent_id`` is absent, creates a
        new review agent — idempotency key required.
        """

        create_new = bool(params.get("create_run", params.get("agent_id") is None))
        brief = params.get("job_brief")
        enforce_write_policy(
            "request_review",
            caller=caller,
            job_brief=brief if isinstance(brief, dict) else None,
            auto_create_pr=False,
            merge_requested=bool(params.get("merge", False)),
        )

        if create_new:
            key = self.idempotency.require_key("request_review", params.get("idempotency_key"))
            cached = self.idempotency.get("request_review", key)
            if cached is not None:
                return cached

            target = validate_dispatch_target(
                self.config,
                repository=str(params["repository"]),
                environment=str(params["environment"]),
                head_branch=str(params["head_branch"]),
                model=str(params.get("model") or "composer-2"),
                base_branch=str(params["base_branch"]) if params.get("base_branch") else None,
            )
            prompt = str(
                params.get("prompt")
                or "Perform a structured code review. Do not merge. Emit a schema-valid handoff."
            )
            ph = hash_prompt(prompt)
            mapping = self._env_uuid_to_name()
            payload = build_create_payload(
                prompt=prompt,
                target=target,
                name=params.get("name") or "relay-request-review",
                auto_create_pr=False,
                ticket_path=params.get("ticket_path"),
                job_brief=brief if isinstance(brief, dict) else None,
                review_lane=True,
                uuid_to_name=mapping,
            )
            brief_auth = parse_job_brief_auth(brief if isinstance(brief, dict) else None)
            redacted_plan = redact_create_payload(payload)
            env_name = canonicalize_environment_name(target.environment, uuid_to_name=mapping)
            if brief_auth.dry_run:
                handoff = success_handoff_for_tool(
                    tool="request_review",
                    agent_id=None,
                    run_id=None,
                    branch=PENDING_BRANCH,
                    ticket_ids=_ticket_ids(params),
                    summary="Dry-run: review create plan validated (no POST /v1/agents)",
                    action_kind="request_review",
                    extra_observed={
                        "dry_run": True,
                        "mutating": False,
                        "merge": False,
                        "requested_head_branch": target.head_branch,
                        "actual_head_branch": None,
                        "environment": env_name,
                        "prompt_hash": ph,
                        "create_request_plan": redacted_plan,
                    },
                )
                self.idempotency.put("request_review", key, handoff)
                self.audit.emit(
                    tool="request_review",
                    caller_id=caller.caller_id,
                    decision="allow",
                    prompt_hash=ph,
                    idempotency_key=key,
                    extra={"dry_run": True},
                )
                return handoff

            self.quotas.check_create()
            ref = self.cursor.create_agent(payload)
            self.quotas.record_create(ref.agent_id)
            handoff = success_handoff_for_tool(
                tool="request_review",
                agent_id=ref.agent_id,
                run_id=ref.run_id,
                branch=PENDING_BRANCH,
                ticket_ids=_ticket_ids(params),
                summary=f"Review agent {ref.agent_id} started (no merge)",
                action_kind="request_review",
                extra_observed={
                    "prompt_hash": ph,
                    "merge": False,
                    "requested_head_branch": target.head_branch,
                    "actual_head_branch": None,
                    "environment": env_name,
                    "create_request_plan": redacted_plan,
                },
            )
            self.idempotency.put("request_review", key, handoff)
            self.audit.emit(
                tool="request_review",
                caller_id=caller.caller_id,
                decision="allow",
                agent_id=ref.agent_id,
                run_id=ref.run_id,
                prompt_hash=ph,
                usage={"spend_units": self.quotas.spend_per_create},
                idempotency_key=key,
            )
            return handoff

        # Follow-up review on existing agent
        agent_id = str(params["agent_id"])
        prompt = str(params.get("prompt") or "Request structured review; do not merge.")
        ph = hash_prompt(prompt)
        key = self.idempotency.require_key("request_review", params.get("idempotency_key"))
        cached = self.idempotency.get("request_review", key)
        if cached is not None:
            return cached
        self.quotas.check_create()
        ref = self.cursor.create_run(agent_id, {"prompt": {"text": prompt}})
        self.quotas.spend_units += self.quotas.spend_per_create
        handoff = success_handoff_for_tool(
            tool="request_review",
            agent_id=agent_id,
            run_id=ref.run_id,
            branch=str(params.get("head_branch") or "unknown"),
            ticket_ids=_ticket_ids(params),
            summary=f"Review follow-up {ref.run_id} (no merge)",
            action_kind="request_review",
            extra_observed={"prompt_hash": ph, "merge": False},
        )
        self.idempotency.put("request_review", key, handoff)
        self.audit.emit(
            tool="request_review",
            caller_id=caller.caller_id,
            decision="allow",
            agent_id=agent_id,
            run_id=ref.run_id,
            prompt_hash=ph,
            usage={"spend_units": self.quotas.spend_per_create},
            idempotency_key=key,
        )
        return handoff

    def _cancel(self, caller: AuthenticatedCaller, params: dict[str, Any]) -> dict[str, Any]:
        enforce_write_policy("cancel", caller=caller)
        agent_id = str(params["agent_id"])
        run_id = str(params["run_id"])
        result = self.cursor.cancel_run(agent_id, run_id)
        self.quotas.record_complete(agent_id)
        handoff = success_handoff_for_tool(
            tool="cancel",
            agent_id=agent_id,
            run_id=run_id,
            branch=str(params.get("head_branch") or "unknown"),
            ticket_ids=_ticket_ids(params),
            summary=f"Cancelled run {run_id} on agent {agent_id}",
            extra_observed={"cancel_status": result.get("status", "CANCELLED")},
        )
        self.audit.emit(
            tool="cancel",
            caller_id=caller.caller_id,
            decision="allow",
            agent_id=agent_id,
            run_id=run_id,
        )
        return handoff


def _ticket_ids(params: dict[str, Any]) -> list[str]:
    raw = params.get("ticket_ids") or params.get("ticket_id")
    if raw is None:
        path = params.get("ticket_path")
        if isinstance(path, str) and path:
            name = Path(path).stem
            return [name.split("-", 1)[0] if name else "CLOUD-02"]
        return ["CLOUD-02"]
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return [str(raw)]


def _pr_number(url: str | None) -> int:
    if not url:
        return 0
    try:
        return int(str(url).rstrip("/").split("/")[-1])
    except ValueError:
        return 0
