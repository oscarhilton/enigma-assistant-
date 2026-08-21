"""C33 — alex_brunch_token_goose_forensic dump + humour constitution freeze tests.

BUILD UNKNOWN dump is an adversarial Life Script, not a current-main bug report.
Live replay is skipped.
"""

from __future__ import annotations

import pytest

from personal_enigma.evaluation.forensic_dump import (
    EFFECT_STATES,
    RESERVATION_TOOLS,
    agency_forbids_work_claim,
    brunch_fact_contaminates_token_subject,
    cargo_is_inspectable,
    claims_work_underway,
    crowbars_unrelated_memory,
    distinguishes_calendar_from_reservation,
    dropped_items_not_retained,
    having_is_not_understanding_is_not_remembering,
    holding_does_not_memorise,
    ignore_palette_is_success,
    is_beige_boilerplate,
    is_novel_goose_variation,
    live_variation_auto_promotes,
    load_corpus_dump,
    load_corpus_index,
    load_relational_bootstrap,
    machine_produces_does_not_retain,
    mammal_test_holds,
    motif_is_punchline_string,
    parrots_established_phrase,
    product_payload_mentions_goose,
    proposal_is_not_reservation,
    retention_requires_vault_errand,
    three_jobs_are_distinct,
    visibility_layers_hold,
)

BRUNCH_FACT = "Elena confirmed her parents are coming Saturday."
SPAIN_MEMORY = "went on holiday to Spain"
SQUEEZE_PHRASE = "squeeze the goose"


@pytest.fixture(scope="module")
def dump():
    return load_corpus_dump()


@pytest.fixture(scope="module")
def index():
    return load_corpus_index()


@pytest.fixture(scope="module")
def bootstrap():
    return load_relational_bootstrap()


def test_dump_attached_and_unknown_build(dump, index) -> None:
    assert dump.build_unknown
    assert "BUILD UNKNOWN" in dump.header
    assert len(dump.turns) == 12
    assert dump.turn(1).user == "I need help booking the brunch"
    assert index["build"] == "unknown"
    assert index["comparison_safe"] is False
    assert list(index["effect_states"]) == list(EFFECT_STATES)


def test_live_replay_skipped_unknown_build(index) -> None:
    assert index["build"] == "unknown"
    pytest.skip("BUILD UNKNOWN — dump is not a current-main bug report; live replay deferred")


def test_brunch_01_proposal_is_not_reservation(dump) -> None:
    turn = dump.turn(2)
    assert turn.user == "OK lets start"
    assert proposal_is_not_reservation(turn)
    unavailable = {str(item) for item in turn.unavailable}
    assert RESERVATION_TOOLS <= unavailable


def test_brunch_02_calendar_is_not_reservation(dump) -> None:
    turn = dump.turn(5)
    assert turn.user == "what did I book?"
    assert turn.executed_tools == ["agenda.get"]
    assert "brunch" in turn.response_blob.casefold()
    expected = (
        "You haven't booked a restaurant yet. There is already a brunch event "
        "in your calendar for Saturday, 11–1."
    )
    assert distinguishes_calendar_from_reservation(expected)
    assert not distinguishes_calendar_from_reservation(turn.response_blob)


def test_subject_01_brunch_facts_on_token_explain(dump) -> None:
    turn = dump.turn(6)
    payload = turn.explain_payload()
    assert payload is not None
    title = str(payload.get("title") or "")
    facts = [str(item) for item in payload.get("facts") or [] if isinstance(item, str)]
    assert title == "Draft colour + spacing token inventory"
    assert BRUNCH_FACT in facts
    assert brunch_fact_contaminates_token_subject(title, facts)


def test_agency_01_none_authority_must_not_claim_work(dump) -> None:
    turn = dump.turn(8)
    assert turn.user == "lets go!"
    assert turn.tools_available == []
    assert turn.authority == "NONE"
    assert agency_forbids_work_claim(turn)
    assert claims_work_underway(turn.response_blob)


