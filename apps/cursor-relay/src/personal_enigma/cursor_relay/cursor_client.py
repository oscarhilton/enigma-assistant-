"""Cursor Cloud Agents API client (HTTP). Tests inject a mock — never live keys."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


@dataclass
class CursorAgentRef:
    agent_id: str
    run_id: str
    url: str | None = None
    status: str = "CREATING"
    raw: dict[str, Any] = field(default_factory=dict)


class CursorApiError(Exception):
    """Cursor API or mock lookup failure."""

    def __init__(self, message: str, *, code: str = "cursor_api_error") -> None:
        super().__init__(message)
        self.code = code


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
        if api_key.startswith("sk-") and "test" in api_key:
            # still ok — just ensure we never log it
            pass
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
        with self._client() as client:
            resp = client.post("/v1/agents", json=payload)
            resp.raise_for_status()
            data = resp.json()
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
        with self._client() as client:
            resp = client.get(f"/v1/agents/{agent_id}")
            resp.raise_for_status()
            return resp.json()

    def get_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        with self._client() as client:
            resp = client.get(f"/v1/agents/{agent_id}/runs/{run_id}")
            resp.raise_for_status()
            return resp.json()

    def create_run(self, agent_id: str, payload: dict[str, Any]) -> CursorAgentRef:
        with self._client() as client:
            resp = client.post(f"/v1/agents/{agent_id}/runs", json=payload)
            resp.raise_for_status()
            data = resp.json()
        run = data.get("run", data)
        return CursorAgentRef(
            agent_id=agent_id,
            run_id=run["id"],
            status=run.get("status", "CREATING"),
            raw=data,
        )

    def cancel_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        with self._client() as client:
            resp = client.post(f"/v1/agents/{agent_id}/runs/{run_id}/cancel")
            resp.raise_for_status()
            return resp.json()


class MockCursorClient:
    """In-memory Cursor API for unit/smoke tests — no network, no secrets."""

    def __init__(self) -> None:
        self.agents: dict[str, dict[str, Any]] = {}
        self.runs: dict[str, dict[str, Any]] = {}
        self.create_calls: list[dict[str, Any]] = []
        self.run_calls: list[dict[str, Any]] = []
        self.cancel_calls: list[tuple[str, str]] = []
        self._seq = 0

    def _next_ids(self) -> tuple[str, str]:
        self._seq += 1
        return f"bc-mock-{self._seq:04d}", f"run-mock-{self._seq:04d}"

    def create_agent(self, payload: dict[str, Any]) -> CursorAgentRef:
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
        if agent_id not in self.agents:
            raise CursorApiError(f"Unknown agent_id: {agent_id}", code="agent_not_found")
        return self.agents[agent_id]

    def get_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        if run_id not in self.runs:
            raise CursorApiError(f"Unknown run_id: {run_id}", code="run_not_found")
        run = dict(self.runs[run_id])
        run["agentId"] = agent_id
        return run

    def create_run(self, agent_id: str, payload: dict[str, Any]) -> CursorAgentRef:
        self.run_calls.append({"agent_id": agent_id, **payload})
        _, run_id = self._next_ids()
        run = {"id": run_id, "agentId": agent_id, "status": "CREATING"}
        self.runs[run_id] = run
        if agent_id in self.agents:
            self.agents[agent_id]["latestRunId"] = run_id
        return CursorAgentRef(agent_id=agent_id, run_id=run_id, status="CREATING", raw={"run": run})

    def cancel_run(self, agent_id: str, run_id: str) -> dict[str, Any]:
        self.cancel_calls.append((agent_id, run_id))
        run = self.runs.get(run_id, {"id": run_id, "agentId": agent_id})
        run["status"] = "CANCELLED"
        self.runs[run_id] = run
        return run
