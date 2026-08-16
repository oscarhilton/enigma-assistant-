"""Hard invariants + full pipeline acceptance for Demo Mode corpus (D08b)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.evaluation.ground_truth import ScenarioSignalClass
from personal_enigma.simulation.cli import main as corpus_main
from personal_enigma.simulation.corpus.adapters.finepersonas import (
    FinePersonasAdapter,
    materialise_local_fixture,
)
from personal_enigma.simulation.corpus.cache import CorpusCache, DerivedCorpusCache
from personal_enigma.simulation.corpus.expand import expand_conversations
from personal_enigma.simulation.corpus.manifest import CorpusManifest, load_manifest
from personal_enigma.simulation.corpus.models import (
    CorpusConversation,
    CorpusMessage,
    CorpusProvenance,
)
from personal_enigma.simulation.corpus.pipeline import build_demo_safe_corpus
from personal_enigma.simulation.corpus.safety import (
    PublicDemoCorpusError,
    assert_public_demo_allowed,
)
from personal_enigma.simulation.corpus.sanitise import (
    GENERATION_METADATA_KEYS,
    SANITISER_VERSION,
    sanitise_conversation,
    sanitise_conversation_detailed,
    sanitise_raw_record,
)
from personal_enigma.simulation.corpus.selectors import select_conversations
from personal_enigma.simulation.corpus.streams import (
    CanonicalScenarioStream,
    CorpusBackgroundStream,
    GeneratedNoiseStream,
)
from personal_enigma.simulation.corpus.timeline import place_conversations_on_timeline
from personal_enigma.simulation.scenario import ScenarioEvent
from personal_enigma.simulation.sources.mail import SyntheticMailSource

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "corpus" / "finepersonas-mini"


def _load_mini() -> list[CorpusConversation]:
    async def _run() -> list[CorpusConversation]:
        adapter = FinePersonasAdapter(load_manifest(FIXTURE / "manifest.yaml"), root=FIXTURE)
        return [c async for c in adapter.iterate_conversations()]

    return asyncio.run(_run())


def test_scenario_signal_class_enum_values() -> None:
    assert ScenarioSignalClass.CANONICAL.value == "canonical"
    assert ScenarioSignalClass.BACKGROUND.value == "background"
    assert ScenarioSignalClass.NOISE.value == "noise"
    assert ScenarioSignalClass.ADVERSARIAL.value == "adversarial"


def test_public_demo_rejects_non_synthetic_confirmed() -> None:
    bad = CorpusManifest(
        id="enron-sample",
        provenance=CorpusProvenance.PUBLIC_REAL,
        profiles_allowed={"public_demo": True, "developer": True, "stress": True},
    )
    with pytest.raises(PublicDemoCorpusError, match="synthetic_confirmed"):
        assert_public_demo_allowed(bad)

    unknown = CorpusManifest(
        id="mystery",
        provenance=CorpusProvenance.UNKNOWN,
        profiles_allowed={"public_demo": True, "developer": True, "stress": True},
    )
    with pytest.raises(PublicDemoCorpusError):
        assert_public_demo_allowed(unknown)


def test_public_demo_accepts_finepersonas_mini() -> None:
    manifest = load_manifest(FIXTURE / "manifest.yaml")
    assert manifest.provenance == CorpusProvenance.SYNTHETIC_CONFIRMED
    assert_public_demo_allowed(manifest)


def test_seeded_selection_deterministic_for_mini_fixture() -> None:
    conversations = _load_mini()
    assert len(conversations) == 3
    a = select_conversations(conversations, seed="alex-v1-email-background-v1", count=2)
    b = select_conversations(conversations, seed="alex-v1-email-background-v1", count=2)
    assert [c.id for c in a] == [c.id for c in b]
    different = select_conversations(conversations, seed="other-seed", count=2)
    assert len(different) == 2
    # Selection is conversation-level — never drops messages from a thread.
    for conv in a:
        original = next(c for c in conversations if c.id == conv.id)
        assert len(conv.messages) == len(original.messages)


def test_sanitiser_strips_generation_metadata_fields() -> None:
    raw = json.loads((FIXTURE / "conversations.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert any(key in raw for key in GENERATION_METADATA_KEYS)
    cleaned = sanitise_raw_record(raw)
    assert GENERATION_METADATA_KEYS.isdisjoint(cleaned.keys())
    for email in cleaned["emails"]:
        assert GENERATION_METADATA_KEYS.isdisjoint(email.keys())


def test_sanitiser_rewrites_domains_urls_and_identities() -> None:
    conv = _load_mini()[0]
    dirty = CorpusConversation(
        id=conv.id,
        messages=[
            conv.messages[0].model_copy(
                update={
                    "body_text": conv.messages[0].body_text
                    + "\nSee https://partner-docs.corp/project/status for details."
                }
            ),
            *conv.messages[1:],
        ],
    )
    cleaned = sanitise_conversation(dirty, rewrite_seed="cast-v1")
    assert "partner-docs.corp" not in cleaned.messages[0].body_text
    assert "portal.company-" in cleaned.messages[0].body_text
    for msg in cleaned.messages:
        assert msg.sender_email.endswith(".example")
        for addr in msg.recipient_emails:
            assert addr.endswith(".example")
    senders = {m.sender_email for m in cleaned.messages}
    assert len(senders) >= 1


def test_sanitiser_rejects_secret_like_strings() -> None:
    conv = CorpusConversation(
        id="secret-conv",
        messages=[
            CorpusMessage(
                corpus_id="finepersonas-mini",
                conversation_id="secret-conv",
                message_index=0,
                sender_name="Leak Bot",
                sender_email="leak@acme.com",
                recipient_names=["Alex Morgan"],
                recipient_emails=["alex@morgan.example"],
                subject="creds",
                body_text="password=hunter2 and sk-abcdefghijklmnopqrstuvwxyz012345",
            )
        ],
    )
    result = sanitise_conversation_detailed(conv)
    assert result.conversation is None
    assert any(r.startswith("secret:") for r in result.diagnostics.reasons)


def test_signal_class_never_visible_on_synthetic_mail_messages() -> None:
    canonical = ScenarioEvent(
        id="canon-1",
        at=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
        source="mail",
        type="email.receive",
        payload={
            "id": "canon-1",
            "subject": "Atlas review",
            "body_text": "Please review Atlas",
            "from": "maya@northstar.example",
            "to": ["alex@morgan.example"],
            "signal_class": ScenarioSignalClass.CANONICAL.value,
            "source_class": "canonical",
            "expected_attention": True,
        },
    )
    background = ScenarioEvent(
        id="bg-1",
        at=datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
        source="mail",
        type="email.receive",
        payload={
            "id": "bg-1",
            "subject": "Invoice copy",
            "body_text": "FYI",
            "from": "sam@company-0001.example",
            "to": ["alex@morgan.example"],
            "signal_class": ScenarioSignalClass.BACKGROUND.value,
            "source_class": "background",
        },
    )
    noise = ScenarioEvent(
        id="noise-1",
        at=datetime(2026, 1, 10, 11, 0, tzinfo=UTC),
        source="mail",
        type="email.receive",
        payload={
            "id": "noise-1",
            "subject": "BuildCloud notification",
            "body_text": "Build finished",
            "from": "noreply@buildcloud.example",
            "to": ["alex@morgan.example"],
            "signal_class": ScenarioSignalClass.NOISE.value,
        },
    )

    source = SyntheticMailSource(
        streams=[
            CanonicalScenarioStream(events=[canonical]),
            CorpusBackgroundStream(events=[background]),
            GeneratedNoiseStream(events=[noise]),
        ]
    )

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    assert len(items) == 3
    for item in items:
        assert "signal_class" not in item
        assert "source_class" not in item
        assert "expected_attention" not in item
        assert "scenario_source" not in item
        assert "is_important" not in item


def test_expand_conversations_reaches_one_hundred() -> None:
    mini = _load_mini()
    expanded = expand_conversations(mini, target_count=100, seed="ci-expand")
    assert len(expanded) == 100
    assert len({c.id for c in expanded}) == 100
    assert all(len(c.messages) >= 1 for c in expanded)


def test_one_hundred_conversation_replay_is_deterministic(tmp_path: Path) -> None:
    manifest = load_manifest(FIXTURE / "manifest.yaml")
    mini = _load_mini()
    window_start = datetime(2026, 1, 1, tzinfo=UTC)
    window_end = datetime(2026, 6, 30, tzinfo=UTC)
    derived_a = DerivedCorpusCache(root=tmp_path / "derived-a")
    derived_b = DerivedCorpusCache(root=tmp_path / "derived-b")

    a = build_demo_safe_corpus(
        mini,
        manifest=manifest,
        seed="alex-v1-email-background-v1",
        count=100,
        window_start=window_start,
        window_end=window_end,
        derived=derived_a,
        expand_to=100,
        require_synthetic=True,
    )
    b = build_demo_safe_corpus(
        mini,
        manifest=manifest,
        seed="alex-v1-email-background-v1",
        count=100,
        window_start=window_start,
        window_end=window_end,
        derived=derived_b,
        expand_to=100,
        require_synthetic=True,
    )

    assert a.manifest["accepted_conversations"] == 100
    assert b.manifest["accepted_conversations"] == 100
    assert a.manifest["sanitiser_version"] == SANITISER_VERSION
    assert a.manifest["provenance"] == CorpusProvenance.SYNTHETIC_CONFIRMED.value
    assert [c.id for c in a.accepted] == [c.id for c in b.accepted]
    assert [(e.id, e.at.isoformat()) for e in a.events] == [
        (e.id, e.at.isoformat()) for e in b.events
    ]

    by_thread: dict[str, list[datetime]] = {}
    for event in a.events:
        thread = str(event.payload["thread_id"])
        by_thread.setdefault(thread, []).append(event.at)
    for stamps in by_thread.values():
        assert stamps == sorted(stamps)
        if len(stamps) > 1:
            assert all(earlier < later for earlier, later in zip(stamps, stamps[1:], strict=False))

    async def _fingerprint(events: list[ScenarioEvent]) -> list[tuple]:
        source = SyntheticMailSource(streams=[CorpusBackgroundStream(events=events)])
        batch = await source.get_changes(None)
        return [
            (item.get("id"), item.get("thread_id"), item.get("subject"), item.get("received_at"))
            for item in batch.items
        ]

    assert asyncio.run(_fingerprint(a.events)) == asyncio.run(_fingerprint(b.events))

    reloaded = derived_a.read_conversations(a.derived_dir)
    assert len(reloaded) == 100
    assert derived_a.read_manifest(a.derived_dir)["accepted_conversations"] == 100


def test_cli_corpus_commands_on_mini_fixture(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert corpus_main(["corpus", "list"]) == 0
    listed = capsys.readouterr().out
    assert "finepersonas-mini" in listed

    assert corpus_main(["corpus", "verify", "finepersonas-mini", "--public-demo"]) == 0
    assert corpus_main(["corpus", "inspect", "finepersonas-mini"]) == 0
    inspect_out = capsys.readouterr().out
    assert "finepersonas-mini" in inspect_out

    assert (
        corpus_main(["corpus", "sample", "finepersonas-mini", "--count", "2", "--seed", "cli"])
        == 0
    )
    sample_lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(sample_lines) == 2

    assert corpus_main(["corpus", "sanitise", "finepersonas-mini", "--seed", "cli"]) == 0
    sanitised = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(sanitised) == 3
    for line in sanitised:
        row = json.loads(line)
        for msg in row["messages"]:
            assert msg["sender_email"].endswith(".example")

    cache_root = tmp_path / "datasets"
    assert (
        corpus_main(
            [
                "corpus",
                "fetch",
                "finepersonas-mini",
                "--cache-root",
                str(cache_root),
                "--from-path",
                str(FIXTURE),
            ]
        )
        == 0
    )
    fetch_out = capsys.readouterr().out
    assert "ok:" in fetch_out
    assert (cache_root / "finepersonas-mini" / "mini-v1" / "conversations.jsonl").exists()

    derived_root = tmp_path / "derived"
    assert (
        corpus_main(
            [
                "corpus",
                "build",
                "finepersonas-mini",
                "--count",
                "100",
                "--expand-to",
                "100",
                "--seed",
                "cli-build",
                "--derived-root",
                str(derived_root),
                "--public-demo",
            ]
        )
        == 0
    )
    build_raw = capsys.readouterr().out.strip()
    assert build_raw, "expected corpus build JSON on stdout"
    build_out = json.loads(build_raw)
    assert build_out["accepted_conversations"] == 100
    assert Path(build_out["derived_dir"]).exists()


def test_fetch_missing_source_returns_error(tmp_path: Path) -> None:
    code = corpus_main(
        [
            "corpus",
            "fetch",
            "finepersonas-mini",
            "--cache-root",
            str(tmp_path / "c"),
            "--from-path",
            str(tmp_path / "missing"),
        ]
    )
    assert code == 2


def test_materialise_local_fixture(tmp_path: Path) -> None:
    target = tmp_path / "out"
    materialise_local_fixture(source_root=FIXTURE, target_root=target)
    assert (target / "conversations.jsonl").exists()


def test_place_conversations_deterministic() -> None:
    mini = _load_mini()
    window_start = datetime(2026, 1, 1, tzinfo=UTC)
    window_end = datetime(2026, 3, 1, tzinfo=UTC)
    a = place_conversations_on_timeline(
        mini, window_start=window_start, window_end=window_end, seed="t"
    )
    b = place_conversations_on_timeline(
        mini, window_start=window_start, window_end=window_end, seed="t"
    )
    assert [(e.id, e.at) for e in a] == [(e.id, e.at) for e in b]
    assert all(e.id.startswith("corpus:") for e in a)


def test_cache_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENIGMA_CORPUS_CACHE", str(tmp_path / "raw"))
    monkeypatch.setenv("ENIGMA_CORPUS_DERIVED", str(tmp_path / "der"))
    from personal_enigma.simulation.corpus.cache import (
        default_cache_root,
        default_derived_root,
    )

    assert default_cache_root() == tmp_path / "raw"
    assert default_derived_root() == tmp_path / "der"
    cache = CorpusCache()
    assert cache.revision_dir("x", "y") == tmp_path / "raw" / "x" / "y"
