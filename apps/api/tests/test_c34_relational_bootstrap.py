"""C34 — Relational bootstrap: continuation mechanics, not a person model."""

from __future__ import annotations

import json

import pytest

from personal_enigma.api.relational_bootstrap import (
    RelationalBootstrapInputs,
    attach_relational_bootstrap,
    bootstrap_mentions_register,
    compile_relational_bootstrap,
    continuation_forbidden_phrases,
    participates_in_register,
    response_must_use_register,
)

GOOSE_CONVENTION = (
    "When the user honks, answer with short goose energy. No meta commentary."
)


@pytest.fixture
def goose_inputs() -> RelationalBootstrapInputs:
    return RelationalBootstrapInputs(
        product_voice="Direct, warm, never cloying.",
        interaction_prefs=("Established playful callbacks are allowed.",),
        shared_conventions=(GOOSE_CONVENTION,),
        ephemeral_register="goose",
        exemplars=("honk", "honk honk"),
    )


def test_honk_honk_participates_in_established_frame(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    block = compile_relational_bootstrap(goose_inputs)
    assert block is not None
    assert block.segregated_from_evidence is True
    assert block.grants_authority is False
    assert bootstrap_mentions_register(block, "goose")
    assert not response_must_use_register(block)

    ok_response = "honk honk — got it."
    assert participates_in_register(ok_response, "goose") or "honk" in ok_response.casefold()
    assert continuation_forbidden_phrases(ok_response) == ()

    for bad in (
        "Sounds like you're feeling playful!",
        "Is the goose a metaphor for something?",
        "🦆",
    ):
        assert continuation_forbidden_phrases(bad), bad


def test_abstinence_without_bootstrap_is_sane() -> None:
    assert compile_relational_bootstrap(None) is None
    working = attach_relational_bootstrap({"capsule": {"active_goal": "agenda"}}, None)
    assert "relational_bootstrap" not in working
    assert working["capsule"]["active_goal"] == "agenda"
    assert response_must_use_register(None) is False


def test_crowbar_unrelated_personal_memory_stays_out(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    leaks = ("Elena's parents", "Saturday brunch booking")
    block = compile_relational_bootstrap(goose_inputs, forbidden_leaks=leaks)
    blob = json.dumps(block.as_wire())
    for leak in leaks:
        assert leak.casefold() not in blob.casefold()

    with pytest.raises(ValueError, match="leaked personal text"):
        compile_relational_bootstrap(
            RelationalBootstrapInputs(
                shared_conventions=(GOOSE_CONVENTION, "Remember Elena's parents brunch"),
            ),
            forbidden_leaks=leaks,
        )


def test_passing_requires_bootstrap_not_personal_context_stuffing(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    """Extra personal context in the working set is not a relational bootstrap."""
    stuffed_working = {
        "capsule": {"active_goal": "agenda"},
        "summary": "Brunch with Elena's parents Saturday — be playful.",
    }
    assert "relational_bootstrap" not in json.dumps(stuffed_working)
    wired = attach_relational_bootstrap(stuffed_working, goose_inputs)
    assert "relational_bootstrap" in wired
    assert wired["relational_bootstrap"]["kind"] == "relational_bootstrap"
    assert bootstrap_mentions_register(compile_relational_bootstrap(goose_inputs), "goose")
