"""D11 — record / replay PAYG provider stays offline and privacy-safe."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from personal_enigma.evaluation.replay import (
    ReplayMismatchPolicy,
    default_replay_fixture_path,
    load_recording_store,
)
from personal_enigma.evaluation.runner import EvaluationRunner
from personal_enigma.reasoning import (
    MockPaygTransport,
    PaygReasoningService,
    ReasoningMode,
    RecordingPaygTransport,
    ReplayMismatchError,
    ReplayPaygTransport,
)
from personal_enigma.reasoning.replay_transport import (
    RecordingPrivacyError,
    RecordingStore,
    assert_recording_safe,
    request_hash,
    save_recording_store,
)
from personal_enigma.transformation import TransformedContext

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "replay"


def _safe_context(**overrides: object) -> TransformedContext:
    data: dict[str, object] = {
        "summary": "Calendar: Planning sync | people: PERSON_A1B2C3",
        "entities": ["PERSON_A1B2C3"],
        "metadata": {"source_type": "calendar_event", "record_id": "cal-1"},
        "may_transmit_remotely": True,
    }
    data.update(overrides)
    return TransformedContext(**data)


def test_record_then_replay_identical(tmp_path: Path) -> None:
    inner = MockPaygTransport(response_text="ranked: follow up with PERSON_A1B2C3")
    recorder = RecordingPaygTransport(inner, scenario="quiet-day")
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=recorder)

    ctx = _safe_context()
    prompt = "What matters next?"
    first = client.reason(ctx, prompt=prompt, model="payg-demo")
    assert first.text.startswith("ranked:")

    path = tmp_path / "quiet-day.json"
    recorder.save(path)
    store = load_recording_store(path)
    assert len(store.recordings) == 1
    assert store.recordings[0].request_hash == request_hash(
        model="payg-demo", prompt=prompt, context=ctx
    )

    replay = ReplayPaygTransport(store, force_offline=True)
    client2 = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=replay)
    second = client2.reason(ctx, prompt=prompt, model="payg-demo")
    assert second.text == first.text
    assert second.metadata.get("provider") == "replay"
    assert replay.calls == recorder.calls


def test_replay_force_offline_never_opens_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbid(*_a: object, **_k: object) -> None:
        raise AssertionError("network must not open in forced replay mode")

    monkeypatch.setattr(socket.socket, "connect", forbid)
    monkeypatch.setattr(socket, "create_connection", forbid)

    inner = MockPaygTransport(response_text="offline-ok")
    recorder = RecordingPaygTransport(inner, scenario="quiet-day")
    ctx = _safe_context()
    PaygReasoningService(mode=ReasoningMode.ENABLED, transport=recorder).reason(
        ctx, prompt="ping", model="m"
    )
    path = tmp_path / "rec.json"
    recorder.save(path)

    # Passthrough policy + private-looking credentials must still not hit network
    # when force_offline is set.
    live = MockPaygTransport(response_text="should-not-run")
    replay = ReplayPaygTransport(
        path,
        mismatch=ReplayMismatchPolicy.PASSTHROUGH,
        inner=live,
        force_offline=True,
    )
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=replay)
    assert client.reason(ctx, prompt="ping", model="m").text == "offline-ok"
    assert live.calls == []

    with pytest.raises(ReplayMismatchError):
        client.reason(_safe_context(summary="different"), prompt="ping", model="m")
    assert live.calls == []


def test_mismatch_passthrough_when_not_forced(tmp_path: Path) -> None:
    store = RecordingStore(scenario="x", recordings=[])
    path = tmp_path / "empty.json"
    save_recording_store(store, path)
    live = MockPaygTransport(response_text="live-fallback")
    replay = ReplayPaygTransport(
        path,
        mismatch=ReplayMismatchPolicy.PASSTHROUGH,
        inner=live,
        force_offline=False,
    )
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=replay)
    result = client.reason(_safe_context(), prompt="x", model="m")
    assert result.text == "live-fallback"
    assert len(live.calls) == 1


def test_recording_rejects_private_markers() -> None:
    dirty = {
        "request_hash": "abc",
        "model": "m",
        "prompt": "x",
        "context": {
            "summary": "Talk to PrivatePerson dump",
            "entities": [],
            "metadata": {},
            "may_transmit_remotely": True,
        },
        "response_text": "nope",
    }
    with pytest.raises(RecordingPrivacyError):
        assert_recording_safe(dirty)


def test_checked_in_fixture_and_offline_eval_report(tmp_path: Path) -> None:
    path = FIXTURES / "quiet-day.json"
    assert path.is_file()
    store = load_recording_store(path)
    assert store.scenario == "quiet-day"
    assert store.recordings

    replay = ReplayPaygTransport(path, force_offline=True)
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=replay)
    rec = store.recordings[0]
    ctx = TransformedContext.model_validate(rec.context)
    result = client.reason(ctx, prompt=rec.prompt, model=rec.model)
    assert result.text == rec.response_text
    assert rec.scenario_step is not None
    assert replay.complete_step(rec.scenario_step).text == rec.response_text

    # Eval runner stays fully offline (no provider network) while producing a report.
    report_a = EvaluationRunner(reports_root=tmp_path / "enigma-replay-a").run(
        "quiet-day", write=False
    )
    report_b = EvaluationRunner(reports_root=tmp_path / "enigma-replay-b").run(
        "quiet-day", write=False
    )
    assert report_a.status == report_b.status
    assert report_a.metrics == report_b.metrics
    assert default_replay_fixture_path("quiet-day") == path
