"""SEC-04 end-to-end Gmail ingestion pipeline tests (fixture transport, no live OAuth)."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from personal_enigma.api.google.gmail.oauth import (
    GMAIL_READONLY_SCOPE,
    GmailScopeError,
    validate_gmail_oauth_scopes,
)
from personal_enigma.api.google.gmail.pipeline import (
    assert_canaries_blocked_at_egress,
    assert_no_plaintext_source_persistence,
    assert_transform_excludes_body,
    build_test_egress_gate,
    gmail_live_sync_enabled,
    ingest_gmail_to_vault,
    transform_message_for_remote,
)
from personal_enigma.api.google.gmail.sec04_adversarial import run_adversarial_parser_benchmark
from personal_enigma.api.sec03_adversarial import run_adversarial_benchmark
from personal_enigma.api.storage.keychain import MemoryKeychain
from personal_enigma.api.storage.vault import PrivateVault, search_directory_for_plaintext
from personal_enigma.fixtures.adversarial_email_cases import CASE_BY_ID
from personal_enigma.fixtures.alex_sensitive_canaries import (
    ALEX_SENSITIVE_CANARIES,
    ALL_CANARY_SENTINELS,
    CANARY_BY_ID,
)
from personal_enigma.fixtures.gmail_nasty_mailbox import NASTY_MAILBOX_MESSAGES
from personal_enigma.fixtures.nasty_mailbox_manifest import (
    MATRIX_BY_CATEGORY,
    FixtureKind,
    NastyMailboxCategory,
    assert_nasty_mailbox_manifest_complete,
)
from personal_enigma.ingestion.gmail_fixture import (
    GmailFixtureTransport,
    adversarial_case_to_gmail_json,
    build_nasty_mailbox_messages,
    canary_to_gmail_json,
    load_gmail_api_fixture,
)
from personal_enigma.ingestion.gmail_persistence import (
    LegacyPrivateStoreError,
    assert_gmail_encrypted_vault_persistence,
)
from personal_enigma.ingestion.sources.gmail import FORBIDDEN_GMAIL_WRITE_PATHS, GmailSource
from personal_enigma.worker.google.gmail import GmailSyncRequest, run_gmail_sync


@pytest.fixture
def memory_keychain(monkeypatch: pytest.MonkeyPatch) -> MemoryKeychain:
    monkeypatch.setenv("ENIGMA_KEYCHAIN_BACKEND", "memory")
    return MemoryKeychain()


def _vault_env(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    monkeypatch.setenv("ENIGMA_PERSISTENCE_BACKEND", "encrypted_vault")


def _nasty_source(
    *,
    vault_db: Path,
    messages: dict[str, dict[str, Any]] | None = None,
) -> GmailSource:
    return GmailSource(
        access_token="fixture-token",
        transport=GmailFixtureTransport(messages=messages),
        enforce_encrypted_vault=True,
        persistence_database_path=vault_db,
        remote_llm_enabled=False,
    )


def _messages_for_category(category: NastyMailboxCategory) -> dict[str, dict[str, Any]]:
    """Resolve manifest rows for one matrix category to Gmail API message dicts."""
    messages: dict[str, dict[str, Any]] = {}
    for entry in MATRIX_BY_CATEGORY[category]:
        if entry.fixture_kind == FixtureKind.ADVERSARIAL_EMAIL:
            case = CASE_BY_ID[entry.adversarial_case_id or entry.fixture_id]
            msg = adversarial_case_to_gmail_json(case)
        elif entry.fixture_kind == FixtureKind.SENSITIVE_CANARY:
            canary = CANARY_BY_ID[entry.canary_id or entry.fixture_id]
            msg = canary_to_gmail_json(canary)
        elif entry.fixture_kind == FixtureKind.GMAIL_API_JSON:
            assert entry.gmail_fixture is not None
            msg = load_gmail_api_fixture(entry.gmail_fixture)
        else:
            continue
        messages[str(msg["id"])] = msg
    return messages


def _category_sentinels(category: NastyMailboxCategory) -> tuple[str, ...]:
    if category != NastyMailboxCategory.CANARY_SECRETS:
        return ()
    return ALL_CANARY_SENTINELS


@pytest.mark.parametrize("category", list(NastyMailboxCategory))
def test_nasty_category_through_vault_pipeline(
    category: NastyMailboxCategory,
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each manifest category survives manifest → parser → encrypted vault."""
    root = tmp_path / f"private-{category.value}"
    _vault_env(monkeypatch, root)
    category_messages = _messages_for_category(category)
    assert category_messages, f"No messages resolved for {category.value}"

    async def _run() -> None:
        source = _nasty_source(vault_db=root / "vault.db", messages=category_messages)
        with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
            result = await ingest_gmail_to_vault(source, vault)
            assert result.message_count == len(category_messages)
            for row in result.records:
                assert row.parsed.untrusted is True
                assert row.message.body_text is not None
                stored = json.loads(vault.read_raw_source(row.source_record.id).decode("utf-8"))
                assert stored["classification"] == "PRIVATE_RAW"
                assert stored["untrusted"] is True
                assert stored["source"] == "gmail"
                assert_transform_excludes_body(
                    row.message,
                    forbidden_substrings=_category_sentinels(category),
                )
            sentinels = _category_sentinels(category)
            if sentinels:
                gate = build_test_egress_gate()
                assert_canaries_blocked_at_egress(gate, sentinel_strings=sentinels)
                for needle in sentinels[:3]:
                    hits = search_directory_for_plaintext(root, (needle,))
                    blob_hits = [path for path, _ in hits if "blobs" in path.parts]
                    assert not blob_hits, (
                        f"Plaintext canary in blob for {category.value}: {needle!r}"
                    )

    asyncio.run(_run())


