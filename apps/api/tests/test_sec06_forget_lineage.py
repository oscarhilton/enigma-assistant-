"""SEC-06 — retention lineage, forget graph, decay, and GC tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.api.storage.crypto import generate_key
from personal_enigma.api.storage.decay import compress_payload_to_shadow
from personal_enigma.api.storage.forget import resolve_forget_plan
from personal_enigma.api.storage.sensitive import (
    SensitiveInferenceError,
    assert_durable_write_allowed,
    classify_sensitive_inference,
)
from personal_enigma.api.storage.vault import (
    PrivateVault,
    copy_vault_directory,
    search_directory_for_plaintext,
)
from personal_enigma.domain.retention import (
    DerivedRecordType,
    MemoryLayer,
    RetentionClass,
    RetentionPurpose,
    SensitiveInferenceClass,
)

EMAIL_A = "EMAIL_A"
EMAIL_B = "EMAIL_B"
FACT_X = "FACT_X"
RELATION_Y = "RELATION_Y"
EMBED_A = "EMBED_A"
SUMMARY_A = "SUMMARY_A"

SENTINEL_BODY_A = "SENTINEL_BODY_EMAIL_A_ULTRA_SECRET"
SENTINEL_BODY_B = "SENTINEL_BODY_EMAIL_B_ULTRA_SECRET"


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


def _seed_email_ab_scenario(vault: PrivateVault) -> dict[str, str]:
    """Centrepiece lineage fixture: EMAIL_A/B, FACT_X, RELATION_Y."""
    rec_a = vault.store_raw_source(
        source="gmail",
        external_id="msg-a",
        raw_content=SENTINEL_BODY_A.encode("utf-8"),
        record_id=EMAIL_A,
    )
    vault.store_raw_source(
        source="gmail",
        external_id="msg-b",
        raw_content=SENTINEL_BODY_B.encode("utf-8"),
        record_id=EMAIL_B,
    )
    vault.store_derived_new(
        record_id=FACT_X,
        record_type=DerivedRecordType.FACT,
        payload={"label": "shared_fact", "subject": "project deadline"},
        derived_from=[EMAIL_A, EMAIL_B],
        purpose=RetentionPurpose.OPEN_LOOP_TRACKING,
    )
    vault.store_derived_new(
        record_id=RELATION_Y,
        record_type=DerivedRecordType.RELATION,
        payload={"from": "PERSON_A", "to": "PROJECT_R9", "kind": "blocks"},
        derived_from=[EMAIL_A],
        purpose=RetentionPurpose.RELATION_INFERENCE,
    )
    vault.store_derived_new(
        record_id=EMBED_A,
        record_type=DerivedRecordType.EMBEDDING,
        payload={"dims": 384, "model": "local"},
        derived_from=[EMAIL_A],
        purpose=RetentionPurpose.RETRIEVAL_INDEX,
        retention_class=RetentionClass.EXPIRE_WITH_SOURCE,
    )
    vault.store_derived_new(
        record_id=SUMMARY_A,
        record_type=DerivedRecordType.SUMMARY,
        payload={"tokens": 42},
        derived_from=[EMAIL_A],
        purpose=RetentionPurpose.ATTENTION_RANKING,
        retention_class=RetentionClass.EXPIRE_WITH_SOURCE,
    )
    return {"blob_a": rec_a.blob_ref}


class TestForgetLineageCentrepiece:
    """EMAIL_A/B forget graph — proves lineage semantics, not just TTL."""

    def test_forget_email_a_preserves_shared_fact(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            refs = _seed_email_ab_scenario(vault)
            blob_a = refs["blob_a"]

            result = vault.forget_source(EMAIL_A)

            assert result.source_deleted is True
            assert FACT_X in result.surviving_derived_ids
            assert RELATION_Y in result.deleted_derived_ids
            assert EMBED_A in result.deleted_derived_ids
            assert SUMMARY_A in result.deleted_derived_ids
            assert vault.get_derived_record(FACT_X) is not None
            assert vault.get_derived_record(RELATION_Y) is None
            assert vault.get_derived_record(EMBED_A) is None
            assert vault.get_source_record(EMAIL_A) is None
            assert not vault.blob_exists(blob_a)
            assert vault.get_source_record(EMAIL_B) is not None
            assert vault.count_orphaned_derivatives() == 0

            fact = vault.get_derived_record(FACT_X)
            assert fact is not None
            assert EMAIL_A not in fact.lineage.derived_from
            assert EMAIL_B in fact.lineage.derived_from
            assert fact.confidence == pytest.approx(0.5)

    def test_forget_email_b_then_fact_x_gone(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            _seed_email_ab_scenario(vault)
            vault.forget_source(EMAIL_A)
            result_b = vault.forget_source(EMAIL_B)

            assert FACT_X in result_b.deleted_derived_ids
            assert vault.get_derived_record(FACT_X) is None
            assert vault.count_orphaned_derivatives() == 0

    def test_forget_audit_contains_no_sensitive_content(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            _seed_email_ab_scenario(vault)
            vault.forget_source(EMAIL_A)
            audit = vault.list_forget_audit(limit=1)
            assert len(audit) == 1
            entry = audit[0]
            assert entry["source_id"] == EMAIL_A
            assert isinstance(entry["deleted_derived_ids"], list)
            haystack = str(entry)
            assert SENTINEL_BODY_A not in haystack
            assert "ULTRA_SECRET" not in haystack


class TestDecayVsForget:
    """DECAY compresses; FORGET removes recoverability."""

    def test_decay_retains_utility_reduces_detail(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_raw_source(
                source="gmail",
                external_id="decay-msg",
                raw_content=b"body",
                record_id="SRC_DECAY",
            )
            vault.store_derived_new(
                record_id="ACTIVE_1",
                record_type=DerivedRecordType.FACT,
                payload={
                    "due_at": "tomorrow 5pm",
                    "subject": "Reply about charger rollout",
                    "exact_amount": 450,
                },
                derived_from=["SRC_DECAY"],
                purpose=RetentionPurpose.OPEN_LOOP_TRACKING,
                memory_layer=MemoryLayer.ACTIVE,
            )
            decayed = vault.decay_derived("ACTIVE_1")

            assert decayed.memory_layer == MemoryLayer.SHADOW
            assert decayed.payload.get("due_bucket") == "WITHIN_2_DAYS"
            assert decayed.payload.get("amount_band") == "UNDER_1000"
            assert decayed.payload.get("importance") == "ABSTRACTED"
            assert decayed.payload.get("_decayed") is True
            assert vault.get_derived_record("ACTIVE_1") is not None

    def test_forget_removes_record_entirely(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_raw_source(
                source="gmail",
                external_id="forget-msg",
                raw_content=b"secret body content",
                record_id="SRC_FORGET",
            )
            vault.store_derived_new(
                record_id="ONLY_FACT",
                record_type=DerivedRecordType.FACT,
                payload={"label": "solo"},
                derived_from=["SRC_FORGET"],
                purpose=RetentionPurpose.OPEN_LOOP_TRACKING,
            )
            vault.forget_source("SRC_FORGET")
            assert vault.get_derived_record("ONLY_FACT") is None
            assert vault.get_source_record("SRC_FORGET") is None

    def test_decay_is_not_rename_anti_pattern(self) -> None:
        """Forget must not pseudonymise — decay compresses fields, not aliases."""
        shadow = compress_payload_to_shadow(
            {"display_name": "Joe Atkinson", "subject": "annoyed about rollout"}
        )
        assert "Joe Atkinson" not in str(shadow.values())
        assert shadow.get("entity_ref") == "ABSTRACTED"

    def test_location_decay_coarsens_precise_value(self) -> None:
        shadow = compress_payload_to_shadow(
            {"location": "42 Baker Street, London, UK"}
        )
        assert shadow.get("coarse_region") == "REGION_LONDON"
        assert "Baker Street" not in str(shadow.values())

        pinpoint = compress_payload_to_shadow({"location": "Shoreditch"})
        assert pinpoint.get("coarse_region", "").startswith("REGION_BUCKET_")
        assert "Shoreditch" not in str(pinpoint.values())


class TestGcAndTtl:
    def test_gc_expires_7_day_raw_blob(
        self, vault_root: Path, memory_keychain
    ) -> None:
        old = datetime.now(tz=UTC) - timedelta(days=8)
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            rec = vault.store_raw_source(
                source="gmail",
                external_id="old-msg",
                raw_content=b"old body",
                record_id="OLD_SRC",
                received_at=old,
            )
            blob_ref = rec.blob_ref
            vault.store_derived_new(
                record_id="OLD_EMBED",
                record_type=DerivedRecordType.EMBEDDING,
                payload={"dims": 8},
                derived_from=["OLD_SRC"],
                purpose=RetentionPurpose.RETRIEVAL_INDEX,
            )
            result = vault.run_gc()

            assert "OLD_SRC" in result.expired_source_ids
            assert vault.get_source_record("OLD_SRC") is None
            assert not vault.blob_exists(blob_ref)
            assert vault.get_derived_record("OLD_EMBED") is None
            assert vault.count_orphaned_derivatives() == 0


class TestSensitiveInferenceGuard:
    def test_rejects_permanent_medical_storage(self) -> None:
        with pytest.raises(SensitiveInferenceError):
            assert_durable_write_allowed(
                payload={"note": "patient diagnosis: anxiety disorder"},
                retention_class=RetentionClass.ACTIVE_UNTIL_RESOLVED,
            )

    def test_allows_ephemeral_answer_only(self) -> None:
        assert_durable_write_allowed(
            payload={"note": "patient diagnosis: anxiety disorder"},
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
        )

    def test_classifies_financial_distress(self) -> None:
        assert (
            classify_sensitive_inference("received notice from debt collector")
            == SensitiveInferenceClass.FINANCIAL_DISTRESS
        )


class TestStolenDirectoryAfterForget:
    def test_stolen_dir_still_passes_after_forget(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            _seed_email_ab_scenario(vault)
            vault.forget_source(EMAIL_A)
            vault.forget_source(EMAIL_B)

        stolen_root = vault_root.parent / "stolen-after-forget"
        copy_vault_directory(vault_root, stolen_root)

        needles = (SENTINEL_BODY_A, SENTINEL_BODY_B, "ULTRA_SECRET")
        hits = search_directory_for_plaintext(stolen_root, needles)
        assert hits == []

        from personal_enigma.api.storage.vault import attempt_open_stolen_vault

        attempt_open_stolen_vault(stolen_root, generate_key())


class TestForgetResolverUnit:
    def test_resolve_exclusive_vs_independent(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            _seed_email_ab_scenario(vault)
            to_delete, to_survive = resolve_forget_plan(vault._conn, EMAIL_A)
            assert RELATION_Y in to_delete
            assert EMBED_A in to_delete
            assert FACT_X in to_survive
