"""Worker entrypoint (scaffold — jobs arrive in later tickets)."""

from __future__ import annotations


def worker_status() -> dict[str, str]:
    return {"status": "idle", "service": "enigma-worker"}


def main() -> None:
    status = worker_status()
    print(f"enigma-worker: {status['status']}")  # noqa: T201
