"""Conservative chat extraction — hard negatives for over-eager AI."""

from __future__ import annotations

import asyncio
from pathlib import Path

from personal_enigma.domain import ChatEvidence, PrivateChatMessage
from personal_enigma.fixtures import build_calendar_event, build_chat_message, build_reminder
from personal_enigma.obligations import (
    ChatExtractKind,
    apply_chat_messages,
    commitment_messages,
    extract_chat_message,
    merge_sources,
)
from personal_enigma.simulation import load_scenario
from personal_enigma.simulation.sources.whatsapp import SyntheticWhatsAppSource

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature"


def _messages(name: str) -> list[PrivateChatMessage]:
    pkg = load_scenario(FEATURE / name)

    async def _run() -> list[PrivateChatMessage]:
        batch = await SyntheticWhatsAppSource(pkg).get_changes(None)
        return [PrivateChatMessage.model_validate(item) for item in batch.items]

    return asyncio.run(_run())


def test_explicit_commitment_writes_open_obligation() -> None:
    messages = _messages("whatsapp-explicit-commitment")
    world = apply_chat_messages(messages)
    assert len(world.obligations) == 1
    extraction = extract_chat_message(
        next(m for m in messages if m.provider_message_id == "wa-alex-book-tonight")
    )
    assert extraction.kind is ChatExtractKind.EXPLICIT_COMMITMENT
    assert extraction.due_bucket == "TONIGHT"
    assert extraction.should_write_obligation is True


def test_soft_intention_is_not_a_deadline_task() -> None:
    messages = _messages("whatsapp-soft-intention")
    world = apply_chat_messages(messages)
    assert world.obligations == []
    kinds = {extract_chat_message(m).kind for m in messages}
    assert ChatExtractKind.SOFT_INTENTION in kinds
    assert ChatExtractKind.EXPLICIT_COMMITMENT not in kinds


def test_waiting_on_is_blocker_not_alex_task() -> None:
    messages = _messages("whatsapp-waiting-on")
    world = apply_chat_messages(messages)
    assert world.obligations == []
    assert len(world.blockers) == 1
    assert world.blockers[0].counterpart == "Elena Vargas"


def test_cancellation_closes_open_chat_obligation() -> None:
    messages = _messages("whatsapp-cancellation")
    world = apply_chat_messages(messages)
    assert world.obligations == []
    assert world.cancelled_message_ids


def test_ambiguous_chatter_must_not_become_a_task() -> None:
    messages = _messages("whatsapp-ambiguous-chatter")
    world = apply_chat_messages(messages)
    assert world.obligations == []
    sometime = next(m for m in messages if m.provider_message_id == "wa-tom-sometime")
    assert extract_chat_message(sometime).kind is ChatExtractKind.SOFT_INTENTION


def test_group_noise_only_alex_commitment_writes() -> None:
    messages = _messages("whatsapp-group-noise")
    world = apply_chat_messages(messages)
    assert len(world.obligations) == 1
    assert "bring" in (world.obligations[0].description or "").casefold()
    noise_ids = {
        "wa-group-gif",
        "wa-group-lol",
        "wa-group-weather",
        "wa-group-thumbs",
        "wa-group-alex-guidebook",
    }
    for message in messages:
        if message.provider_message_id in noise_ids:
            assert extract_chat_message(message).should_write_obligation is False


def test_reaction_does_not_invent_obligation() -> None:
    messages = _messages("whatsapp-reaction-only")
    world = apply_chat_messages(messages)
    assert world.obligations == []
    for message in messages:
        if message.kind == "reaction":
            assert extract_chat_message(message).kind is ChatExtractKind.NONE


def test_correction_amends_instead_of_duplicating() -> None:
    messages = _messages("whatsapp-correction")
    world = apply_chat_messages(messages)
    assert len(world.obligations) == 1
    assert "sunday" in world.obligations[0].description.casefold()


def test_brunch_chat_merges_onto_existing_calendar_obligation() -> None:
    reminder = build_reminder(
        id="rem-brunch-book",
        title="Book Saturday brunch for Elena's parents",
    )
    event = build_calendar_event(
        id="cal-brunch-parents",
        title="Brunch with Elena's parents",
    )
    chat = build_chat_message(
        id="wa-alex-sort-brunch",
        provider_message_id="wa-alex-sort-brunch",
        chat_id="chat-elena",
        from_person={"display_name": "Alex Morgan", "provider_id": "alex"},
        to=[{"display_name": "Elena Vargas", "provider_id": "elena"}],
        body_text="Ah okay — I'll sort brunch",
    )
    merged = merge_sources(
        reminders=[reminder],
        calendar_events=[event],
        chat_messages=commitment_messages([chat]),
    )
    assert len(merged) == 1
    kinds = {evidence.kind for evidence in merged[0].evidence}
    assert "reminder" in kinds
    assert "calendar" in kinds
    assert "chat" in kinds
    assert any(isinstance(e, ChatEvidence) for e in merged[0].evidence)


def test_over_eager_sometime_never_dated() -> None:
    message = build_chat_message(
        from_person={"display_name": "Tom Rivera", "provider_id": "tom"},
        body_text="We really need to do that sometime 😂",
    )
    extraction = extract_chat_message(message)
    world = apply_chat_messages([message])
    assert extraction.kind is ChatExtractKind.SOFT_INTENTION
    assert extraction.should_write_obligation is False
    assert world.obligations == []
    assert extraction.due_bucket is None
