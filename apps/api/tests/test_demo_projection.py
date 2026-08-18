"""Demo conversational projection API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.demo_assist import (
    AssistPlan,
    SyntheticDemoServices,
    execute_and_verify,
)
from personal_enigma.api.demo_intents import build_next_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.attention.projection import (
    AttentionItemView,
    AttentionState,
    PresentationPlan,
)

TOKEN_ID = "item-obligation_token_audit"
BRUNCH_ID = "item-obligation_brunch_book"
ATLAS_ID = "item-obligation_atlas_review"
SAM_TITLE = "Reply to Sam on empty-state decision"
JAN19 = "cp-2026-01-19T10:00"
JAN20 = "cp-2026-01-20T11:00"


def _ids_for_kind(turn: dict, kind: str, key: str) -> set[str]:
    return {item[key]["id"] for item in turn["items"] if item["kind"] == kind}


def _titles_in_turn(turn: dict) -> set[str]:
    titles: set[str] = set()
    for item in turn["items"]:
        if item["kind"] == "attention_item":
            titles.add(item["item"]["title"])
        elif item["kind"] == "next_action":
            titles.add(item["action"]["title"])
        elif item["kind"] == "enigma_message":
            titles.add(item["text"])
        elif item["kind"] == "attention_summary":
            titles.update(row["title"] for row in item["state"]["needs_you"])
            titles.update(row["title"] for row in item["state"]["context"])
            titles.update(row["title"] for row in item["state"]["next_actions"])
    return titles


def _ask(client: TestClient, text: str) -> dict:
    return client.post("/demo/conversation/message", json={"text": text}).json()


@pytest.fixture
def demo_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    return TestClient(create_app())


def test_attention_state_jan19_milestone(demo_client: TestClient) -> None:
    body = demo_client.get("/demo/attention/state").json()
    assert body["checkpoint_id"] == "cp-2026-01-19T10:00"
    assert body["needs_you"] == []
    context_ids = {row["id"] for row in body["context"]}
    assert "item-obligation_token_audit" in context_ids
    assert body["presentation"]["proactive_silence"] is True
    assert body["next_actions"]


def test_checkpoint_jump_jan20(demo_client: TestClient) -> None:
    jumped = demo_client.post("/demo/timeline/checkpoint/cp-2026-01-20T11:00").json()
    assert jumped["checkpoint_id"] == "cp-2026-01-20T11:00"
    state = jumped["attention"]
    needs = {row["id"] for row in state["needs_you"]}
    assert "item-obligation_brunch_book" in needs
    assert "item-obligation_token_audit" not in needs


def test_qualification_debug_token_jan20(demo_client: TestClient) -> None:
    demo_client.post("/demo/timeline/checkpoint/cp-2026-01-20T11:00")
    debug = demo_client.get(
        "/demo/attention/item-obligation_token_audit/qualification-debug"
    ).json()
    assert debug["policy_decision"] == "context"
    assert debug["actionability_now"] == 0.9
    assert debug["composite_score"] < debug["surface_threshold"]


def test_proactive_silence_does_not_append_conversation_item(
    demo_client: TestClient,
) -> None:
    before = demo_client.get("/demo/conversation").json()["items"]
    demo_client.post("/demo/timeline/checkpoint/cp-2026-01-19T10:00")
    after = demo_client.get("/demo/conversation").json()["items"]
    assert len(after) == len(before)
    events = demo_client.get("/demo/events").json()["events"]
    assert any(event["kind"] == "proactive_silence" for event in events)


def test_what_needs_me_jan19_single_summary_turn(demo_client: TestClient) -> None:
    turn = demo_client.post(
        "/demo/conversation/message",
        json={"text": "What needs me?"},
    ).json()
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"attention_summary"}
    summary = next(item for item in turn["items"] if item["kind"] == "attention_summary")
    context_ids = {row["id"] for row in summary["state"]["context"]}
    assert "item-obligation_token_audit" in context_ids
    assert summary["state"]["next_actions"]


def test_what_needs_me_intent(demo_client: TestClient) -> None:
    demo_client.post("/demo/timeline/checkpoint/cp-2026-01-20T11:00")
    turn = demo_client.post(
        "/demo/conversation/message",
        json={"text": "What needs me?"},
    ).json()
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"attention_summary"}
    summary = next(item for item in turn["items"] if item["kind"] == "attention_summary")
    assert summary["state"]["needs_you"]
    assert {row["id"] for row in summary["state"]["needs_you"]} == {BRUNCH_ID}


def test_why_jan19_uses_context_not_transcript(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Why?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"attention_item"}
    item = turn["items"][0]["item"]
    assert item["id"] == BRUNCH_ID
    assert item["bucket"] == "context"


def test_why_jan20_explains_needs_you(demo_client: TestClient) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    turn = _ask(demo_client, "Why?")
    assert {item["kind"] for item in turn["items"]} == {"attention_item"}
    item = turn["items"][0]["item"]
    assert item["id"] == BRUNCH_ID
    assert item["bucket"] == "needs_you"


def test_what_changed_jan19_world_just_loaded(demo_client: TestClient) -> None:
    assert demo_client.get("/demo/status").json()["checkpoint_id"] == JAN19
    turn = _ask(demo_client, "What changed?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"enigma_message"}
    assert "just loaded" in turn["items"][0]["text"].lower()
    assert "next_action" not in kinds
    assert "attention_item" not in kinds
    assert "attention_summary" not in kinds


def test_what_changed_jan20_brunch_only(demo_client: TestClient) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    turn = _ask(demo_client, "What changed?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"attention_item"}
    assert _ids_for_kind(turn, "attention_item", "item") == {BRUNCH_ID}
    assert turn["items"][0]["item"]["bucket"] == "needs_you"
    assert TOKEN_ID not in _ids_for_kind(turn, "next_action", "action")
    assert TOKEN_ID not in _ids_for_kind(turn, "attention_item", "item")
    assert "attention_summary" not in kinds


def test_waiting_on_jan19_excludes_next_action(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "What am I waiting on?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"attention_item"}
    ids = _ids_for_kind(turn, "attention_item", "item")
    assert TOKEN_ID not in ids
    assert BRUNCH_ID in ids
    assert ATLAS_ID in ids
    assert all(item["item"]["bucket"] == "context" for item in turn["items"])
    assert "next_action" not in kinds
    assert SAM_TITLE not in " ".join(_titles_in_turn(turn))


def test_waiting_on_jan20_excludes_needs_you_and_next_action(
    demo_client: TestClient,
) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    turn = _ask(demo_client, "What am I waiting on?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"attention_item"}
    ids = _ids_for_kind(turn, "attention_item", "item")
    assert ids == {ATLAS_ID}
    assert BRUNCH_ID not in ids
    assert TOKEN_ID not in ids
    assert "next_action" not in kinds
    assert "attention_summary" not in kinds


def test_can_wait_jan19_reassurance_not_next_action(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "What can wait?")
    kinds = {item["kind"] for item in turn["items"]}
    assert "next_action" not in kinds
    assert "attention_summary" not in kinds
    ids = _ids_for_kind(turn, "attention_item", "item")
    assert TOKEN_ID not in ids
    assert BRUNCH_ID in ids
    assert ATLAS_ID in ids
    texts = " ".join(
        item["text"] for item in turn["items"] if item["kind"] == "enigma_message"
    )
    assert SAM_TITLE in texts


def test_can_wait_jan20_excludes_brunch_needs_you(demo_client: TestClient) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    turn = _ask(demo_client, "What can wait?")
    kinds = {item["kind"] for item in turn["items"]}
    assert "next_action" not in kinds
    assert "attention_summary" not in kinds
    ids = _ids_for_kind(turn, "attention_item", "item")
    assert BRUNCH_ID not in ids
    assert TOKEN_ID not in ids
    assert ATLAS_ID in ids
    texts = " ".join(
        item["text"] for item in turn["items"] if item["kind"] == "enigma_message"
    )
    assert SAM_TITLE in texts


def test_what_should_i_do_next_jan19_support_layer_only(
    demo_client: TestClient,
) -> None:
    turn = _ask(demo_client, "What should I do next?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"next_action"}
    actions = [item["action"] for item in turn["items"]]
    assert {row["source_candidate_id"] for row in actions} == {TOKEN_ID}
    assert all(row["reason"] == "Unblocked now" for row in actions)
    assert BRUNCH_ID not in _ids_for_kind(turn, "attention_item", "item")


def test_what_should_i_do_next_jan20_not_highest_attention(
    demo_client: TestClient,
) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    turn = _ask(demo_client, "What should I do next?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"next_action"}
    actions = [item["action"] for item in turn["items"]]
    assert {row["source_candidate_id"] for row in actions} == {TOKEN_ID}
    assert BRUNCH_ID not in _ids_for_kind(turn, "attention_item", "item")
    assert "attention_summary" not in kinds


def test_next_intent_does_not_fall_back_to_needs_you() -> None:
    brunch = AttentionItemView(
        id=BRUNCH_ID,
        title="Book Saturday brunch for Elena's parents",
        explanation="Needs you.",
        policy_decision="surface",
        bucket="needs_you",
    )
    state = AttentionState(
        simulated_time="2026-01-20T11:00:00+00:00",
        checkpoint_id=JAN20,
        needs_you=[brunch],
        context=[],
        next_actions=[],
        presentation=PresentationPlan(chat_opening_count=1),
    )
    turn = build_next_turn(state, at=state.simulated_time)
    assert {item["kind"] for item in turn} == {"enigma_message"}
    text = turn[0]["text"].lower()
    assert "nothing worth doing" not in text
    assert "strong next action" in text
    assert BRUNCH_ID not in str(turn)


def test_jan19_help_me_do_that_proposes_token_not_brunch(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Can you help me do that?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"assist_proposal"}
    proposal = turn["items"][0]["proposal"]
    assert "token" in proposal["title"].lower()
    assert "brunch" not in proposal["title"].lower()
    assert proposal["action_label"] == "Approve"
    conversation = demo_client.get("/demo/conversation").json()["items"]
    assert not any(item["kind"] == "assist_result" for item in conversation)


def test_jan19_approve_token_assist_overlay_and_result(demo_client: TestClient) -> None:
    """Draft Assist ADVANCES TOKEN — does not SATISFY the obligation."""
    _ask(demo_client, "What should I do next?")
    propose = _ask(demo_client, "Help me do this")
    assert propose["items"][0]["kind"] == "assist_proposal"
    proposal_id = propose["items"][0]["proposal"]["id"]
    result = demo_client.post(f"/demo/assist/{proposal_id}/approve").json()
    assert result["ok"] is True
    assert result["kind"] == "assist_result"
    assert "draft" in result["message"].lower()
    conversation = demo_client.get("/demo/conversation").json()["items"]
    assert any(item["kind"] == "assist_result" and item["ok"] for item in conversation)
    live = demo_client.get("/demo/attention/state").json()
    assert TOKEN_ID in {row["id"] for row in live["context"]}
    assert TOKEN_ID in {
        row["source_candidate_id"] for row in live["next_actions"] if row["source_candidate_id"]
    }
    assert any("review" in row["title"].lower() for row in live["next_actions"])
    frozen = project_checkpoint(JAN19).state
    assert TOKEN_ID in {row.id for row in frozen.context}
    after = _ask(demo_client, "What should I do next?")
    blob = str(after).lower()
    assert "nothing worth doing" not in blob


def test_jan20_help_me_do_that_proposes_brunch_not_auto_approved(
    demo_client: TestClient,
) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    needs = _ask(demo_client, "What needs me?")
    assert {row["id"] for row in needs["items"][0]["state"]["needs_you"]} == {BRUNCH_ID}
    turn = _ask(demo_client, "Can you help me do that?")
    kinds = {item["kind"] for item in turn["items"]}
    assert kinds == {"assist_proposal"}
    proposal = turn["items"][0]["proposal"]
    assert "brunch" in proposal["title"].lower()
    assert "token" not in proposal["title"].lower()
    conversation = demo_client.get("/demo/conversation").json()["items"]
    assert not any(item["kind"] == "assist_result" for item in conversation)


def test_jan20_approve_assist_executes_verifies_and_acknowledges(
    demo_client: TestClient,
) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    _ask(demo_client, "What needs me?")
    turn = _ask(demo_client, "Can you help me do that?")
    proposal_id = turn["items"][0]["proposal"]["id"]
    result = demo_client.post(f"/demo/assist/{proposal_id}/approve").json()
    assert result["ok"] is True
    assert result["kind"] == "assist_result"
    assert result["proposal_id"] == proposal_id
    assert "brunch" in result["message"].lower()
    assert "booked" in result["message"].lower()
    conversation = demo_client.get("/demo/conversation").json()["items"]
    acks = [
        item
        for item in conversation
        if item["kind"] == "assist_result" and item["ok"] is True
    ]
    assert acks
    assert "booked" in acks[-1]["message"].lower()
    frozen = project_checkpoint(JAN20).state
    assert BRUNCH_ID in {row.id for row in frozen.needs_you}
    live = demo_client.get("/demo/attention/state").json()
    assert BRUNCH_ID not in {row["id"] for row in live["needs_you"]}


def test_jan20_assist_six_exchange_loop(demo_client: TestClient) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    understand = _ask(demo_client, "What needs me?")
    assert {row["id"] for row in understand["items"][0]["state"]["needs_you"]} == {BRUNCH_ID}
    propose = _ask(demo_client, "Can you help me do that?")
    assert {item["kind"] for item in propose["items"]} == {"assist_proposal"}
    proposal_id = propose["items"][0]["proposal"]["id"]
    result = demo_client.post(f"/demo/assist/{proposal_id}/approve").json()
    assert result["ok"] is True
    after = _ask(demo_client, "What needs me?")
    summary = after["items"][0]["state"]
    assert BRUNCH_ID not in {row["id"] for row in summary["needs_you"]}
    conversation = demo_client.get("/demo/conversation").json()["items"]
    assert any(
        item["kind"] == "assist_result" and "booked" in item["message"].lower()
        for item in conversation
    )


def test_jan20_help_after_next_intent_proposes_token(demo_client: TestClient) -> None:
    demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    _ask(demo_client, "What should I do next?")
    turn = _ask(demo_client, "Help me do that")
    title = turn["items"][0]["proposal"]["title"].lower()
    assert "token" in title
    assert "brunch" not in title


def test_unknown_assist_approve_does_not_pretend_success(demo_client: TestClient) -> None:
    response = demo_client.post("/demo/assist/no-such/approve")
    assert response.status_code == 404
    conversation = demo_client.get("/demo/conversation").json()["items"]
    assert not any(item["kind"] == "assist_result" for item in conversation)


def test_verify_failure_does_not_claim_success() -> None:
    services = SyntheticDemoServices(fail_writes=True)
    plan = AssistPlan(
        proposal_id="assist-fail",
        title="Book Saturday brunch for Elena's parents",
        description="I'll book this on the synthetic demo calendar.",
        action_label="Approve",
        source_item_id=BRUNCH_ID,
        action_kind="calendar_book",
    )
    ok, message = execute_and_verify(plan, services)
    assert ok is False
    assert "couldn't verify" in message.lower()
    assert services.calendar_events == {}


def test_draft_assist_advances_token_brunch_satisfies() -> None:
    from personal_enigma.api.demo_assist import (
        apply_verified_assist_effect,
        assist_effect_for,
        overlay_session_world,
    )
    from personal_enigma.api.demo_projection import project_checkpoint

    draft = AssistPlan(
        proposal_id="assist-draft",
        title="Draft colour + spacing token inventory",
        description="I'll record a synthetic demo draft for this.",
        action_label="Approve",
        source_item_id=TOKEN_ID,
        action_kind="synthetic_note",
    )
    book = AssistPlan(
        proposal_id="assist-book",
        title="Book Saturday brunch for Elena's parents",
        description="I'll book this on the synthetic demo calendar.",
        action_label="Approve",
        source_item_id=BRUNCH_ID,
        action_kind="calendar_book",
    )
    assert assist_effect_for(draft) == "ADVANCES"
    assert assist_effect_for(book) == "SATISFIES"
    completed: set[str] = set()
    advances: dict = {}
    apply_verified_assist_effect(draft, completed_item_ids=completed, advances=advances)
    assert TOKEN_ID not in completed
    frozen = project_checkpoint(JAN19).state
    live = overlay_session_world(frozen, completed, advances)
    assert TOKEN_ID in {row.id for row in live.context}
    assert live.next_actions[0].title == "Review the draft"
    apply_verified_assist_effect(book, completed_item_ids=completed, advances=advances)
    assert BRUNCH_ID in completed


def test_greeting_returns_simple_copy(demo_client: TestClient) -> None:
    for text in ("hey", "hi", "hello", "Hey!", "Hello."):
        turn = _ask(demo_client, text)
        assert turn["items"][0]["text"] == "Hey. What's up?"


def test_whats_urgent_matches_attention_summary(demo_client: TestClient) -> None:
    canonical = _ask(demo_client, "What needs me?")
    natural = _ask(demo_client, "What's urgent?")
    assert {item["kind"] for item in natural["items"]} == {"attention_summary"}
    assert natural["items"][0]["state"] == canonical["items"][0]["state"]


def test_whats_next_matches_next_action(demo_client: TestClient) -> None:
    canonical = _ask(demo_client, "What should I do next?")
    natural = _ask(demo_client, "What's next?")
    assert {item["kind"] for item in natural["items"]} == {"next_action"}
    assert natural["items"][0]["action"] == canonical["items"][0]["action"]


def test_need_to_do_now_with_trailing_slash(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "What do i need to do now/")
    assert {item["kind"] for item in turn["items"]} == {"next_action"}
    assert turn["items"][0]["action"]["source_candidate_id"] == TOKEN_ID


def test_am_i_free_this_weekend_jan19(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Am I free this weekend?")
    assert {item["kind"] for item in turn["items"]} == {"enigma_message"}
    text = turn["items"][0]["text"].lower()
    assert "saturday" in text
    assert "brunch" in text
    assert "book saturday brunch" in text
    assert "i'm not sure i follow" not in text


@pytest.mark.parametrize(
    ("utterance", "period_fragment"),
    [
        ("Am I free later?", "later today"),
        ("Am I free this afternoon?", "this afternoon"),
        ("Am I free tomorrow?", "tomorrow"),
        ("am i fee later", "later today"),
    ],
)
def test_relative_availability_jan19(
    demo_client: TestClient,
    utterance: str,
    period_fragment: str,
) -> None:
    turn = _ask(demo_client, utterance)
    assert {item["kind"] for item in turn["items"]} == {"enigma_message"}
    text = turn["items"][0]["text"].lower()
    assert period_fragment in text
    assert "don't see anything" in text
    assert "i'm not sure i follow" not in text


@pytest.mark.parametrize(
    "utterance",
    [
        "What is the fee?",
        "Feel free to do it",
    ],
)
def test_non_availability_utterances_unknown(
    demo_client: TestClient,
    utterance: str,
) -> None:
    turn = _ask(demo_client, utterance)
    assert turn["items"][0]["text"] == "I'm not sure I follow."


def test_unknown_stays_unknown(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Where should I book brunch?")
    assert turn["items"][0]["text"] == "I'm not sure I follow."
