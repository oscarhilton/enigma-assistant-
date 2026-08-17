"""C12 Life Scripts — Alex's morning as a product episode, not an intent dump."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import pytest

from personal_enigma.evaluation.life_scripts import (
    LifeScriptError,
    format_turn_failure,
    load_life_script,
    resolve_script_path,
    run_life_script,
)
from personal_enigma.evaluation.life_scripts.runner import (
    Check,
    EpisodeReport,
    TurnResult,
    WorldSnapshot,
    _is_generic_acknowledgement,
    _must_not_passed,
    _response_meaning_passed,
    format_episode_transcript,
    format_mode_line,
    format_scenario_line,
)
from personal_enigma.evaluation.life_scripts.schema import SMELL_EXPECT_KEYS

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
JAN19 = SCRIPTS / "alex_jan19_morning.script.yaml"
SANITY = SCRIPTS / "alex_conversational_sanity.script.yaml"
FOCUS = SCRIPTS / "alex_jan19_focus_vs_radar.script.yaml"
WEEK = SCRIPTS / "alex_jan19_week_grounding.script.yaml"
WHEN = SCRIPTS / "alex_jan19_when_should_i.script.yaml"
LIFECYCLE = SCRIPTS / "alex_jan19_assist_lifecycle.script.yaml"
SPEECH = SCRIPTS / "alex_jan19_speech_acts.script.yaml"
ATTEST = SCRIPTS / "alex_jan19_user_attestation.script.yaml"
SUPPORT = SCRIPTS / "alex_jan19_support_funnel.script.yaml"
WHATSAPP = SCRIPTS / "alex_jan20_whatsapp.script.yaml"

# Live Fireworks invented this shape from referent_candidates with no tool.
INVENTED_WEEK_ANSWER = """
Here's what's on this week:

| Item | When | Notes |
| Brunch with Elena's parents | Saturday — you'll host | venue, menu, guest list still open |
| Draft colour + spacing token inventory | finish mid-week | |
| Atlas proposal review | best tackled early in the week to give the proposer time | |

