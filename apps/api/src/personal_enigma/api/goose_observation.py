"""C37 — Observe idle / walk / return. Do not invent C36.

Local SURFACE instrumentation. Never attach to the remote working set.
`possible_fix: NOT YET` is constitutional.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from personal_enigma.api.goose_pixels import (
    AgentWorkPhase,
    AgentWorkSnapshot,
    GooseExpressiveness,
    GooseMotion,
    GoosePixelLicence,
    license_goose_pixels,
)
from personal_enigma.api.relational_bootstrap import (
    RelationalBootstrapInputs,
    compile_relational_bootstrap,
)

PossibleFix = Literal["NOT YET"]
Severity = Literal["low", "medium", "high"]
TelemetryName = Literal[
    "goose_became_visible",
    "goose_motion_started",
    "goose_returned",
    "goose_inspected",
    "agent_work_changed",
    "frame_expression_changed",
]

POSSIBLE_FIX: PossibleFix = "NOT YET"

ALLOWED_TELEMETRY_EVENTS: frozenset[str] = frozenset(
    {
        "goose_became_visible",
        "goose_motion_started",
        "goose_returned",
        "goose_inspected",
        "agent_work_changed",
        "frame_expression_changed",
    }
)

FORBIDDEN_TELEMETRY_EVENTS: frozenset[str] = frozenset(
    {
        "goose_clicked_17_times",
        "goose_engagement_score",
        "user_affection",
        "daily_goose_retention",
    }
)

FORBIDDEN_INVENTION_TOKENS: frozenset[str] = frozenset(
    {
        "waiting_goose_with_newspaper.gif",
        "newspaper.gif",
        "affection",
        "speech bubble",
        "shadows",
        "satchel",
    }
)

_REPO_SCRIPTS = Path("packages/evaluation/scripts/goose_pixel_observation")

_GOOSE_CONVENTION = (
    "When the user honks, answer with short goose energy. No meta commentary."
)

_MOTION_INTERPRETATION: dict[GooseMotion, str] = {
    "absent": "not present",
    "idle": "looks finished",
    "walk": "actively working",
    "return": "returned with a result",
}


@dataclass(frozen=True, slots=True)
class GooseTelemetryEvent:
    name: TelemetryName
    motion: GooseMotion
    previous_motion: GooseMotion | None
    work_phase: AgentWorkPhase | None
    work_semantic_token: str
    expressiveness: GooseExpressiveness
    inspect_target: str | None
    inspect_labels: tuple[str, ...]
    implied_meaning: str


@dataclass
class GooseTelemetryLog:
    events: list[GooseTelemetryEvent] = field(default_factory=list)

    def emit(
        self,
        name: str,
        *,
        motion: GooseMotion,
        previous_motion: GooseMotion | None,
        work_phase: AgentWorkPhase | None,
        work_semantic_token: str,
        expressiveness: GooseExpressiveness,
        inspect_target: str | None,
        inspect_labels: tuple[str, ...],
    ) -> GooseTelemetryEvent:
        if name in FORBIDDEN_TELEMETRY_EVENTS:
            raise ValueError(f"engagement telemetry is forbidden: {name}")
        if name not in ALLOWED_TELEMETRY_EVENTS:
            raise ValueError(f"unknown goose telemetry event: {name}")
        event = GooseTelemetryEvent(
            name=name,  # type: ignore[arg-type]
            motion=motion,
            previous_motion=previous_motion,
            work_phase=work_phase,
            work_semantic_token=work_semantic_token,
            expressiveness=expressiveness,
            inspect_target=inspect_target,
            inspect_labels=inspect_labels,
            implied_meaning=implied_meaning(motion),
        )
        self.events.append(event)
        return event


@dataclass(frozen=True, slots=True)
class ObservationBeat:
    user: str | None
    work: AgentWorkSnapshot | None
    frame: str
    inspect: bool = False
    truth: str | None = None


@dataclass(frozen=True, slots=True)
class GooseObservationScript:
    scenario: str
    purpose: str
    beats: tuple[ObservationBeat, ...]
    possible_fix: PossibleFix = POSSIBLE_FIX


@dataclass(frozen=True, slots=True)
class GooseObservation:
    scenario: str
    goose_state: GooseMotion
    user_interpretation: str
    problem: bool
    severity: Severity
    possible_fix: PossibleFix = POSSIBLE_FIX

    def as_yaml(self) -> str:
        problem = "true" if self.problem else "false"
        return (
            f"scenario: {self.scenario}\n"
            "observed:\n"
            f"  goose_state: {self.goose_state}\n"
            f'  user_interpretation: "{self.user_interpretation}"\n'
            f"problem: {problem}\n"
            f"severity: {self.severity}\n"
            f"possible_fix: {self.possible_fix}\n"
        )


@dataclass(frozen=True, slots=True)
class DerivedAnswers:
    moved_when_work_moved: bool
    still_when_semantics_unchanged: bool
    inspect_matches_animation: bool | None
    frame_changed_only_presentation: bool | None


@dataclass(frozen=True, slots=True)
class BeatProjection:
    beat: ObservationBeat
    licence: GoosePixelLicence
    events: tuple[GooseTelemetryEvent, ...]


@dataclass(frozen=True, slots=True)
class ObservationReport:
    script: GooseObservationScript
    projections: tuple[BeatProjection, ...]
    observation: GooseObservation
    derived: DerivedAnswers
    log: GooseTelemetryLog


def implied_meaning(motion: GooseMotion) -> str:
    return _MOTION_INTERPRETATION[motion]


def scripts_dir(repo_root: Path) -> Path:
    return repo_root / _REPO_SCRIPTS


def _bootstrap(frame: str):
    return compile_relational_bootstrap(
        RelationalBootstrapInputs(
            product_voice="Direct, warm, never cloying.",
            interaction_prefs=("Established playful callbacks are allowed.",),
            shared_conventions=(_GOOSE_CONVENTION,),
            ephemeral_register=frame,
            exemplars=("honk", "honk honk"),
        )
    )


def _work_from_mapping(raw: Mapping[str, Any] | None) -> AgentWorkSnapshot | None:
    if raw is None:
        return None
    exists = bool(raw.get("exists", False))
    phase_raw = raw.get("phase")
    phase: AgentWorkPhase | None
    if phase_raw in {"in_flight", "waiting", "complete"}:
        phase = phase_raw
    else:
        phase = None
    labels_raw = raw.get("inspect_labels") or ()
    labels = tuple(str(label) for label in labels_raw)
    target = raw.get("inspect_target")
    return AgentWorkSnapshot(
        exists=exists,
        phase=phase,
        semantic_token=str(raw.get("semantic_token") or ""),
        inspect_target=str(target) if target else None,
        inspect_labels=labels,
    )


def script_from_mapping(data: Mapping[str, Any]) -> GooseObservationScript:
    fix = data.get("possible_fix", POSSIBLE_FIX)
    if fix != POSSIBLE_FIX:
        raise ValueError("possible_fix must be NOT YET for C37")
    beats: list[ObservationBeat] = []
    for raw_beat in data.get("beats") or ():
        if not isinstance(raw_beat, Mapping):
            raise ValueError("beat must be a mapping")
        user_raw = raw_beat.get("user")
        truth_raw = raw_beat.get("truth")
        work_raw = raw_beat.get("work")
        work = _work_from_mapping(work_raw if isinstance(work_raw, Mapping) else None)
        beats.append(
            ObservationBeat(
                user=str(user_raw) if user_raw is not None else None,
                work=work,
                frame=str(raw_beat.get("frame") or "goose"),
                inspect=bool(raw_beat.get("inspect", False)),
                truth=str(truth_raw) if truth_raw else None,
            )
        )
    scenario = str(data.get("scenario") or "")
    if not scenario:
        raise ValueError("scenario is required")
    return GooseObservationScript(
        scenario=scenario,
        purpose=str(data.get("purpose") or "").strip(),
        beats=tuple(beats),
        possible_fix=POSSIBLE_FIX,
    )


def _work_identity(work: AgentWorkSnapshot | None) -> tuple[object, ...]:
    if work is None:
        return (False, None, "")
    return (work.exists, work.phase, work.semantic_token)


def project_events(
    log: GooseTelemetryLog,
    *,
    previous_work: AgentWorkSnapshot | None,
    previous_licence: GoosePixelLicence | None,
    work: AgentWorkSnapshot | None,
    licence: GoosePixelLicence,
    inspected: bool = False,
) -> tuple[GooseTelemetryEvent, ...]:
    before = len(log.events)
    prev_motion: GooseMotion = previous_licence.motion if previous_licence else "absent"
    previous_motion = prev_motion if previous_licence else None
    work_phase = work.phase if work is not None else None

    def _emit(name: str) -> None:
        log.emit(
            name,
            motion=licence.motion,
            previous_motion=previous_motion,
            work_phase=work_phase,
            work_semantic_token=licence.work_semantic_token,
            expressiveness=licence.expressiveness,
            inspect_target=licence.inspect_target,
            inspect_labels=licence.inspect_labels,
        )

    if _work_identity(previous_work) != _work_identity(work):
        _emit("agent_work_changed")
    if (
        previous_licence is not None
        and previous_licence.expressiveness != licence.expressiveness
        and previous_licence.work_semantic_token == licence.work_semantic_token
    ):
        _emit("frame_expression_changed")
    if prev_motion == "absent" and licence.motion != "absent":
        _emit("goose_became_visible")
    if licence.motion != prev_motion and licence.motion != "absent":
        _emit("goose_motion_started")
    if licence.motion == "return" and prev_motion != "return":
        _emit("goose_returned")
    if inspected:
        _emit("goose_inspected")
    return tuple(log.events[before:])


def _beat_problem(truth: str | None, licence: GoosePixelLicence) -> tuple[bool, Severity, str]:
    interpretation = implied_meaning(licence.motion)
    if truth == "waiting_external" and licence.motion == "idle":
        return True, "medium", "looks finished"
    if truth == "waiting_external" and licence.motion == "walk":
        return True, "high", "looks actively working"
    if truth == "no_work" and licence.motion != "absent":
        return True, "high", "looks like work is happening"
    if truth in {"work_failed", "verification_failed"} and licence.motion == "return":
        return True, "high", "looks like the job succeeded"
    return False, "low", interpretation


def capture_observation(
    scenario: str,
    projections: tuple[BeatProjection, ...],
) -> GooseObservation:
    if not projections:
        return GooseObservation(
            scenario=scenario,
            goose_state="absent",
            user_interpretation="not present",
            problem=False,
            severity="low",
        )
    worst: GooseObservation | None = None
    for projection in projections:
        problem, severity, interpretation = _beat_problem(projection.beat.truth, projection.licence)
        candidate = GooseObservation(
            scenario=scenario,
            goose_state=projection.licence.motion,
            user_interpretation=interpretation,
            problem=problem,
            severity=severity,
        )
        if worst is None or _severity_rank(candidate) > _severity_rank(worst):
            worst = candidate
    assert worst is not None
    last = projections[-1]
    if not worst.problem:
        return GooseObservation(
            scenario=scenario,
            goose_state=last.licence.motion,
            user_interpretation=implied_meaning(last.licence.motion),
            problem=False,
            severity="low",
        )
    return worst


def _severity_rank(observation: GooseObservation) -> tuple[int, int]:
    ranks = {"low": 0, "medium": 1, "high": 2}
    return (1 if observation.problem else 0, ranks[observation.severity])


def derive_answers(
    projections: tuple[BeatProjection, ...],
    log: GooseTelemetryLog,
) -> DerivedAnswers:
    moved_when_work_moved = True
    still_when_semantics_unchanged = True
    previous: BeatProjection | None = None
    for projection in projections:
        if previous is not None:
            work_moved = _work_identity(previous.beat.work) != _work_identity(projection.beat.work)
            motion_changed = previous.licence.motion != projection.licence.motion
            if work_moved and motion_changed:
                names = {event.name for event in projection.events}
                if "agent_work_changed" not in names:
                    moved_when_work_moved = False
            if work_moved and not motion_changed and projection.licence.motion != "absent":
                moved_when_work_moved = False
            if (
                not work_moved
                and motion_changed
                and previous.licence.expressiveness == projection.licence.expressiveness
            ):
                still_when_semantics_unchanged = False
        previous = projection

    inspect_events = [event for event in log.events if event.name == "goose_inspected"]
    inspect_matches: bool | None
    if not inspect_events:
        inspect_matches = None
    else:
        inspect_matches = all(
            event.inspect_labels == _labels_for_event(event, projections)
            and event.implied_meaning == implied_meaning(event.motion)
            for event in inspect_events
        )

    frame_events = [event for event in log.events if event.name == "frame_expression_changed"]
    frame_only: bool | None
    if not frame_events:
        frame_only = None
    else:
        frame_only = True
        for projection in projections:
            names = {event.name for event in projection.events}
            if "frame_expression_changed" not in names:
                continue
            idx = projections.index(projection)
            if idx == 0:
                continue
            prev = projections[idx - 1]
            if _work_identity(prev.beat.work) != _work_identity(projection.beat.work):
                frame_only = False
            if prev.licence.motion != projection.licence.motion:
                frame_only = False
            if "agent_work_changed" in names:
                frame_only = False

    return DerivedAnswers(
        moved_when_work_moved=moved_when_work_moved,
        still_when_semantics_unchanged=still_when_semantics_unchanged,
        inspect_matches_animation=inspect_matches,
        frame_changed_only_presentation=frame_only,
    )


def _labels_for_event(
    event: GooseTelemetryEvent,
    projections: tuple[BeatProjection, ...],
) -> tuple[str, ...]:
    for projection in projections:
        if event in projection.events:
            return projection.licence.inspect_labels
    return event.inspect_labels


def play_script(script: GooseObservationScript) -> ObservationReport:
    log = GooseTelemetryLog()
    projections: list[BeatProjection] = []
    previous_work: AgentWorkSnapshot | None = None
    previous_licence: GoosePixelLicence | None = None
    for beat in script.beats:
        licence = license_goose_pixels(work=beat.work, bootstrap=_bootstrap(beat.frame))
        events = project_events(
            log,
            previous_work=previous_work,
            previous_licence=previous_licence,
            work=beat.work,
            licence=licence,
            inspected=beat.inspect,
        )
        projections.append(BeatProjection(beat=beat, licence=licence, events=events))
        previous_work = beat.work
        previous_licence = licence
    packed = tuple(projections)
    return ObservationReport(
        script=script,
        projections=packed,
        observation=capture_observation(script.scenario, packed),
        derived=derive_answers(packed, log),
        log=log,
    )


def reject_invention(blob: str) -> None:
    lowered = blob.casefold()
    for token in FORBIDDEN_INVENTION_TOKENS:
        if token in lowered:
            raise ValueError(f"C37 must not invent {token}")


def captured_observation_path(scenario: str, *, captured_dir: Path) -> Path:
    return captured_dir / f"{scenario}.yaml"


__all__ = [
    "ALLOWED_TELEMETRY_EVENTS",
    "FORBIDDEN_INVENTION_TOKENS",
    "FORBIDDEN_TELEMETRY_EVENTS",
    "POSSIBLE_FIX",
    "BeatProjection",
    "DerivedAnswers",
    "GooseObservation",
    "GooseObservationScript",
    "GooseTelemetryEvent",
    "GooseTelemetryLog",
    "ObservationBeat",
    "ObservationReport",
    "capture_observation",
    "captured_observation_path",
    "derive_answers",
    "implied_meaning",
    "play_script",
    "project_events",
    "reject_invention",
    "script_from_mapping",
    "scripts_dir",
]
