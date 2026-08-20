"""Relay-side audit log (caller, agent, run, prompt hash, usage)."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def hash_prompt(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class AuditLog:
    path: Path | None = None
    records: list[dict[str, Any]] = field(default_factory=list)

    def emit(
        self,
        *,
        tool: str,
        caller_id: str,
        decision: str,
        agent_id: str | None = None,
        run_id: str | None = None,
        prompt_hash: str | None = None,
        usage: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "ts": time.time(),
            "tool": tool,
            "caller_id": caller_id,
            "decision": decision,
            "agent_id": agent_id,
            "run_id": run_id,
            "prompt_hash": prompt_hash,
            "usage": usage or {},
            "idempotency_key": idempotency_key,
            "detail": detail,
        }
        if extra:
            record.update(extra)
        # Never persist secrets
        for banned in ("cursor_api_key", "authorization", "token", "api_key"):
            record.pop(banned, None)
        self.records.append(record)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
        return record
