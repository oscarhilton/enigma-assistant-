"""SEC-04 legacy private.db persistence guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.ingestion.gmail_persistence import (
    LegacyPrivateStoreError,
    PersistenceBackend,
    assert_gmail_encrypted_vault_persistence,
    default_legacy_database_path,
    is_legacy_private_db_path,
    resolve_gmail_persistence_path,
    resolve_persistence_backend,
)
from personal_enigma.ingestion.sources.gmail import GmailSource


def test_default_legacy_path_is_detected() -> None:
    path = default_legacy_database_path()
    assert path.name == "private.db"
    assert path.parent.name == "personal-enigma"
    assert is_legacy_private_db_path(path)


def test_vault_db_path_is_not_legacy() -> None:
    vault = Path.home() / ".enigma" / "private" / "vault.db"
    assert not is_legacy_private_db_path(vault)


def test_resolve_backend_legacy_from_default_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENIGMA_PERSISTENCE_BACKEND", raising=False)
    monkeypatch.delenv("ENIGMA_DATABASE_URL", raising=False)
    assert resolve_persistence_backend() == PersistenceBackend.LEGACY_PLAINTEXT


def test_resolve_backend_encrypted_vault_from_path() -> None:
    vault = Path("/tmp/enigma-test/private/vault.db")
    assert resolve_persistence_backend(database_path=vault) == PersistenceBackend.ENCRYPTED_VAULT


def test_resolve_backend_explicit_env_overrides_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = Path("/tmp/enigma-test/private/vault.db")
    monkeypatch.setenv("ENIGMA_PERSISTENCE_BACKEND", "legacy_plaintext")
    assert resolve_persistence_backend(database_path=vault) == PersistenceBackend.LEGACY_PLAINTEXT


def test_assert_refuses_default_legacy_target() -> None:
    with pytest.raises(LegacyPrivateStoreError, match="persistence_backend is legacy_plaintext"):
        assert_gmail_encrypted_vault_persistence()


def test_assert_refuses_explicit_legacy_backend() -> None:
    vault = Path("/tmp/enigma-test/private/vault.db")
    with pytest.raises(LegacyPrivateStoreError, match="legacy_plaintext"):
        assert_gmail_encrypted_vault_persistence(
            database_path=vault,
            persistence_backend=PersistenceBackend.LEGACY_PLAINTEXT,
        )


def test_assert_refuses_explicit_legacy_url() -> None:
    legacy = default_legacy_database_path()
    url = f"sqlite:///{legacy}"
    with pytest.raises(LegacyPrivateStoreError, match="legacy_plaintext"):
        assert_gmail_encrypted_vault_persistence(database_url=url)


def test_assert_refuses_env_legacy_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    legacy = tmp_path / "personal-enigma" / "private.db"
    legacy.parent.mkdir(parents=True)
    monkeypatch.setenv("ENIGMA_DATABASE_URL", f"sqlite:///{legacy}")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("ENIGMA_PERSISTENCE_BACKEND", raising=False)
    resolved = resolve_gmail_persistence_path()
    assert resolved == legacy.resolve()
    assert resolve_persistence_backend() == PersistenceBackend.LEGACY_PLAINTEXT
    with pytest.raises(LegacyPrivateStoreError):
        assert_gmail_encrypted_vault_persistence()


def test_assert_refuses_env_legacy_backend_even_on_vault_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = Path("/tmp/enigma-test/private/vault.db")
    monkeypatch.setenv("ENIGMA_PERSISTENCE_BACKEND", "legacy_plaintext")
    with pytest.raises(LegacyPrivateStoreError):
        assert_gmail_encrypted_vault_persistence(database_path=vault)


def test_assert_allows_vault_db_path() -> None:
    vault = Path("/tmp/enigma-test/private/vault.db")
    assert_gmail_encrypted_vault_persistence(database_path=vault)


def test_assert_allows_explicit_encrypted_vault_backend() -> None:
    legacy = default_legacy_database_path()
    assert_gmail_encrypted_vault_persistence(
        database_path=legacy,
        persistence_backend=PersistenceBackend.ENCRYPTED_VAULT,
    )


def test_gmail_source_init_refuses_legacy_when_enforced() -> None:
    with pytest.raises(LegacyPrivateStoreError):
        GmailSource(access_token="token", enforce_encrypted_vault=True)


def test_gmail_source_init_skips_guard_by_default() -> None:
    GmailSource(access_token="token")


def test_sec04_eval_has_no_dev_exception_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-04 eval must not offer a dev bypass for legacy_plaintext."""
    monkeypatch.setenv("ENIGMA_PERSISTENCE_BACKEND", "legacy_plaintext")
    with pytest.raises(LegacyPrivateStoreError, match="No fallback or dev exception"):
        assert_gmail_encrypted_vault_persistence()