These context items are scheduled for the week.
"""


def test_script_path_resolves_by_name() -> None:
    assert resolve_script_path("alex_jan19_morning") == JAN19.resolve()
    assert resolve_script_path("alex_conversational_sanity") == SANITY.resolve()
    assert resolve_script_path("alex_jan19_focus_vs_radar") == FOCUS.resolve()
    assert resolve_script_path("alex_jan19_week_grounding") == WEEK.resolve()
    assert resolve_script_path("alex_jan19_when_should_i") == WHEN.resolve()
    assert resolve_script_path("alex_jan19_assist_lifecycle") == LIFECYCLE.resolve()
    assert resolve_script_path("alex_jan19_speech_acts") == SPEECH.resolve()
    assert resolve_script_path("alex_jan19_user_attestation") == ATTEST.resolve()
    assert resolve_script_path("alex_jan19_support_funnel") == SUPPORT.resolve()
    assert resolve_script_path("alex_jan20_whatsapp") == WHATSAPP.resolve()


def test_jan19_script_speaks_like_alex() -> None:
    script = load_life_script(JAN19)
    users = [step.user for step in script.turns if step.user]
    assert users[0] == "Morning. What's actually worth worrying about today?"
    assert "Can't be bothered." in users
    assert "What's Elena's favourite restaurant?" in users
    assert any(step.clock for step in script.turns)
    assert any(step.world_event is not None for step in script.turns)
    assert any(step.inject is not None for step in script.turns)


def test_jan19_script_has_no_internal_smell_keys() -> None:
    raw = JAN19.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw


def test_loader_rejects_router_intent_smell(tmp_path: Path) -> None:
    path = tmp_path / "smelly.script.yaml"
    path.write_text(
        "\n".join(
            [
                "scenario: smell",
                "clock: 2026-01-19T10:00:00",
                "purpose: x",
                "pass_rule: x",
                "turns:",
                '  - user: "Nah, can\'t be arsed. Anything else?"',
                "    expect:",
                "      router_intent: GET_ALTERNATIVE_NEXT_ACTION",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(LifeScriptError, match="must not encode router/orchestrator internals"):
        load_life_script(path)


def test_failure_output_is_readable_without_pytest() -> None:
    result = TurnResult(
        kind="user",
        label="Nah, can't be arsed. Anything else?",
        user="Nah, can't be arsed. Anything else?",
        clock_label="10:07",
        checks=[
            Check("no world mutation", "no world mutation", "no world mutation", True),
            Check(
                "exclude TOKEN_AUDIT",
                "exclude TOKEN_AUDIT",
                "TOKEN_AUDIT returned again",
                False,
            ),
            Check(
                "return alternative",
                "return alternative",
                "subject remained TOKEN_AUDIT",
                False,
            ),
        ],
        fail_summary=(
            "conversational rejection was understood,\n      but exclusion was not propagated."
        ),
        v1="live",
    )
    text = format_turn_failure(result)
    assert text.startswith("ALEX 10:07")
    assert '"Nah, can\'t be arsed. Anything else?"' in text
    assert "Expected" in text
    assert "Observed" in text
    assert "✗ TOKEN_AUDIT returned again" in text
    assert "FAIL: conversational rejection was understood," in text
    assert "item-foo" not in text
    assert "AssertionError" not in text


def test_alex_jan19_morning_deterministic() -> None:
    report = run_life_script(JAN19, mode="deterministic")
    skipped = [row for row in report.turns if row.kind == "skipped"]
    reasons = " ".join(row.skipped_reason or "" for row in skipped)
    assert "assist.explain" in reasons
    assert "attention.can_wait" in reasons
    assert len(skipped) == 2
    assert any(row.kind == "clock" for row in report.turns)
    assert report.ok, report.transcript
    assert "Scenario: 15/15 active turns passed · 2 deferred" in report.transcript
    assert "Mode: deterministic" in report.transcript
    assert "live turns passed" not in report.transcript
    assert "Life Script · alex_jan19_morning ·" not in report.transcript


def test_transcript_live_mode_names_fireworks_separately() -> None:
    script = load_life_script(JAN19)
    report = EpisodeReport(
        script=script,
        mode="live",
        turns=[],
        transcript="",
        provider="Fireworks",
    )
    assert format_scenario_line(report) == "Scenario: 0/0 active turns passed · 0 deferred"
    assert format_mode_line(report) == "Mode: live · Fireworks"
    text = format_episode_transcript(report)
    assert "Mode: live · Fireworks" in text
    assert "Mode: deterministic" not in text


def test_conversational_sanity_script_is_the_torture_transcript() -> None:
    script = load_life_script(SANITY)
    users = [step.user for step in script.turns if step.user]
    assert users == [
        "Hey! Hows my week looking?",
        "Whats on for today?",
        "Urgent?",
        "Anything important in my emails?",
        "wait",
        "what",
        ":)",
        "whats the colour of the sky",
        "What do I have on today?",
    ]
    raw = SANITY.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw


def _turn(report: EpisodeReport, user: str) -> TurnResult:
    return next(row for row in report.turns if row.user == user)


def test_generic_acknowledgement_is_not_an_answer() -> None:
    assert _is_generic_acknowledgement("Okay.")
    assert _is_generic_acknowledgement("ok")
    assert not _is_generic_acknowledgement("Usually blue, depending on the weather.")
    ok, _ = _response_meaning_passed("answers_general_question", blob="okay.", names=[])
    assert not ok
    ok, _ = _response_meaning_passed(
        "answers_general_question",
        blob="usually blue depending on the weather",
        names=[],
    )
    assert ok
    ok, _ = _response_meaning_passed("acknowledgement", blob="okay.", names=[])
    assert ok
    ok, _ = _response_meaning_passed("confusion_or_clarification", blob="okay.", names=[])
    assert not ok
    ok, _ = _response_meaning_passed(
        "confusion_or_clarification", blob="sorry — what did you mean?", names=[]
    )
    assert ok


def test_alex_conversational_sanity_exposes_okay_as_not_understanding() -> None:
    report = run_life_script(SANITY, mode="deterministic")
    skipped = [row for row in report.turns if row.kind == "skipped"]
    assert len(skipped) == 1
    assert "source_scope" in (skipped[0].skipped_reason or "")
    assert _turn(report, "Hey! Hows my week looking?").passed
    assert _turn(report, "Whats on for today?").passed
    assert _turn(report, "Urgent?").passed
    assert _turn(report, "wait").passed
    assert _turn(report, ":)").passed
    assert _turn(report, "What do I have on today?").passed
    what = _turn(report, "what")
    sky = _turn(report, "whats the colour of the sky")
    assert not what.passed
    assert not sky.passed
    assert "not falling back is not the same as understanding." in (what.fail_summary or "")
    assert "not falling back is not the same as understanding." in (sky.fail_summary or "")
    assert not report.ok
    unknown = [
        row
        for row in report.turns
        if any("i'm not sure i follow" in line.lower() for line in row.enigma_lines)
    ]
    assert unknown == []


def _c09_live_enabled() -> bool:
    flag = os.environ.get("ENIGMA_C09_LIVE", "").lower() in ("1", "true", "yes")
    return flag and bool(os.environ.get("FIREWORKS_API_KEY"))


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live Life Script proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_alex_jan19_morning_live() -> None:
    report = run_life_script(JAN19, mode="live")
    assert report.ok, report.transcript


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live Life Script proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_alex_conversational_sanity_live() -> None:
    report = run_life_script(SANITY, mode="live")
    assert report.ok, report.transcript


def test_deterministic_planner_does_not_import_phrase_maps() -> None:
    from personal_enigma.evaluation.life_scripts.runner import DeterministicLifeScriptLLM

    names = DeterministicLifeScriptLLM.select_tools.__code__.co_names
    assert "tool_calls_from_intent" not in names
    assert "IntentOracleLLM" not in names


def test_focus_vs_radar_script_speaks_like_alex() -> None:
    script = load_life_script(FOCUS)
    users = [step.user for step in script.turns if step.user]
    assert users == [
        "What is urgent right now?",
        "this week?",
        "what about the week after?",
        "What is the draft colour?",
        "Can you help me do that?",
        "Can you help me do the token inventory",
        "Can you help me do the design tokens",
        "Go on then.",
        "help!",
        "heeeelllppp!!",
    ]
    events = [step.event for step in script.turns if step.event]
    assert events == ["assist_verified"]
    assert any(step.v1 == "deferred" and step.event == "assist_verified" for step in script.turns)
    raw = FOCUS.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw
    assert "preserve_subject:" in raw
    assert "secondary_items_may_include:" in raw
    assert "assist_target:" in raw
    assert "attributed_to_original_assist:" in raw


def test_loader_accepts_focus_public_effect_keys() -> None:
    script = load_life_script(FOCUS)
    horizon = next(step for step in script.turns if step.user == "this week?")
    assert horizon.expect is not None
    assert horizon.expect.preserve_subject == "TOKEN_AUDIT"
    assert horizon.expect.secondary_items_may_include == "BRUNCH"
    named = next(
        step for step in script.turns if step.user == "Can you help me do the token inventory"
    )
    assert named.expect is not None
    assert named.expect.assist_target == "TOKEN_AUDIT"
    assert named.expect.current_subject_id == "TOKEN_AUDIT"
    retarget = next(
        step for step in script.turns if step.user == "Can you help me do the design tokens"
    )
    assert retarget.inject is not None
    assert retarget.inject.wrong_subject_id == "BRUNCH"
    assert retarget.expect is not None
    assert retarget.expect.assist_target == "TOKEN_AUDIT"
    delayed = next(step for step in script.turns if step.event == "assist_verified")
    assert delayed.v1 == "deferred"
    assert delayed.expect is not None
    assert delayed.expect.attributed_to_original_assist == "BRUNCH"
    assert delayed.response is not None
    assert "appear_as_reply_to_current_user_turn" in delayed.response.must_not


def test_alex_jan19_focus_vs_radar_deterministic() -> None:
    report = run_life_script(FOCUS, mode="deterministic")
    skipped = [row for row in report.turns if row.kind == "skipped"]
    assert len(skipped) == 1
    assert skipped[0].label == "event: assist_verified"
    reason = (skipped[0].skipped_reason or "").lower()
    assert "asynchronous assist" in reason
    assert _turn(report, "What is urgent right now?").passed
    assert _turn(report, "this week?").passed
    this_week = _turn(report, "this week?")
    names = {row.name: row for row in this_week.checks}
    assert names["preserve_subject"].passed
    assert names["secondary_items_may_include"].passed
    assert names["secondary_items"].passed
    assert _turn(report, "what about the week after?").passed
    assert _turn(report, "What is the draft colour?").passed
    that = _turn(report, "Can you help me do that?")
    assert that.passed
    assert any(row.name == "assist_target" and row.passed for row in that.checks)
    named = _turn(report, "Can you help me do the token inventory")
    assert named.passed
    assert any(row.name == "assist_target" and row.passed for row in named.checks)
    retarget = _turn(report, "Can you help me do the design tokens")
    assert retarget.passed, report.transcript
    assert any(row.name == "assist_target" and row.passed for row in retarget.checks)
    approve = _turn(report, "Go on then.")
    assert approve.passed, report.transcript
    help_turn = _turn(report, "help!")
    assert help_turn.passed
    assert any(row.name == "no tool" and row.passed for row in help_turn.checks)
    yell = _turn(report, "heeeelllppp!!")
    assert yell.passed
    assert any(row.name == "no tool" and row.passed for row in yell.checks)
    assert report.ok, report.transcript
    assert "Scenario: 10/10 active turns passed · 1 deferred" in report.transcript
    assert "Mode: deterministic" in report.transcript


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live Life Script proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_alex_jan19_focus_vs_radar_live() -> None:
    report = run_life_script(FOCUS, mode="live")
    skipped = [row for row in report.turns if row.kind == "skipped"]
    assert len(skipped) == 1
    assert skipped[0].label == "event: assist_verified"
    assert report.ok, report.transcript


def test_week_grounding_script_speaks_like_alex() -> None:
    script = load_life_script(WEEK)
    users = [step.user for step in script.turns if step.user]
    assert users == ["Whats on this week?"]
    step = script.turns[0]
    assert step.expect is not None
    assert step.expect.meaning == "week_overview"
    assert step.expect.tool == "agenda.get"
    assert step.expect.tool_required is True
    assert step.expect.grounded_world_response is True
    assert step.response is not None
    assert "infer_unsourced_task_details" in step.response.must_not
    assert "invent_deadline" in step.response.must_not
    assert "invent_recommendation_strength" in step.response.must_not
    assert "treat_context_as_calendar" in step.response.must_not
    raw = WEEK.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw


def _empty_world() -> WorldSnapshot:
    return WorldSnapshot(
        checkpoint_id="cp-2026-01-19T10:00",
        completed=frozenset(),
        calendar_ids=frozenset(),
        note_ids=frozenset(),
    )


def test_invented_week_answer_fails_must_not_flags() -> None:
    blob = INVENTED_WEEK_ANSWER.lower()
    session = cast(Any, type("S", (), {"conversation_context": "", "conversation": []})())
    empty = _empty_world()
    flags = (
        "infer_unsourced_task_details",
        "invent_deadline",
        "invent_recommendation_strength",
        "treat_context_as_calendar",
    )
    for flag in flags:
        ok, observed = _must_not_passed(
            flag,
            items=[],
            blob=blob,
            names=[],
            session=session,
            before=empty,
            after=empty,
            subject=None,
        )
        assert not ok, f"{flag} should fail on invented week prose ({observed})"


def test_grounded_week_agenda_copy_passes_must_not_flags() -> None:
    blob = (
        "nothing needs you this week as an interrupt. "
        "strong next action: draft colour + spacing token inventory. "
        "on radar this week: book brunch with elena's parents. "
        "calendar: wednesday has token inventory review, 14:00–15:00; "
        "thursday has team standup, 09:00–09:15; "
        "saturday has brunch with elena's parents, 11:00–13:00."
    )
    session = cast(Any, type("S", (), {"conversation_context": "", "conversation": []})())
    empty = _empty_world()
    for flag in (
        "infer_unsourced_task_details",
        "invent_deadline",
        "invent_recommendation_strength",
        "treat_context_as_calendar",
    ):
        ok, observed = _must_not_passed(
            flag,
            items=[],
            blob=blob,
            names=["agenda.get"],
            session=session,
            before=empty,
            after=empty,
            subject=None,
        )
        assert ok, f"{flag} false-positive on grounded agenda copy ({observed})"


def test_alex_jan19_week_grounding_deterministic() -> None:
    report = run_life_script(WEEK, mode="deterministic")
    turn = _turn(report, "Whats on this week?")
    assert turn.passed, report.transcript
    names = {row.name: row for row in turn.checks}
    assert names["agenda.get"].passed
    assert names["meaning · week_overview"].passed
    assert names["tool_required"].passed
    assert names["grounded_world_response"].passed
    assert names["must_not · infer_unsourced_task_details"].passed
    assert names["must_not · invent_deadline"].passed
    assert names["must_not · invent_recommendation_strength"].passed
    assert names["must_not · treat_context_as_calendar"].passed
    assert report.ok, report.transcript
    assert "Scenario: 1/1 active turns passed · 0 deferred" in report.transcript


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live Life Script proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_alex_jan19_week_grounding_live() -> None:
    report = run_life_script(WEEK, mode="live")
    assert report.ok, report.transcript


def test_assist_lifecycle_script_speaks_like_alex() -> None:
    script = load_life_script(LIFECYCLE)
    users = [step.user for step in script.turns if step.user]
    assert users == [
        "Alright, what's a good thing to get done then?",
        "Can you help me do the token inventory?",
        "Go on then.",
        "So what should I do next?",
    ]
    raw = LIFECYCLE.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw
    follow = next(step for step in script.turns if step.user == "So what should I do next?")
    assert follow.response is not None
    assert "nothing_worth_doing" in follow.response.must_not
    assert "invent_empty_universe" in follow.response.must_not
    assert "mark_cancelled_or_complete" in follow.response.must_not


def test_nothing_worth_doing_must_not_flags() -> None:
    session = cast(Any, type("S", (), {"conversation_context": "", "conversation": []})())
    empty = _empty_world()
    ok, _ = _must_not_passed(
        "nothing_worth_doing",
        items=[],
        blob="nothing worth doing right now.",
        names=["next_action.get"],
        session=session,
        before=empty,
        after=empty,
        subject=None,
    )
    assert not ok
    ok, _ = _must_not_passed(
        "invent_empty_universe",
        items=[],
        blob="nothing worth doing right now.",
        names=["next_action.get"],
        session=session,
        before=empty,
        after=empty,
        subject=None,
    )
    assert not ok
    preferred = "nothing stands out as a strong next action."
    ok, _ = _must_not_passed(
        "nothing_worth_doing",
        items=[],
        blob=preferred,
        names=["next_action.get"],
        session=session,
        before=empty,
        after=empty,
        subject=None,
    )
    assert ok
    ok, _ = _must_not_passed(
        "invent_empty_universe",
        items=[],
        blob=preferred,
        names=["next_action.get"],
        session=session,
        before=empty,
        after=empty,
        subject=None,
    )
    assert ok


def test_alex_jan19_assist_lifecycle_deterministic() -> None:
    report = run_life_script(LIFECYCLE, mode="deterministic")
    assert _turn(report, "Alright, what's a good thing to get done then?").passed
    assert _turn(report, "Can you help me do the token inventory?").passed
    approve = _turn(report, "Go on then.")
    assert approve.passed, report.transcript
    follow = _turn(report, "So what should I do next?")
    assert follow.passed, report.transcript
    names = {row.name: row for row in follow.checks}
    assert names["must_not · mark_cancelled_or_complete"].passed
    assert names["must_not · nothing_worth_doing"].passed
    assert names["must_not · invent_empty_universe"].passed
    assert report.ok, report.transcript


FORENSIC_DUMP_USERS = [
    "Can I see the Draft Colour?",
    "Lets see it",
    "yes",
    "What would you recommend?",
    "yes but how",
    "What should I get the parents?",
    "No, the parents im meeting saturday",
    "What should I get them",
    "I think the mum like susho",
    "yes sushi",
    "yes but what place?",
    "Sushi places",
    "we will be in Shoreditch",
    "what sushi places are there in shoreditch",
]


def test_speech_acts_script_uses_exact_dump_utterances() -> None:
    script = load_life_script(SPEECH)
    users = [step.user for step in script.turns if step.user]
    assert users == FORENSIC_DUMP_USERS
    raw = SPEECH.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw
    deferred = [step.user for step in script.turns if step.v1 == "deferred"]
    assert deferred == [
        "Can I see the Draft Colour?",
        "What would you recommend?",
        "Sushi places",
        "what sushi places are there in shoreditch",
    ]
    yes = next(step for step in script.turns if step.user == "yes")
    assert yes.response is not None
    assert "upgrade_consent_to_approve" in yes.response.must_not
    correction = next(
        step for step in script.turns if step.user == "No, the parents im meeting saturday"
    )
    assert correction.expect is not None
    assert correction.expect.current_subject_id == "BRUNCH"
    assert correction.response is not None
    assert "resolve_referent_as_action" in correction.response.must_not
    shoreditch = next(step for step in script.turns if step.user == "we will be in Shoreditch")
    assert shoreditch.response is not None
    assert "persist_turn_local_as_memory" in shoreditch.response.must_not
    assert "resolve_referent_as_action" in shoreditch.response.must_not


def test_invent_external_venues_must_not_flag() -> None:
    session = cast(Any, type("S", (), {"conversation_context": "", "conversation": []})())
    empty = _empty_world()
    invented = (
        "here are a few sushi places in shoreditch | name | address | price |\n"
        "| koi | 12 rivington street | ££ | 0.4 miles |"
    )
    ok, _ = _must_not_passed(
        "invent_external_venues",
        items=[],
        blob=invented,
        names=[],
        session=session,
        before=empty,
        after=empty,
        subject=None,
    )
    assert not ok
    ok, _ = _must_not_passed(
        "invent_external_venues",
        items=[],
        blob="i don't have a location saved.",
        names=[],
        session=session,
        before=empty,
        after=empty,
        subject=None,
    )
    assert ok


def test_alex_jan19_speech_acts_deterministic() -> None:
    report = run_life_script(SPEECH, mode="deterministic")
    skipped = [row for row in report.turns if row.kind == "skipped"]
    assert len(skipped) == 4
    reasons = " ".join(row.skipped_reason or "" for row in skipped)
    assert "artifact.inspect" in reasons
    assert "world.advise" in reasons
    assert "places.search" in reasons
    assert _turn(report, "Lets see it").passed
    yes = _turn(report, "yes")
    assert yes.passed, report.transcript
    assert any(
        row.name == "must_not · upgrade_consent_to_approve" and row.passed
        for row in yes.checks
    )
    correction = _turn(report, "No, the parents im meeting saturday")
    assert correction.passed, report.transcript
    assert any(row.name == "subject" and row.passed for row in correction.checks)
    assert any(
        row.name == "must_not · resolve_referent_as_action" and row.passed
        for row in correction.checks
    )
    place = _turn(report, "yes but what place?")
    assert place.passed, report.transcript
    shoreditch = _turn(report, "we will be in Shoreditch")
    assert shoreditch.passed, report.transcript
    assert any(
        row.name == "must_not · persist_turn_local_as_memory" and row.passed
        for row in shoreditch.checks
    )
    assert report.ok, report.transcript
    assert "Scenario: 10/10 active turns passed · 4 deferred" in report.transcript


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live Life Script proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_alex_jan19_speech_acts_live() -> None:
    report = run_life_script(SPEECH, mode="live")
    skipped = [row for row in report.turns if row.kind == "skipped"]
    assert len(skipped) == 4
    assert report.ok, report.transcript


def test_when_should_i_script_speaks_like_alex() -> None:
    script = load_life_script(WHEN)
    users = [step.user for step in script.turns if step.user]
    assert users == [
        "What's on next week?",
        "Not the dinner with my girlfriend's parents?",
        "Check my calendar for the dinner.",
        "Saturday? I think?",
        "When should I do it?",
        "Like... now?",
        "Are you sure there's nothing more important?",
    ]
    raw = WHEN.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw
    first = script.turns[0]
    assert first.expect is not None
    assert first.expect.tool == "agenda.get"
    assert first.expect.current_subject_id is None
    assert first.expect.preserve_subject is True
    when = next(step for step in script.turns if step.user == "When should I do it?")
    assert when.expect is not None
    assert when.expect.tools == ["referent.get_duration", "availability.check"]
    assert when.response is not None
    assert "duration_as_when_answer" in when.response.must_not
    assert "stop_after_intermediate_fact" in when.response.must_not
    saturday = next(step for step in script.turns if step.user == "Saturday? I think?")
    assert saturday.response is not None
    assert "duration_as_when_answer" in saturday.response.must_not
    sure = next(
        step
        for step in script.turns
        if step.user == "Are you sure there's nothing more important?"
    )
    assert sure.expect is not None
    assert sure.expect.tool == "attention.get_current"


def test_alex_jan19_when_should_i_deterministic() -> None:
    report = run_life_script(WHEN, mode="deterministic")
    empty = _turn(report, "What's on next week?")
    assert empty.passed, report.transcript
    names = {row.name: row for row in empty.checks}
    assert names["agenda.get"].passed
    assert names["preserve_subject"].passed
    assert names["subject"].passed
    assert names["exclude BRUNCH"].passed
    correction = _turn(report, "Not the dinner with my girlfriend's parents?")
    assert correction.passed, report.transcript
    when = _turn(report, "When should I do it?")
    assert when.passed, report.transcript
    assert any(row.name == "capabilities" and row.passed for row in when.checks)
    assert any(
        row.name == "must_not · duration_as_when_answer" and row.passed
        for row in when.checks
    )
    now = _turn(report, "Like... now?")
    assert now.passed, report.transcript
    sure = _turn(report, "Are you sure there's nothing more important?")
    assert sure.passed, report.transcript
    assert report.ok, report.transcript
    assert "Scenario: 7/7 active turns passed · 0 deferred" in report.transcript


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live Life Script proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_alex_jan19_when_should_i_live() -> None:
    report = run_life_script(WHEN, mode="live")
    assert report.ok, report.transcript


def test_alex_jan20_whatsapp_script_speaks_like_alex() -> None:
    script = load_life_script(WHATSAPP)
    users = [step.user for step in script.turns if step.user]
    assert users == [
        "Did Elena say whether her parents are definitely coming?",
        "Do I need to sort anything because of that?",
        "What exactly did she say?",
    ]
    raw = WHATSAPP.read_text(encoding="utf-8")
    for key in SMELL_EXPECT_KEYS:
        assert f"{key}:" not in raw


def test_alex_jan20_whatsapp_deterministic() -> None:
    report = run_life_script(WHATSAPP, mode="deterministic")
    assert not [row for row in report.turns if row.kind == "skipped"]
    assert report.ok, report.transcript
    assert "Scenario: 3/3 active turns passed" in report.transcript
    quote = _turn(report, "What exactly did she say?")
    assert any(row.name == "source.quote" and row.passed for row in quote.checks)
    fact = _turn(report, "Did Elena say whether her parents are definitely coming?")
    assert any(row.name == "meaning · parents_confirmed" and row.passed for row in fact.checks)
    assert any(row.name == "must_not · verbatim_chat_body" and row.passed for row in fact.checks)