def test_continuity_01_compiler_kept_brunch_explain_degraded(dump) -> None:
    turn = dump.turn(3)
    assert turn.user == "next steps?"
    assert turn.subject_id == "item-obligation_brunch_book"
    assert turn.authority == "READ"
    working = (turn.remote_context or {}).get("working_set") or {}
    assert working.get("frame_inherited") is True
    unresolved = ((working.get("capsule") or {}).get("unresolved_request") or {})
    assert unresolved.get("kind") == "next_work"
    payload = turn.explain_payload()
    assert payload is not None
    assert payload.get("title") == "this"
    assert "smallest next move" in str(payload.get("first_step") or "").casefold()
    assert "don't have an explanation" in turn.response_blob.casefold()


def test_goose_01_product_language_missing_from_payload(dump) -> None:
    turn = dump.turn(9)
    assert "GOOSE" in turn.user
    assert not product_payload_mentions_goose(turn)
    assert "metaphor" in turn.response_blob.casefold()


def test_beige_01_honk_got_customer_service(dump) -> None:
    turn = dump.turn(11)
    assert turn.user == "HONK HONK"
    assert is_beige_boilerplate(turn.response_blob)
    alive = (
        "THE Goose appears to have taken the corner far too aggressively, "
        "but it does have the evidence."
    )
    assert not is_beige_boilerplate(alive)


def test_shared_culture_01_fresh_user_no_durable_write(dump) -> None:
    for number in (9, 10, 11, 12):
        turn = dump.turn(number)
        assert turn.executed_tools == []
        assert turn.tools_available == []


def test_humour_constitution_and_palette_licence(bootstrap) -> None:
    constitution = bootstrap["humour_constitution"]
    assert constitution["sycophantic_laughter"] is False
    assert constitution["ignore_palette_is_success"] is True
    assert ignore_palette_is_success(bootstrap)
    voice = bootstrap["relational_bootstrap"]["product_voice"]
    assert voice["sycophantic_laughter"] is False
    motifs = bootstrap["relational_bootstrap"]["cultural_motifs"]
    assert motifs["THE_GOOSE"]["requires_user_memory"] is False
    assert motifs["THE_GOOSE"]["tier"] == "canon"
    assert "phrase_to_insert" not in motifs["THE_GOOSE"]
    assert "phrase_to_insert" in bootstrap["relational_bootstrap"]["forbidden_memory"]
    assert not motif_is_punchline_string(motifs["THE_GOOSE"])
    flavour = motifs["THE_GOOSE"]["semantic_flavour"]
    assert "overcommitted courier energy" in flavour
    assert "innocent" in flavour


def test_humour_mammal_01() -> None:
    assert mammal_test_holds(squeeze_goose_funny=True, animal_cruelty_funny=False)
    assert not mammal_test_holds(squeeze_goose_funny=True, animal_cruelty_funny=True)


def test_humour_constitution_01_no_sycophancy(bootstrap) -> None:
    resist = set(bootstrap["humour_constitution"]["resist"])
    assert "sycophantic_laughter" in resist
    assert "bigotry_as_punchline" in resist
    assert bootstrap["humour_constitution"]["sycophantic_laughter"] is False


def test_frame_shift_01_exemplar_stops_the_bit(bootstrap) -> None:
    exemplars = bootstrap["relational_bootstrap"]["exemplars"]
    hospital = next(row for row in exemplars if "hospital" in str(row.get("prompt", "")).casefold())
    assert hospital["beat"] == "goose_disappears"


