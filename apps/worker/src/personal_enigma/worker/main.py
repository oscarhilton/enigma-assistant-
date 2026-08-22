"""Worker entrypoint (scaffold — jobs arrive in later tickets)."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def worker_status() -> dict[str, str]:
    return {"status": "idle", "service": "enigma-worker"}


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["retention-ttl"]:
        from personal_enigma.worker.retention import run_retained_assertion_ttl_expiry

        result = run_retained_assertion_ttl_expiry()
        print(  # noqa: T201
            "enigma-worker: retained_assertion.ttl_expiry "
            f"expired={result.expired_count}"
        )
        return
    if args[:1] == ["retention-forget"] and len(args) >= 2:
        from personal_enigma.worker.retention import run_retained_assertion_forget

        result = run_retained_assertion_forget(args[1])
        print(  # noqa: T201
            f"enigma-worker: retained_assertion.forget root={result.root_assertion_id}"
        )
        return
    status = worker_status()
    print(f"enigma-worker: {status['status']}")  # noqa: T201
