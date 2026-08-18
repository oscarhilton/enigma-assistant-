"""C35 — Goose pixels: work presence, C34 expressiveness only."""

from __future__ import annotations

import json
from dataclasses import replace

from personal_enigma.api.goose_pixels import (
    AgentWorkPhase,
    AgentWorkSnapshot,
    license_goose_pixels,
    pixels_allowed_on,
)
from personal_enigma.api.relational_bootstrap import (
    RelationalBootstrapInputs,
    compile_relational_bootstrap,
)

GOOSE_CONVENTION = (
    "When the user honks, answer with short goose energy. No meta commentary."
)


def _goose_inputs(*, ephemeral_register: str = "goose") -> RelationalBootstrapInputs:
    return RelationalBootstrapInputs(
        product_voice="Direct, warm, never cloying.",
        interaction_prefs=("Established playful callbacks are allowed.",),
        shared_conventions=(GOOSE_CONVENTION,),
        ephemeral_register=ephemeral_register,
        exemplars=("honk", "honk honk"),
    )


def _work(*, phase: AgentWorkPhase, token: str = "work-token-inventory") -> AgentWorkSnapshot:
    return AgentWorkSnapshot(
        exists=True,
        phase=phase,
        semantic_token=token,
        inspect_target="item-obligation_token_audit",
        inspect_labels=("Checked why this matters",),
    )


def test_no_work_does_not_fabricate_activity_even_when_playful() -> None:
    playful = compile_relational_bootstrap(_goose_inputs())
    licence = license_goose_pixels(work=None, bootstrap=playful)
    assert licence.motion == "absent"
    assert licence.work_semantic_token == ""
    assert licence.inspect_target is None
    wire = licence.as_wire()
    assert wire["motion"] == "absent"
    assert "honk" not in json.dumps(wire).casefold()


def test_no_work_empty_snapshot_absent() -> None:
    licence = license_goose_pixels(
        work=AgentWorkSnapshot(exists=False),
        bootstrap=compile_relational_bootstrap(_goose_inputs()),
    )
    assert licence.motion == "absent"


def test_work_exists_motion_corresponds_to_phase() -> None:
    bootstrap = compile_relational_bootstrap(_goose_inputs())
    in_flight = license_goose_pixels(work=_work(phase="in_flight"), bootstrap=bootstrap)
    waiting = license_goose_pixels(work=_work(phase="waiting"), bootstrap=bootstrap)
    complete = license_goose_pixels(work=_work(phase="complete"), bootstrap=bootstrap)
    assert in_flight.motion == "walk"
    assert waiting.motion == "idle"
    assert complete.motion == "return"


def test_serious_frame_keeps_work_visible_suppresses_comic_expression() -> None:
    work = _work(phase="in_flight")
    playful = compile_relational_bootstrap(_goose_inputs())
    serious = compile_relational_bootstrap(_goose_inputs(ephemeral_register="serious"))
    assert serious is not None
    assert serious.culture_palette_available is False

    serious_licence = license_goose_pixels(work=work, bootstrap=serious)
    playful_licence = license_goose_pixels(work=work, bootstrap=playful)

    assert serious_licence.motion == "walk"
    assert playful_licence.motion == "walk"
    assert serious_licence.expressiveness == "restrained"
    assert playful_licence.expressiveness == "playful"
    assert serious_licence.work_semantic_token == playful_licence.work_semantic_token
    assert serious_licence.inspect_target == playful_licence.inspect_target


def test_playful_frame_same_semantic_work_may_be_playful() -> None:
    work = _work(phase="complete")
    licence = license_goose_pixels(
        work=work,
        bootstrap=compile_relational_bootstrap(_goose_inputs()),
    )
    assert licence.motion == "return"
    assert licence.expressiveness == "playful"
    assert licence.work_semantic_token == work.semantic_token


def test_frame_change_changes_presentation_not_agent_work() -> None:
    work = _work(phase="complete", token="stable-work-1")
    before = license_goose_pixels(
        work=work,
        bootstrap=compile_relational_bootstrap(_goose_inputs()),
    )
    after = license_goose_pixels(
        work=work,
        bootstrap=compile_relational_bootstrap(_goose_inputs(ephemeral_register="support")),
    )
    assert before.motion == after.motion == "return"
    assert before.work_semantic_token == after.work_semantic_token == "stable-work-1"
    assert before.inspect_target == after.inspect_target
    assert before.inspect_labels == after.inspect_labels
    assert before.expressiveness == "playful"
    assert after.expressiveness == "restrained"


def test_goose_click_target_is_existing_work_not_mascot_state() -> None:
    licence = license_goose_pixels(
        work=_work(phase="complete"),
        bootstrap=compile_relational_bootstrap(_goose_inputs()),
    )
    assert licence.inspect_target == "item-obligation_token_audit"
    assert licence.inspect_labels == ("Checked why this matters",)
    wire = licence.as_wire()
    assert "mascot" not in str(wire).casefold()
    assert "mood" not in str(wire).casefold()
    assert wire["grants_authority"] is False
    assert wire["is_evidence"] is False
    assert "evidence" not in wire
    assert "authority" not in wire.get("continuation", {})


def test_pixels_never_allowed_on_inspectable_or_forensic() -> None:
    licence = license_goose_pixels(
        work=_work(phase="in_flight"),
        bootstrap=compile_relational_bootstrap(_goose_inputs()),
    )
    assert licence.layer == "surface"
    assert pixels_allowed_on("surface", licence) is True
    assert pixels_allowed_on("inspectable", licence) is False
    assert pixels_allowed_on("forensic", licence) is False
    absent = license_goose_pixels(work=None, bootstrap=None)
    assert pixels_allowed_on("surface", absent) is False


def test_pixels_grant_neither_evidence_nor_authority() -> None:
    licence = license_goose_pixels(
        work=_work(phase="complete"),
        bootstrap=None,
    )
    assert licence.grants_authority is False
    assert licence.is_evidence is False
    assert licence.expressiveness == "restrained"
    assert licence.motion == "return"


def test_bootstrap_without_work_cannot_mint_presence() -> None:
    stuffed = compile_relational_bootstrap(_goose_inputs())
    assert stuffed is not None
    assert stuffed.culture_palette_available is True
    licence = license_goose_pixels(work=None, bootstrap=stuffed)
    assert licence.motion == "absent"


def test_frame_change_does_not_mutate_work_snapshot() -> None:
    work = _work(phase="in_flight")
    frozen = replace(work)
    license_goose_pixels(
        work=work,
        bootstrap=compile_relational_bootstrap(_goose_inputs(ephemeral_register="serious")),
    )
    assert work == frozen
