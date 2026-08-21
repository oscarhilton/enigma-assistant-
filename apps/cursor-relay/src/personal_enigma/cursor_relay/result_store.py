"""In-memory cache of terminal run report-back snapshots (CLOUD-04).

Process-local by default — same single-instance constraint as idempotency/quota stores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TERMINAL_RUN_STATUSES = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})


@dataclass(frozen=True)
class TerminalRunSnapshot:
    """Normalized terminal handoff fields for a finished cloud-agent run."""

    agent_id: str
    run_id: str
    run_status: str
    final_result: str | None
    duration_ms: int | None
    git_branches: list[str]
    pr_urls: list[str]
    result_source: str  # cache | stream | get_run
    stream_error: dict[str, str] | None = None
    raw_git: list[dict[str, Any]] = field(default_factory=list)

    def cache_key(self) -> str:
        return f"{self.agent_id}:{self.run_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "run_status": self.run_status,
            "final_result": self.final_result,
            "duration_ms": self.duration_ms,
            "git_branches": list(self.git_branches),
            "pr_urls": list(self.pr_urls),
            "result_source": self.result_source,
            "stream_error": dict(self.stream_error) if self.stream_error else None,
            "raw_git": list(self.raw_git),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TerminalRunSnapshot:
        return cls(
            agent_id=str(data["agent_id"]),
            run_id=str(data["run_id"]),
            run_status=str(data["run_status"]),
            final_result=data.get("final_result"),
            duration_ms=data.get("duration_ms"),
            git_branches=[str(b) for b in data.get("git_branches") or []],
            pr_urls=[str(u) for u in data.get("pr_urls") or []],
            result_source=str(data.get("result_source") or "cache"),
            stream_error=data.get("stream_error"),
            raw_git=list(data.get("raw_git") or []),
        )


class ResultStore:
    """Cache terminal run snapshots keyed by ``agent_id:run_id``."""

    def __init__(self) -> None:
        self._entries: dict[str, TerminalRunSnapshot] = {}

    def get(self, agent_id: str, run_id: str) -> TerminalRunSnapshot | None:
        return self._entries.get(f"{agent_id}:{run_id}")

    def put(self, snapshot: TerminalRunSnapshot) -> None:
        if snapshot.run_status not in TERMINAL_RUN_STATUSES:
            msg = f"Refusing to cache non-terminal run status: {snapshot.run_status}"
            raise ValueError(msg)
        self._entries[snapshot.cache_key()] = snapshot

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {k: v.to_dict() for k, v in self._entries.items()}