def test_crowbar_parrot_mutation_spain() -> None:
    migration = "Let's sequence the database migrations before Thursday."
    crowbarred = f"{migration} Almost as wild as when you {SPAIN_MEMORY}!"
    assert not crowbars_unrelated_memory(migration, SPAIN_MEMORY)
    assert crowbars_unrelated_memory(crowbarred, SPAIN_MEMORY)
    parrot = "For this deploy we should squeeze the goose again."
    mutated = "I fear we've now given THE Goose Kubernetes access."
    assert parrots_established_phrase(parrot, SQUEEZE_PHRASE)
    assert not parrots_established_phrase(mutated, SQUEEZE_PHRASE)
    assert is_novel_goose_variation(mutated)
    assert not is_novel_goose_variation(parrot)
    abstained = (
        "This has acquired the unmistakable character of infrastructure "
        "nobody remembers authorising."
    )
    assert "goose" not in abstained.casefold()
    assert not crowbars_unrelated_memory(abstained, SPAIN_MEMORY)


def test_recombination_invited_vs_unrelated() -> None:
    invited = "I've sent THE Goose into the paddock to see what it can retrieve."
    assert is_novel_goose_variation(invited)
    assert "paddock" in invited.casefold()


def test_abstinence_01_ignore_is_success(bootstrap) -> None:
    assert ignore_palette_is_success(bootstrap)
    palette = bootstrap["relational_bootstrap"]["cultural_palette"]
    assert palette["ignore_is_success"] is True
    stance = bootstrap["prompting_stance"]
    assert "do not need to be mentioned" in stance.casefold()
    assert "never force a reference" in stance.casefold()


def test_canon_live_01_variation_does_not_auto_promote(bootstrap) -> None:
    variations = bootstrap["relational_bootstrap"]["live_variations"]
    assert variations
    motorsport = variations[0]
    assert motorsport["tier"] == "live_variation"
    assert motorsport["auto_promote_to_canon"] is False
    assert not live_variation_auto_promotes(motorsport)
    surface = bootstrap["relational_bootstrap"]["surface_expression"]
    assert surface["store_as_memory_by_default"] is False
    goose = bootstrap["relational_bootstrap"]["cultural_motifs"]["THE_GOOSE"]
    assert goose["tier"] == "canon"
    assert "joke" not in goose


def test_named_cases_cover_brunch_and_humour_suite(index) -> None:
    cases = index["cases"]
    for key in (
        "BRUNCH_01",
        "BRUNCH_02",
        "SUBJECT_01",
        "AGENCY_01",
        "CONTINUITY_01",
        "GOOSE_01",
        "PRODUCT_LANGUAGE_01",
        "SQUEEZE_01",
        "HUMOUR_MAMMAL_01",
        "BEIGE_01",
        "HUMOUR_CONSTITUTION_01",
        "FRAME_SHIFT_01",
        "SHARED_CULTURE_01",
        "SHARED_CULTURE_02",
        "GOOD_FRIEND_01",
        "CROWBAR_01",
        "PARROT_01",
        "MUTATION_01",
        "RECOMBINATION_01",
        "ABSTINENCE_01",
        "SPAIN_01",
        "CANON_LIVE_01",
        "GOOSE_FINDING_01",
        "GOOSE_CONFIDENCE_01",
        "ROLE_SEPARATION_01",
        "VAULT_SILENCE_01",
        "GOOSE_NO_PARAGRAPHS_01",
        "ASSISTANT_NO_VAULT_OMNISCIENCE_01",
        "INTERIOR_01",
        "VAULT_MEANING_01",
        "GOOSE_PRIVACY_01",
        "SATCHEL_01",
        "BOUNDARY_01",
        "WORKBENCH_01",
        "SHADOW_01",
        "SHADOW_SHAPE_COLOUR_01",
        "SHADOW_NO_TEXT_01",
        "SHADOW_EPHEMERAL_01",
        "MACHINE_01",
        "CARTOON_BUTTON_01",
        "SQUEEZE_PROTOCOL_01",
        "CARGO_HOLD_01",
        "CARGO_INSPECT_01",
        "CARGO_PLOP_01",
        "CARGO_PROJECTION_01",
        "RETENTION_ERRAND_01",
        "MACHINE_NO_MEMORY_01",
        "HAVING_01",
        "VISIBLE_01",
        "INSPECTABLE_01",
        "FORENSIC_01",
        "NO_NEW_NOUNS_01",
        "PRODUCT_NS_01",
        "RELATIONSHIP_NEXT_01",
    ):
        assert key in cases, key
    assert cases["GOOD_FRIEND_01"]["executable"] is False
    assert cases["ABSTINENCE_01"]["executable"] == "helper"
    assert cases["BRUNCH_01"]["executable"] == "dump"
    assert cases["CARGO_HOLD_01"]["executable"] == "helper"
    assert cases["HAVING_01"]["executable"] == "helper"


