"""Evaluation-facing replay helpers (D11) — offline eval with recorded PAYG pairs."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.reasoning.replay_transport import (
    ProviderRecording,
    RecordingPaygTransport,
    RecordingPrivacyError,
    RecordingStore,
    ReplayMismatchError,
    ReplayMismatchPolicy,
    ReplayPaygTransport,
    assert_recording_safe,
    load_recording_store,
    request_hash,
    save_recording_store,
)

__all__ = [
    "ProviderRecording",
    "RecordingPaygTransport",
    "RecordingPrivacyError",
    "RecordingStore",
    "ReplayMismatchError",
    "ReplayMismatchPolicy",
    "ReplayPaygTransport",
    "assert_recording_safe",
    "default_replay_fixture_path",
    "load_recording_store",
    "request_hash",
    "save_recording_store",
]


def default_replay_fixture_path(scenario: str = "quiet-day") -> Path:
    """Path to the checked-in Demo replay fixture for ``scenario``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "packages" / "evaluation" / "fixtures" / "replay" / f"{scenario}.json"
        if candidate.is_file():
            return candidate
        candidate = parent / "scenarios" / "feature" / scenario / "recordings" / "payg.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no replay fixture found for scenario {scenario!r}")