def test_legacy_private_db_refused_for_gmail_ingest() -> None:
    with pytest.raises(LegacyPrivateStoreError, match="legacy_plaintext"):
        assert_gmail_encrypted_vault_persistence()


def test_nasty_mailbox_manifest_and_catalog_complete() -> None:
    assert_nasty_mailbox_manifest_complete()
    assert len(NASTY_MAILBOX_MESSAGES) >= len(build_nasty_mailbox_messages())


def test_fixture_transport_covers_full_nasty_matrix() -> None:
    messages = build_nasty_mailbox_messages()
    assert len(messages) == len(NASTY_MAILBOX_MESSAGES)


def test_nasty_mailbox_ingests_through_real_parser(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _vault_env(monkeypatch, root)

    async def _run() -> None:
        source = _nasty_source(vault_db=root / "vault.db")
        with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
            result = await ingest_gmail_to_vault(source, vault)
            assert result.message_count == len(build_nasty_mailbox_messages())
            assert result.next_cursor is not None
            for row in result.records:
                assert row.parsed.untrusted is True
                stored = json.loads(vault.read_raw_source(row.source_record.id).decode("utf-8"))
                assert stored["classification"] == "PRIVATE_RAW"
                assert stored["untrusted"] is True
                assert row.message.body_text is not None

    asyncio.run(_run())


def test_vault_blobs_not_plaintext_on_disk(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _vault_env(monkeypatch, root)
    needles = ALL_CANARY_SENTINELS[:5]

    async def _run() -> None:
        source = _nasty_source(vault_db=root / "vault.db")
        with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
            await ingest_gmail_to_vault(source, vault)
            for needle in needles:
                hits = search_directory_for_plaintext(root, (needle,))
                blob_hits = [path for path, _ in hits if "blobs" in path.parts]
                assert not blob_hits, f"Plaintext canary in blob: {needle!r}"

    asyncio.run(_run())


def test_canaries_blocked_at_egress_after_ingest(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _vault_env(monkeypatch, root)
    gate = build_test_egress_gate()

    async def _run() -> None:
        source = _nasty_source(vault_db=root / "vault.db")
        with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
            result = await ingest_gmail_to_vault(source, vault)
            assert result.message_count > 0
            for row in result.records:
                assert_transform_excludes_body(
                    row.message,
                    forbidden_substrings=ALL_CANARY_SENTINELS,
                )
            assert_canaries_blocked_at_egress(gate, sentinel_strings=ALL_CANARY_SENTINELS)

    asyncio.run(_run())


def test_no_plaintext_outside_encrypted_vault_tree(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _vault_env(monkeypatch, root)
    needles = tuple(canary.raw_marker for canary in ALEX_SENSITIVE_CANARIES[:3])

    async def _run() -> None:
        source = _nasty_source(vault_db=root / "vault.db")
        with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
            await ingest_gmail_to_vault(source, vault)
            assert_no_plaintext_source_persistence(vault, needles)

    asyncio.run(_run())


def test_transform_never_includes_wholesale_body() -> None:
    async def _run() -> None:
        source = _nasty_source(vault_db=Path("/tmp/enigma-test/private/vault.db"))
        batch = await source.get_changes(None)
        for item in batch.items[:5]:
            from personal_enigma.domain import PrivateMessage

            message = PrivateMessage.model_validate(item)
            remote = transform_message_for_remote(message)
            blob = json.dumps(remote.model_dump(mode="json"))
            if message.body_text:
                assert message.body_text not in blob
            assert remote.metadata["wholesale_body_included"] is False

    asyncio.run(_run())


def test_sec03_adversarial_cases_through_real_parser_path() -> None:
    verdicts = run_adversarial_parser_benchmark()
    failures = [v for v in verdicts if not v.passed]
    assert not failures, failures[0].failure_taxonomy if failures else None


def test_sec03_demo_path_still_green() -> None:
    verdicts = run_adversarial_benchmark()
    assert all(v.passed for v in verdicts)


def test_oauth_rejects_broader_scopes() -> None:
    with pytest.raises(GmailScopeError, match="exceed gmail.readonly"):
        validate_gmail_oauth_scopes(
            f"{GMAIL_READONLY_SCOPE} https://www.googleapis.com/auth/gmail.modify"
        )
    with pytest.raises(GmailScopeError, match="exceed gmail.readonly"):
        validate_gmail_oauth_scopes("https://www.googleapis.com/auth/calendar.readonly")
    with pytest.raises(GmailScopeError, match="required scope missing"):
        validate_gmail_oauth_scopes("")


def test_gmail_live_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_GMAIL_LIVE", raising=False)
    assert gmail_live_sync_enabled() is False


def test_worker_vault_sync_path(
    tmp_path: Path,
    memory_keychain: MemoryKeychain,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _vault_env(monkeypatch, root)

    async def _run() -> None:
        source = _nasty_source(vault_db=root / "vault.db")
        with PrivateVault.open(root=root, keychain=memory_keychain) as vault:
            result = await run_gmail_sync(
                GmailSyncRequest(access_token="fixture-token"),
                source=source,
                vault=vault,
                skip_persistence_guard=False,
            )
            assert result.vault_records == len(build_nasty_mailbox_messages())
            assert result.message_count == result.vault_records

    asyncio.run(_run())


def test_no_gmail_write_methods_in_connector_modules() -> None:
    from personal_enigma.ingestion import sources

    gmail_module = inspect.getfile(sources.gmail)
    text = Path(gmail_module).read_text(encoding="utf-8")
    assert "def send" not in text
    assert ".post(" not in text
    assert ".put(" not in text
    assert ".delete(" not in text
    for forbidden in FORBIDDEN_GMAIL_WRITE_PATHS:
        assert forbidden in text


def test_gmail_source_refuses_write_paths() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(lambda r: httpx.Response(404))
        source = GmailSource(access_token="fixture-token", transport=transport)
        with pytest.raises(Exception, match="write path refused"):
            await source._get_json("/users/me/messages/send")

    asyncio.run(_run())


@pytest.mark.skipif(
    not gmail_live_sync_enabled(),
    reason="Live Google OAuth smoke requires ENIGMA_GMAIL_LIVE=1 and credentials",
)
def test_live_oauth_smoke_optional() -> None:
    """Optional live TEST account smoke — skipped in CI by default."""
    pytest.skip("Live OAuth smoke not configured in this environment")
