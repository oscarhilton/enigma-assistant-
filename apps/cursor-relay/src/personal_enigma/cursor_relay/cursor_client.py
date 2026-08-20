"""Cursor Cloud Agents API client (HTTP). Tests inject a mock — never live keys."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from personal_enigma.cursor_relay.create_contract import (
    extract_validation_fields,
    truncate_field,
)


@dataclass
class CursorAgentRef:
    agent_id: str
    run_id: str
    url: str | None = None
    status: str = "CREATING"
    raw: dict[str, Any] = field(default_factory=dict)


class CursorApiError(Exception):
    """Cursor API or mock lookup failure."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "cursor_api_error",
        validation: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.validation = validation or []


def _safe_http_error(exc: BaseException) -> CursorApiError:
    """Map httpx failures to CursorApiError without leaking secrets or bodies."""

    if isinstance(exc, httpx.TimeoutException):
        return CursorApiError("Cursor API request timed out", code="cursor_timeout")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code if exc.response is not None else "?"
        validation: list[dict[str, str]] = []
        if exc.response is not None and status == 400:
            try:
                body = exc.response.json()
            except (json.JSONDecodeError, ValueError):
                body = None
            if body is not None:
                validation = extract_validation_fields(body)
            msg = "Cursor API HTTP 400"
            if validation:
                # Compact allowlisted summary only
                bits = []
                for item in validation[:5]:
                    parts = [
                        f"{k}={truncate_field(v, limit=80)}" for k, v in sorted(item.items())
                    ]
                    bits.append("{" + ", ".join(parts) + "}")
                msg = f"Cursor API HTTP 400 validation: {'; '.join(bits)}"
            return CursorApiError(msg, code="cursor_validation_error", validation=validation)
        return CursorApiError(
            f"Cursor API HTTP {status}",
            code="cursor_http_error",
        )
    if isinstance(exc, httpx.HTTPError):
        return CursorApiError("Cursor API transport error", code="cursor_transport_error")
    return CursorApiError("Cursor API failure", code="cursor_api_error")


class CursorClient(Protocol):
    def create_agent(self, payload: dict[str, Any]) -> CursorAgentRef: ...

    def get_agent(self, agent_id: str) -> dict[str, Any]: ...

    def get_run(self, agent_id: str, run_id: str) -> dict[str, Any]: ...

    def create_run(self, agent_id: str, payload: dict[str, Any]) -> CursorAgentRef: ...

    def cancel_run(self, agent_id: str, run_id: str) -> dict[str, Any]: ...