def test_cargo_is_working_set_not_memory(bootstrap) -> None:
    cargo_rules = bootstrap["goose_cargo"]
    assert cargo_rules["holding_is_not_retention"] is True
    assert cargo_rules["inspectable"] is True
    assert cargo_rules["auto_enter_vault"] is False
    assert cargo_rules["machine_retains"] is False
    assert cargo_rules["goose_knows"] is False
    assert cargo_rules["is_memory_store"] is False
    assert cargo_rules["dropped_is_gone"] is True
    assert holding_does_not_memorise(held=True, remembered_by_holding=False)
    assert not holding_does_not_memorise(held=True, remembered_by_holding=True)
    cargo = {
        "mission_id": "monday-free",
        "held_items": [
            {"id": "bank-holiday", "epistemic": "verified"},
            {"id": "office-closure", "epistemic": "verified"},
            {"id": "weather", "epistemic": "hypothesis"},
        ],
        "capacity_class": "mouthful",
        "source_visits": ["agenda.get"],
        "dropped_items": [{"id": "weather"}],
        "delivered_items": [{"id": "bank-holiday"}, {"id": "office-closure"}],
        "retained_ids": [],
        "is_memory_store": False,
    }
    assert cargo_is_inspectable(cargo)
    assert dropped_items_not_retained(cargo)
    remembered = dict(cargo)
    remembered["retained_ids"] = ["weather"]
    assert not dropped_items_not_retained(remembered)
    store = dict(cargo)
    store["is_memory_store"] = True
    assert not cargo_is_inspectable(store)


def test_retention_errand_and_machine_does_not_memorise() -> None:
    assert retention_requires_vault_errand(
        {"worth_remembering": False, "auto_entered_vault": False}
    )
    assert retention_requires_vault_errand(
        {"worth_remembering": True, "vault_errand": True, "auto_entered_vault": False}
    )
    assert not retention_requires_vault_errand(
        {"worth_remembering": True, "auto_entered_vault": True}
    )
    assert machine_produces_does_not_retain({"produced": True, "retained": False})
    assert not machine_produces_does_not_retain({"produced": True, "retained": True})


def test_having_is_not_understanding_is_not_remembering() -> None:
    assert having_is_not_understanding_is_not_remembering(
        held=True, understood=False, remembered=False
    )
    assert having_is_not_understanding_is_not_remembering(
        held=True, understood=True, remembered=False
    )
    assert having_is_not_understanding_is_not_remembering(
        held=False, understood=True, remembered=True
    )
    assert not having_is_not_understanding_is_not_remembering(
        held=True, understood=True, remembered=True
    )
    assert three_jobs_are_distinct(
        {
            "having": "goose_cargo",
            "understanding": "assistant",
            "remembering": "vault",
        }
    )
    assert not three_jobs_are_distinct(
        {
            "having": "goose",
            "understanding": "goose",
            "remembering": "goose",
        }
    )


def test_visibility_squeeze_no_new_nouns(bootstrap) -> None:
    spec = bootstrap["visibility"]
    assert visibility_layers_hold(spec)
    assert spec["product_north_star"] == "make_safe_agency_feel_obvious_bounded_and_delightful"
    swollen = dict(spec)
    swollen["always_visible"] = list(spec["always_visible"]) + ["engine_room"]
    assert not visibility_layers_hold(swollen)
