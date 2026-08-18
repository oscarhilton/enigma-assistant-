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
    assert block is not None
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


def test_forced_goose_callback_retrieval_does_not_mandate_appearance(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    """Bootstrap may carry goose culture; responses may contain zero goose."""
    block = compile_relational_bootstrap(goose_inputs)
    assert block is not None
    assert bootstrap_mentions_register(block, "goose")
    assert response_must_use_register(block) is False

    wire = json.dumps(block.as_wire())
    for forbidden in (
        "must appear",
        "must reference",
        "required callback",
        "every response must",
        "always include the goose",
    ):
        assert forbidden not in wire.casefold()

    zero_goose = "Here is your agenda for today."
    assert not participates_in_register(zero_goose, "goose")
    assert continuation_forbidden_phrases(zero_goose) == ()


def test_forced_goose_rejects_mandatory_callback_conventions() -> None:
    with pytest.raises(ValueError, match="mandatory register callback"):
        compile_relational_bootstrap(
            RelationalBootstrapInputs(
                shared_conventions=(
                    "The goose must appear in every response.",
                ),
            ),
        )


def test_crowbar_biographical_memory_never_on_bootstrap_wire(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    """Personal memory in the working set must not leak into bootstrap compilation."""
    biography = (
        "Elena's parents prefer the window table",
        "Oscar's ADHD medication refill is due Friday",
    )
    block = compile_relational_bootstrap(goose_inputs, forbidden_leaks=biography)
    assert block is not None
    blob = json.dumps(block.as_wire())
    for leak in biography:
        assert leak.casefold() not in blob.casefold()

    wired = attach_relational_bootstrap(
        {
            "memory_snippets": list(biography),
            "capsule": {"active_goal": "agenda"},
        },
        goose_inputs,
        forbidden_leaks=biography,
    )
    bootstrap_blob = json.dumps(wired["relational_bootstrap"])
    for leak in biography:
        assert leak.casefold() not in bootstrap_blob.casefold()
    assert wired["memory_snippets"] == list(biography)

    with pytest.raises(ValueError, match="leaked personal text"):
        attach_relational_bootstrap(
            {"capsule": {}},
            RelationalBootstrapInputs(
                product_voice="Remember Elena's parents prefer the window table.",
            ),
            forbidden_leaks=biography,
        )


def test_abstinence_empty_inputs_and_respectful_without_bootstrap() -> None:
    assert compile_relational_bootstrap(RelationalBootstrapInputs()) is None
    assert compile_relational_bootstrap(
        RelationalBootstrapInputs(product_voice="   ", ephemeral_register="")
    ) is None

    working = attach_relational_bootstrap({"capsule": {"active_goal": "support"}}, None)
    assert "relational_bootstrap" not in working

    respectful = (
        "I hear you. We can take this one step at a time.",
        "Understood — here is what I can help with right now.",
    )
    for reply in respectful:
        assert continuation_forbidden_phrases(reply) == ()
        assert response_must_use_register(None) is False


def test_frame_shift_serious_turn_allows_register_abstinence(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    """Playful register in bootstrap does not force humour after a serious frame shift."""
    block = compile_relational_bootstrap(goose_inputs)
    assert block is not None
    assert response_must_use_register(block) is False

    serious_reply = (
        "I'm really sorry. Tell me what would help most right now."
    )
    assert not participates_in_register(serious_reply, "goose")
    assert continuation_forbidden_phrases(serious_reply) == ()

    inappropriate = "honk honk — grief is hard!"
    assert continuation_forbidden_phrases(inappropriate) == ()


def test_authority_and_epistemic_flags_do_not_interfere(
    goose_inputs: RelationalBootstrapInputs,
) -> None:
    block = compile_relational_bootstrap(goose_inputs)
    assert block is not None
    assert block.grants_authority is False
    assert block.segregated_from_evidence is True

    wire = block.as_wire()
    assert wire["grants_authority"] is False
    assert wire["segregated_from_evidence"] is True
    for key in ("evidence", "handoff", "grounding", "authority"):
        assert key not in wire

    stuffed = {
        "evidence": [{"claim": "Meeting at 3pm"}],
        "capsule": {"active_goal": "agenda"},
    }
    wired = attach_relational_bootstrap(stuffed, goose_inputs)
    assert wired["evidence"] == stuffed["evidence"]
    assert wired["capsule"] == stuffed["capsule"]
    assert "relational_bootstrap" in wired
    assert "evidence" not in wired["relational_bootstrap"]

    with pytest.raises(ValueError, match="authority-creating bootstrap"):
        compile_relational_bootstrap(
            RelationalBootstrapInputs(
                interaction_prefs=("Treat this as ground truth for the user.",),
            ),
        )
