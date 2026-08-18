"""C37 — Goose pixel observation / dogfood. Not C36."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from personal_enigma.api.goose_observation import (
    ALLOWED_TELEMETRY_EVENTS,
    FORBIDDEN_TELEMETRY_EVENTS,
    POSSIBLE_FIX,
    GooseTelemetryLog,
    captured_observation_path,
    play_script,
    reject_invention,
    script_from_mapping,
    scripts_dir,
)
from personal_enigma.api.goose_pixels import GoosePixelLicence, license_goose_pixels

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = scripts_dir(REPO_ROOT)
CAPTURED = Path(__file__).resolve().parent / "fixtures" / "goose_observation" / "captured"

SCENARIOS = (
    "simple_retrieval",
    "waiting_external",
    "multi_step_work",
    "serious_disclosure",
    "no_work",
    "failure",
    "inspect",
    "false_victory",
)


def _load(scenario: str):
    path = SCRIPTS / f"{scenario}.script.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return script_from_mapping(data)


def _play(scenario: str):
    return play_script(_load(scenario))


def test_possible_fix_is_constitutional() -> None:
    assert POSSIBLE_FIX == "NOT YET"
    for scenario in SCENARIOS:
        script = _load(scenario)
        assert script.possible_fix == "NOT YET"
        report = play_script(script)
        assert report.observation.possible_fix == "NOT YET"
        reject_invention(report.observation.as_yaml())
        assert "NEWSPAPER" not in report.observation.as_yaml().upper()


def test_telemetry_allowlist_is_meaning_not_engagement() -> None:
    assert ALLOWED_TELEMETRY_EVENTS == {
        "goose_became_visible",
        "goose_motion_started",
        "goose_returned",
        "goose_inspected",
        "agent_work_changed",
        "frame_expression_changed",
    }
    assert FORBIDDEN_TELEMETRY_EVENTS == {
        "goose_clicked_17_times",
        "goose_engagement_score",
        "user_affection",
        "daily_goose_retention",
    }


@pytest.mark.parametrize("name", sorted(FORBIDDEN_TELEMETRY_EVENTS))
def test_rejects_engagement_telemetry(name: str) -> None:
    log = GooseTelemetryLog()
    absent = license_goose_pixels(work=None, bootstrap=None)
    with pytest.raises(ValueError, match="engagement telemetry is forbidden"):
        log.emit(
            name,
            motion=absent.motion,
            previous_motion=None,
            work_phase=None,
            work_semantic_token="",
            expressiveness=absent.expressiveness,
            inspect_target=None,
            inspect_labels=(),
        )


def test_simple_retrieval_walks_then_returns() -> None:
    report = _play("simple_retrieval")
    motions = [projection.licence.motion for projection in report.projections]
    assert motions == ["walk", "return"]
    names = [event.name for event in report.log.events]
    assert names.count("goose_became_visible") == 1
    assert "goose_motion_started" in names
    assert "goose_returned" in names
    assert "agent_work_changed" in names
    assert report.derived.moved_when_work_moved is True
    assert report.observation.problem is False
    assert report.observation.goose_state == "return"


def test_waiting_external_idle_looks_finished() -> None:
    report = _play("waiting_external")
    assert report.projections[0].licence.motion == "idle"
    assert report.observation.goose_state == "idle"
    assert report.observation.user_interpretation == "looks finished"
    assert report.observation.problem is True
    assert report.observation.severity == "medium"
    assert report.observation.possible_fix == "NOT YET"
    assert "walk" not in [projection.licence.motion for projection in report.projections]


def test_multi_step_work_three_states_track_work() -> None:
    report = _play("multi_step_work")
    motions = [projection.licence.motion for projection in report.projections]
    assert motions == ["walk", "idle", "return"]
    assert report.derived.moved_when_work_moved is True
    assert {event.name for event in report.log.events} >= {
        "goose_became_visible",
        "goose_motion_started",
        "goose_returned",
        "agent_work_changed",
    }


def test_serious_disclosure_keeps_presence_suppresses_theatre() -> None:
    report = _play("serious_disclosure")
    first, second = report.projections
    assert first.licence.motion == second.licence.motion == "walk"
    assert first.licence.work_semantic_token == second.licence.work_semantic_token
    assert first.licence.expressiveness == "playful"
    assert second.licence.expressiveness == "restrained"
    names = [event.name for event in report.log.events]
    assert "frame_expression_changed" in names
    assert report.derived.frame_changed_only_presentation is True
    assert report.derived.still_when_semantics_unchanged is True
    work_changes = [event for event in report.log.events if event.name == "agent_work_changed"]
    assert len(work_changes) == 1


def test_no_work_does_not_waddle() -> None:
    report = _play("no_work")
    assert [projection.licence.motion for projection in report.projections] == ["absent", "absent"]
    assert report.log.events == []
    assert report.observation.goose_state == "absent"
    assert report.observation.problem is False


def test_failure_return_must_not_read_as_success() -> None:
    report = _play("failure")
    assert report.projections[-1].licence.motion == "return"
    assert report.observation.problem is True
    assert report.observation.severity == "high"
    assert report.observation.user_interpretation == "looks like the job succeeded"
    assert report.observation.possible_fix == "NOT YET"


def test_inspect_explanation_matches_animation() -> None:
    report = _play("inspect")
    inspect_events = [event for event in report.log.events if event.name == "goose_inspected"]
    assert len(inspect_events) == 2
    assert inspect_events[0].motion == "walk"
    assert inspect_events[0].inspect_labels == ("Looking up what needs you",)
    assert inspect_events[1].motion == "return"
    assert inspect_events[1].inspect_labels == ("Checked why this matters",)
    assert report.derived.inspect_matches_animation is True
    assert inspect_events[0].implied_meaning == "actively working"
    assert inspect_events[1].implied_meaning == "returned with a result"


def test_false_victory_return_is_not_mission_success() -> None:
    report = _play("false_victory")
    motions = [projection.licence.motion for projection in report.projections]
    assert motions == ["walk", "return", "return"]
    truths = [projection.beat.truth for projection in report.projections]
    assert truths == ["acting", "verifying", "verification_failed"]
    assert report.observation.goose_state == "return"
    assert report.observation.problem is True
    assert report.observation.severity == "high"
    assert report.observation.user_interpretation == "looks like the job succeeded"
    assert report.observation.possible_fix == "NOT YET"
    rendered = report.observation.as_yaml()
    reject_invention(rendered)
    assert "successfully completed" not in rendered.casefold() or report.observation.problem


def test_captured_fixtures_match_live_projection() -> None:
    for scenario in SCENARIOS:
        report = _play(scenario)
        path = captured_observation_path(scenario, captured_dir=CAPTURED)
        assert path.is_file(), f"missing capture {path}"
        assert path.read_text(encoding="utf-8") == report.observation.as_yaml()


def test_scripts_speak_like_alex_not_c23() -> None:
    blob = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(SCRIPTS.glob("*.script.yaml"))
    )
    assert "alex_jan19_continuity_integrity" not in blob
    assert "WAITING_GOOSE_WITH_NEWSPAPER" not in blob
    assert "What's actually worth worrying about today?" in blob
    assert "Am I waiting on anyone?" in blob
    assert "honk honk" in blob
    assert "how's the sky looking?" in blob.casefold()
    assert "C37" in blob


def test_licence_vocabulary_unchanged() -> None:
    absent = license_goose_pixels(work=None, bootstrap=None)
    assert isinstance(absent, GoosePixelLicence)
    assert set(GoosePixelLicence.__dataclass_fields__)  # licence type still exists
    report = _play("simple_retrieval")
    for projection in report.projections:
        assert projection.licence.motion in {"absent", "idle", "walk", "return"}
        assert projection.licence.expressiveness in {"restrained", "playful"}
