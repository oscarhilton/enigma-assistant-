"""RECON-05D — worker scheduling for retained-assertion TTL / forget.

Calls canonical vault APIs. Does not reimplement RECON-05B cascade semantics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.api.storage.retention_vault import VaultDurableAssertionStore
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention import DerivedRecordType, RetentionPurpose
from personal_enigma.domain.retention_gate import RetentionOutcome, evaluate_retention
from personal_enigma.worker.main import main, worker_status
from personal_enigma.worker.retention import (
    DEFAULT_TTL_INTERVAL,
    TTL_EXPIRY_JOB,
    RetentionJobSpec,
    default_retention_job_specs,
    open_retention_vault,
    retention_job_is_due,
    run_due_retention_maintenance,
    run_retained_assertion_forget,
    run_retained_assertion_ttl_expiry,
)
from personal_enigma.worker.storage import open_worker_store


def _assertion(**overrides: object) -> GroundedAssertion:
    base: dict[str, object] = {
        "id": "A-ceramics",
        "kind": AssertionKind.PREFERENCE,
        "subject": "PERSON_Maya",
        "predicate": "likes",
        "value": "ceramics",
        "epistemic_status": EpistemicStatus.USER_CONFIRMED,
        "purpose_tags": ["user_explicit_recall"],
        "evidence_refs": ["EV_CHAT_1"],
    }
    base.update(overrides)
    return GroundedAssertion.model_validate(base)


@pytest.fixture
def memory_keychain(monkeypatch: pytest.MonkeyPatch):
    from personal_enigma.api.storage.keychain import MemoryKeychain

    monkeypatch.setenv("ENIGMA_KEYCHAIN_BACKEND", "memory")
    chain = MemoryKeychain()
    yield chain
    chain.clear()


@pytest.fixture
def vault_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    return root


@pytest.fixture
def operational_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "operational" / "private.db"
    monkeypatch.setenv("ENIGMA_DATABASE_URL", f"sqlite:///{path}")
    return path


def test_worker_status_unchanged() -> None:
    assert worker_status() == {"status": "idle", "service": "enigma-worker"}


def test_default_schedule_is_ttl_only() -> None:
    specs = default_retention_job_specs()
    assert len(specs) == 1
    assert specs[0].name == TTL_EXPIRY_JOB
    assert specs[0].interval == DEFAULT_TTL_INTERVAL


def test_ttl_job_is_due_when_never_run() -> None:
    spec = RetentionJobSpec(name=TTL_EXPIRY_JOB, interval=DEFAULT_TTL_INTERVAL)
    now = datetime(2026, 8, 22, tzinfo=UTC)
    assert retention_job_is_due(spec, None, now=now)


def test_ttl_job_not_due_inside_interval() -> None:
    spec = RetentionJobSpec(name=TTL_EXPIRY_JOB, interval=DEFAULT_TTL_INTERVAL)
    now = datetime(2026, 8, 22, 12, tzinfo=UTC)
    last = now - timedelta(minutes=10)
    assert not retention_job_is_due(spec, last, now=now)
    assert retention_job_is_due(spec, last, now=now + DEFAULT_TTL_INTERVAL)


def test_open_retention_vault_is_private_vault(
    vault_root: Path, memory_keychain
) -> None:
    with open_retention_vault(root=vault_root, keychain=memory_keychain) as vault:
        assert isinstance(vault, PrivateVault)
        assert vault.paths.root == vault_root


def test_ttl_expiry_job_delegates_to_canonical_expire_ttl(
    vault_root: Path, memory_keychain, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: dict[str, object] = {}

    def fake_expire(self: VaultDurableAssertionStore, *, now: datetime | None = None):
        called["store"] = self
        called["now"] = now
        return []

    monkeypatch.setattr(VaultDurableAssertionStore, "expire_ttl", fake_expire)
    now = datetime(2026, 6, 1, tzinfo=UTC)
    result = run_retained_assertion_ttl_expiry(
        root=vault_root, now=now, keychain=memory_keychain
    )
    assert called["now"] == now
    assert isinstance(called["store"], VaultDurableAssertionStore)
    assert result.expired_count == 0
    assert result.vault_root == str(vault_root)


def test_forget_job_delegates_to_canonical_forget(
    vault_root: Path, memory_keychain, monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_enigma.domain.retention_gate import ForgetCascadeResult

    called: dict[str, object] = {}

    def fake_forget(self: VaultDurableAssertionStore, assertion_id: str):
        called["id"] = assertion_id
        return ForgetCascadeResult(
            root_assertion_id=assertion_id,
            deleted_assertion_ids=[assertion_id],
            trigger="forget",
        )

    monkeypatch.setattr(VaultDurableAssertionStore, "forget", fake_forget)
    result = run_retained_assertion_forget(
        "maya-pref", root=vault_root, keychain=memory_keychain
    )
    assert called["id"] == "maya-pref"
    assert result.root_assertion_id == "maya-pref"
    assert result.trigger == "forget"
    assert result.deleted_assertion_ids == ("maya-pref",)


def test_ttl_job_expires_elapsed_assertion_and_exclusive_derivative(
    vault_root: Path, memory_keychain, operational_db: Path
) -> None:
    from personal_enigma.api.storage.retention_vault import assertion_lineage_ref

    expired_at = datetime(2026, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 3, tzinfo=UTC)
    availability = _assertion(
        id="restaurant-avail",
        kind=AssertionKind.FACT,
        subject="self",
        predicate="plans_to",
        value="dine at Bistro Saturday 7pm",
        purpose_tags=["temporary_case"],
        validity_kind=AssertionValidityKind.TTL,
        temporal_scope="dinner_planning",
        valid_until=expired_at,
        evidence_refs=["EV_BOOKING_1"],
    )
    decision = evaluate_retention(availability)
    assert decision.outcome == RetentionOutcome.TTL

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(availability, decision)
        vault.store_derived_new(
            record_id="dinner-rec",
            record_type=DerivedRecordType.FEATURE,
            payload={"recommendation": "book_bistro_saturday"},
            derived_from=[assertion_lineage_ref("restaurant-avail")],
            purpose=RetentionPurpose.TEMPORARY_CASE,
        )

    result = run_retained_assertion_ttl_expiry(
        root=vault_root, now=now, keychain=memory_keychain
    )
    assert result.expired_count == 1
    assert "restaurant-avail" in result.forgotten_assertion_ids
    assert "dinner-rec" in result.deleted_derived_ids
    assert result.triggers == ("ttl_expiry",)

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        assert store.list_retained_ids() == []
        assert vault.get_derived_record("dinner-rec") is None

    assert not operational_db.exists()


def test_ttl_job_does_not_sweep_unexpired(
    vault_root: Path, memory_keychain
) -> None:
    future = datetime(2026, 12, 1, tzinfo=UTC)
    availability = _assertion(
        id="restaurant-future",
        kind=AssertionKind.FACT,
        subject="self",
        predicate="plans_to",
        value="dine at Bistro in December",
        purpose_tags=["temporary_case"],
        validity_kind=AssertionValidityKind.TTL,
        valid_until=future,
    )
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(availability, evaluate_retention(availability))

    result = run_retained_assertion_ttl_expiry(
        root=vault_root,
        now=datetime(2026, 6, 1, tzinfo=UTC),
        keychain=memory_keychain,
    )
    assert result.expired_count == 0
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        assert VaultDurableAssertionStore(vault).list_retained_ids() == [
            "restaurant-future"
        ]


def test_forget_job_removes_retained_assertion(
    vault_root: Path, memory_keychain
) -> None:
    assertion = _assertion(id="maya-pref")
    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))

    result = run_retained_assertion_forget(
        "maya-pref", root=vault_root, keychain=memory_keychain
    )
    assert result.root_assertion_id == "maya-pref"
    assert "maya-pref" in result.deleted_assertion_ids
    assert result.trigger == "forget"

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        assert VaultDurableAssertionStore(vault).list_retained_ids() == []


def test_due_maintenance_runs_ttl_when_due(
    vault_root: Path, memory_keychain
) -> None:
    now = datetime(2026, 8, 22, tzinfo=UTC)
    result = run_due_retention_maintenance(
        root=vault_root,
        now=now,
        last_runs={},
        keychain=memory_keychain,
    )
    assert result.ran == (TTL_EXPIRY_JOB,)
    assert result.skipped == ()
    assert result.ttl is not None
    assert result.ttl.expired_count == 0


def test_due_maintenance_skips_when_not_due(
    vault_root: Path, memory_keychain, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = {"ttl": 0}

    def boom(**kwargs: object) -> None:
        called["ttl"] += 1
        raise AssertionError("TTL job must not run when not due")

    monkeypatch.setattr(
        "personal_enigma.worker.retention.schedule.run_retained_assertion_ttl_expiry",
        boom,
    )
    now = datetime(2026, 8, 22, 12, tzinfo=UTC)
    result = run_due_retention_maintenance(
        root=vault_root,
        now=now,
        last_runs={TTL_EXPIRY_JOB: now - timedelta(minutes=5)},
        keychain=memory_keychain,
    )
    assert result.ran == ()
    assert result.skipped == (TTL_EXPIRY_JOB,)
    assert result.ttl is None
    assert called["ttl"] == 0


def test_due_maintenance_skips_unknown_job_names(
    vault_root: Path, memory_keychain
) -> None:
    result = run_due_retention_maintenance(
        root=vault_root,
        now=datetime(2026, 8, 22, tzinfo=UTC),
        keychain=memory_keychain,
        specs=(
            RetentionJobSpec(name="sec06.blob_gc", interval=DEFAULT_TTL_INTERVAL),
            RetentionJobSpec(name=TTL_EXPIRY_JOB, interval=DEFAULT_TTL_INTERVAL),
        ),
    )
    assert result.skipped == ("sec06.blob_gc",)
    assert result.ran == (TTL_EXPIRY_JOB,)
    assert result.ttl is not None


def test_ttl_job_does_not_open_operational_store(
    vault_root: Path,
    memory_keychain,
    operational_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("retention maintenance must not open_worker_store")

    monkeypatch.setattr(
        "personal_enigma.worker.storage.open_worker_store", forbidden
    )
    run_retained_assertion_ttl_expiry(
        root=vault_root,
        now=datetime(2026, 6, 1, tzinfo=UTC),
        keychain=memory_keychain,
    )
    assert not operational_db.exists()
    # Operational helper still works when a caller actually wants it.
    assert open_worker_store is not None


def test_main_retention_ttl_dispatches(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from personal_enigma.worker.retention.jobs import RetentionTtlExpiryResult

    called = {"n": 0}

    def fake() -> RetentionTtlExpiryResult:
        called["n"] += 1
        return RetentionTtlExpiryResult(
            expired_count=2,
            forgotten_assertion_ids=("a1",),
            deleted_derived_ids=(),
            audit_ids=(),
            triggers=("ttl_expiry",),
            vault_root="/tmp/private",
        )

    monkeypatch.setattr(
        "personal_enigma.worker.retention.run_retained_assertion_ttl_expiry",
        fake,
    )
    main(["retention-ttl"])
    out = capsys.readouterr().out
    assert called["n"] == 1
    assert "retained_assertion.ttl_expiry" in out
    assert "expired=2" in out
    assert "ceramics" not in out


def test_main_retention_forget_dispatches(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from personal_enigma.worker.retention.jobs import RetentionForgetResult

    called: dict[str, str] = {}

    def fake(assertion_id: str) -> RetentionForgetResult:
        called["id"] = assertion_id
        return RetentionForgetResult(
            root_assertion_id=assertion_id,
            deleted_assertion_ids=(assertion_id,),
            deleted_derived_ids=(),
            audit_id="audit-1",
            trigger="forget",
            vault_root="/tmp/private",
        )

    monkeypatch.setattr(
        "personal_enigma.worker.retention.run_retained_assertion_forget",
        fake,
    )
    main(["retention-forget", "maya-pref"])
    out = capsys.readouterr().out
    assert called["id"] == "maya-pref"
    assert "retained_assertion.forget" in out
    assert "maya-pref" in out
    assert "ceramics" not in out


def test_main_retention_forget_without_id_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("forget must not run without an assertion id")

    monkeypatch.setattr(
        "personal_enigma.worker.retention.run_retained_assertion_forget",
        boom,
    )
    with pytest.raises(SystemExit) as exited:
        main(["retention-forget"])
    assert exited.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err
    assert "retention-forget" in captured.err
    assert captured.err.count("idle") == 0


def test_main_retention_forget_blank_id_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["retention-forget", "   "])
    assert exited.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_main_default_still_idle(capsys: pytest.CaptureFixture[str]) -> None:
    main([])
    assert capsys.readouterr().out.strip() == "enigma-worker: idle"
