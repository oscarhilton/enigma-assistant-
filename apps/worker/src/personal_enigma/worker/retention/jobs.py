"""Retained-assertion TTL / forget jobs (RECON-05D).

Donor C29/C15 ``run_retention_gc`` called ``PrivateVault.run_gc()`` (SEC-06
raw-blob / resolved-obligation sweep). That API is already on main via
RECON-04 and is not re-scheduled here.

This module only orchestrates RECON-05B vault APIs:

    PrivateVault → VaultDurableAssertionStore.expire_ttl | .forget

It never opens the ingest/Alembic operational store and must not read
``ENIGMA_DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from personal_enigma.api.storage.keychain import KeychainBackend
from personal_enigma.api.storage.retention_vault import VaultDurableAssertionStore
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.retention_gate import ForgetCascadeResult

TTL_EXPIRY_JOB = "retained_assertion.ttl_expiry"
FORGET_JOB = "retained_assertion.forget"


@dataclass(frozen=True, slots=True)
class RetentionTtlExpiryResult:
    """Ids-only summary of a TTL expiry sweep."""

    expired_count: int
    forgotten_assertion_ids: tuple[str, ...]
    deleted_derived_ids: tuple[str, ...]
    audit_ids: tuple[str, ...]
    triggers: tuple[str, ...]
    vault_root: str


@dataclass(frozen=True, slots=True)
class RetentionForgetResult:
    """Ids-only summary of an explicit retained-assertion forget."""

    root_assertion_id: str
    deleted_assertion_ids: tuple[str, ...]
    deleted_derived_ids: tuple[str, ...]
    audit_id: str | None
    trigger: str
    vault_root: str


def open_retention_vault(
    *,
    root: Path | None = None,
    keychain: KeychainBackend | None = None,
) -> PrivateVault:
    """Open PrivateVault for retention maintenance.

    Intentionally ignores ``ENIGMA_DATABASE_URL`` / ``open_worker_store``.
    """
    return PrivateVault.open(root=root, keychain=keychain)


@contextmanager
def _bound_vault(
    *,
    root: Path | None,
    keychain: KeychainBackend | None,
    vault: PrivateVault | None,
) -> Iterator[PrivateVault]:
    if vault is not None:
        yield vault
        return
    opened = open_retention_vault(root=root, keychain=keychain)
    try:
        yield opened
    finally:
        opened.close()


def _unique(ids: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(ids))


def _summarize_ttl(
    results: list[ForgetCascadeResult],
    *,
    vault_root: str,
) -> RetentionTtlExpiryResult:
    forgotten: list[str] = []
    derived: list[str] = []
    audits: list[str] = []
    triggers: list[str] = []
    for result in results:
        forgotten.extend(result.deleted_assertion_ids)
        derived.extend(result.deleted_derived_ids)
        if result.audit_id:
            audits.append(result.audit_id)
        triggers.append(result.trigger)
    return RetentionTtlExpiryResult(
        expired_count=len(results),
        forgotten_assertion_ids=_unique(forgotten),
        deleted_derived_ids=_unique(derived),
        audit_ids=tuple(audits),
        triggers=tuple(triggers),
        vault_root=vault_root,
    )


def run_retained_assertion_ttl_expiry(
    *,
    root: Path | None = None,
    now: datetime | None = None,
    keychain: KeychainBackend | None = None,
    vault: PrivateVault | None = None,
) -> RetentionTtlExpiryResult:
    """Sweep elapsed TTL retained assertions via the canonical vault API."""
    with _bound_vault(root=root, keychain=keychain, vault=vault) as bound:
        store = VaultDurableAssertionStore(bound)
        results = store.expire_ttl(now=now)
        return _summarize_ttl(results, vault_root=str(bound.paths.root))


def run_retained_assertion_forget(
    assertion_id: str,
    *,
    root: Path | None = None,
    keychain: KeychainBackend | None = None,
    vault: PrivateVault | None = None,
) -> RetentionForgetResult:
    """Forget one retained assertion via the canonical vault API."""
    with _bound_vault(root=root, keychain=keychain, vault=vault) as bound:
        store = VaultDurableAssertionStore(bound)
        result = store.forget(assertion_id)
        return RetentionForgetResult(
            root_assertion_id=result.root_assertion_id,
            deleted_assertion_ids=tuple(result.deleted_assertion_ids),
            deleted_derived_ids=tuple(result.deleted_derived_ids),
            audit_id=result.audit_id,
            trigger=result.trigger,
            vault_root=str(bound.paths.root),
        )