class HttpCursorClient:
    """Thin wrapper around Cloud Agents API v1 (same surface as ``@cursor/sdk``)."""

    def __init__(self, *, api_key: str, base_url: str = "https://api.cursor.com") -> None:
        if not api_key:
            msg = "CURSOR_API_KEY is required for HttpCursorClient"
            raise ValueError(msg)
        self._api_key = api_key
        self._base = base_url.rstrip("/")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base,
            auth=(self._api_key, ""),
            headers={"Content-Type": "application/json"},
            timeout=60.0,
        )

    def create_agent(self, payload: dict[str, Any]) -> CursorAgentRef:
        try:
            with self._client() as client:
                resp = client.post("/v1/agents", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise _safe_http_error(exc) from None
        agent = data["agent"]
        run = data["run"]
        return CursorAgentRef(
            agent_id=agent["id"],
            run_id=run["id"],
            url=agent.get("url"),
            status=run.get("status", "CREATING"),
            raw=data,
        )

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        try:
            with self._client() as client:
                resp = client.get(f"/v1/agents/{agent_id}")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise _safe_http_error(exc) from None

    def get_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        try:
            with self._client() as client:
                resp = client.get(f"/v1/agents/{agent_id}/runs/{run_id}")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise _safe_http_error(exc) from None

    def create_run(self, agent_id: str, payload: dict[str, Any]) -> CursorAgentRef:
        try:
            with self._client() as client:
                resp = client.post(f"/v1/agents/{agent_id}/runs", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise _safe_http_error(exc) from None
        run = data.get("run", data)
        return CursorAgentRef(
            agent_id=agent_id,
            run_id=run["id"],
            status=run.get("status", "CREATING"),
            raw=data,
        )

    def cancel_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        try:
            with self._client() as client:
                resp = client.post(f"/v1/agents/{agent_id}/runs/{run_id}/cancel")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise _safe_http_error(exc) from None


class MockCursorClient:
    """In-memory Cursor API for unit/smoke tests — no network, no secrets."""

    def __init__(self) -> None:
        self.agents: dict[str, dict[str, Any]] = {}
        self.runs: dict[str, dict[str, Any]] = {}
        self.create_calls: list[dict[str, Any]] = []
        self.run_calls: list[dict[str, Any]] = []
        self.cancel_calls: list[tuple[str, str]] = []
        self._seq = 0
        self.fail_next: str | None = None
        self.fail_validation: list[dict[str, str]] | None = None

    def _maybe_fail(self) -> None:
        mode = self.fail_next
        self.fail_next = None
        if mode == "timeout":
            raise CursorApiError("Cursor API request timed out", code="cursor_timeout")
        if mode == "http_503":
            raise CursorApiError("Cursor API HTTP 503", code="cursor_http_error")
        if mode == "transport":
            raise CursorApiError("Cursor API transport error", code="cursor_transport_error")
        if mode == "http_400":
            validation = self.fail_validation or [
                {"code": "invalid_argument", "message": "bad env", "field": "env.name"}
            ]
            self.fail_validation = None
            raise CursorApiError(
                "Cursor API HTTP 400 validation: "
                + str({k: v for item in validation for k, v in item.items()}),
                code="cursor_validation_error",
                validation=validation,
            )

    def _next_ids(self) -> tuple[str, str]:
        self._seq += 1
        return f"bc-mock-{self._seq:04d}", f"run-mock-{self._seq:04d}"

    def create_agent(self, payload: dict[str, Any]) -> CursorAgentRef:
        self._maybe_fail()
        self.create_calls.append(payload)
        agent_id, run_id = self._next_ids()
        agent = {
            "id": agent_id,
            "name": payload.get("name") or "mock-agent",
            "status": "ACTIVE",
            "url": f"https://cursor.com/agents/{agent_id}",
            "latestRunId": run_id,
            "repos": payload.get("repos", []),
            "env": payload.get("env"),
        }
        run = {
            "id": run_id,
            "agentId": agent_id,
            "status": "CREATING",
            # Cursor-generated head — not the caller's requested branch.
            "git": {"branches": [{"branch": f"cursor/auto-{self._seq:04d}"}]},
        }
        self.agents[agent_id] = agent
        self.runs[run_id] = run
        return CursorAgentRef(
            agent_id=agent_id,
            run_id=run_id,
            url=agent["url"],
            status="CREATING",
            raw={"agent": agent, "run": run},
        )

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        self._maybe_fail()
        if agent_id not in self.agents:
            raise CursorApiError(f"Unknown agent_id: {agent_id}", code="agent_not_found")
        return self.agents[agent_id]

    def get_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        self._maybe_fail()
        if run_id not in self.runs:
            raise CursorApiError(f"Unknown run_id: {run_id}", code="run_not_found")
        run = dict(self.runs[run_id])
        run["agentId"] = agent_id
        return run

    def create_run(self, agent_id: str, payload: dict[str, Any]) -> CursorAgentRef:
        self._maybe_fail()
        self.run_calls.append({"agent_id": agent_id, **payload})
        _, run_id = self._next_ids()
        run = {"id": run_id, "agentId": agent_id, "status": "CREATING"}
        self.runs[run_id] = run
        if agent_id in self.agents:
            self.agents[agent_id]["latestRunId"] = run_id
        return CursorAgentRef(agent_id=agent_id, run_id=run_id, status="CREATING", raw={"run": run})

    def cancel_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        self._maybe_fail()
        self.cancel_calls.append((agent_id, run_id))
        run = self.runs.get(run_id, {"id": run_id, "agentId": agent_id})
        run["status"] = "CANCELLED"
        self.runs[run_id] = run
        return run
