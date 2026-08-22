"""Due-check orchestration for retained-assertion maintenance (RECON-05D).

Last-run timestamps are caller-supplied. They must not be persisted through
``ENIGMA_DATABASE_URL`` / the ingest Alembic store. A process supervisor or
in-process loop invokes ``run_due_retention_maintenance``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from personal_enigma.api.storage.keychain import KeychainBackend
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.worker.retention.jobs import (
    TTL_EXPIRY_JOB,
    RetentionTtlExpiryResult,
    run_retained_assertion_ttl_expiry,
)

DEFAULT_TTL_INTERVAL = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class RetentionJobSpec:
    """Named maintenance job and how often it may run."""

    name: str
    interval: timedelta


@dataclass(frozen=True, slots=True)
class RetentionMaintenanceResult:
    """Which scheduled jobs ran. Summaries are ids-only."""

    ran: tuple[str, ...]
    skipped: tuple[str, ...]
    ttl: RetentionTtlExpiryResult | None


def default_retention_job_specs() -> tuple[RetentionJobSpec, ...]:
    """TTL expiry is the only scheduled retained-assertion job.

    Explicit forget is on-demand orchestration, not an interval sweep.
    """
    return (RetentionJobSpec(name=TTL_EXPIRY_JOB, interval=DEFAULT_TTL_INTERVAL),)


def retention_job_is_due(
    spec: RetentionJobSpec,
    last_run_at: datetime | None,
    *,
    now: datetime,
) -> bool:
    if last_run_at is None:
        return True
    return now >= last_run_at + spec.interval


def run_due_retention_maintenance(
    *,
    root: Path | None = None,
    now: datetime | None = None,
    last_runs: Mapping[str, datetime] | None = None,
    force: bool = False,
    keychain: KeychainBackend | None = None,
    vault: PrivateVault | None = None,
    specs: Sequence[RetentionJobSpec] | None = None,
) -> RetentionMaintenanceResult:
    """Run due retained-assertion jobs against PrivateVault.

    Unknown spec names are skipped so this orchestrator cannot grow a second
    forget graph or a SEC-06 blob-GC side channel.
    """
    current = now or datetime.now(tz=UTC)
    runs = last_runs or {}
    selected = tuple(specs) if specs is not None else default_retention_job_specs()
    ran: list[str] = []
    skipped: list[str] = []
    ttl: RetentionTtlExpiryResult | None = None

    for spec in selected:
        if spec.name != TTL_EXPIRY_JOB:
            skipped.append(spec.name)
            continue
        if not force and not retention_job_is_due(spec, runs.get(spec.name), now=current):
            skipped.append(spec.name)
            continue
        ttl = run_retained_assertion_ttl_expiry(
            root=root,
            now=current,
            keychain=keychain,
            vault=vault,
        )
        ran.append(spec.name)

    return RetentionMaintenanceResult(ran=tuple(ran), skipped=tuple(skipped), ttl=ttl)
