"""Demo-mode synthetic chat index — PRIVATE_RAW locally, facts for tools."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from personal_enigma.domain import PrivateChatMessage, PrivateMessage
from personal_enigma.obligations import ChatWorldState, apply_chat_messages
from personal_enigma.simulation import load_scenario
from personal_enigma.simulation.sources.mail import SyntheticMailSource
from personal_enigma.simulation.sources.whatsapp import SyntheticWhatsAppSource

RAW_TTL = timedelta(days=7)
_REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass
class DemoChatIndex:
    messages: list[PrivateChatMessage] = field(default_factory=list)
    mail: list[PrivateMessage] = field(default_factory=list)
    world: ChatWorldState = field(default_factory=ChatWorldState)
    expired_ids: set[str] = field(default_factory=set)

    def is_expired(self, message: PrivateChatMessage) -> bool:
        return (
            message.id in self.expired_ids
            or message.provider_message_id in self.expired_ids
        )


def scenario_root(scenario_id: str) -> Path:
    return _REPO_ROOT / "scenarios" / scenario_id


def load_demo_chat_index(
    scenario_id: str,
    *,
    until: datetime,
) -> DemoChatIndex:
    """Load synthetic WhatsApp + mail up to ``until``. Raw TTL is 7 days."""
    root = scenario_root(scenario_id)
    if not (root / "scenario.yaml").is_file():
        return DemoChatIndex()
    package = load_scenario(root)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)

    async def _fetch() -> tuple[list[PrivateChatMessage], list[PrivateMessage]]:
        wa = await SyntheticWhatsAppSource(package, until=until).get_changes(None)
        mail = await SyntheticMailSource(package, until=until).get_changes(None)
        chats = [PrivateChatMessage.model_validate(item) for item in wa.items]
        messages = [PrivateMessage.model_validate(item) for item in mail.items]
        return chats, messages

    chats, mail = asyncio.run(_fetch())
    cutoff = until - RAW_TTL
    expired = {
        message.id
        for message in chats
        if message.sent_at is not None and message.sent_at < cutoff
    }
    expired.update(
        message.provider_message_id
        for message in chats
        if message.sent_at is not None and message.sent_at < cutoff
    )
    # Raw TTL hides quote bodies (expired_ids). Derived world facts still
    # fold from the full chat set — EXPIRY ≠ LOSS OF ALL UTILITY.
    return DemoChatIndex(
        messages=chats,
        mail=mail,
        world=apply_chat_messages(chats),
        expired_ids=expired,
    )


def find_chat_quote(
    index: DemoChatIndex,
    *,
    source_id: str | None = None,
    user_message: str = "",
    conversation: list[dict[str, object]] | None = None,
) -> PrivateChatMessage | None:
    if source_id:
        for message in index.messages:
            if source_id in {message.id, message.provider_message_id, message.chat_id}:
                if message.kind == "text" and message.body_text:
                    return message
    parts = [user_message]
    for item in conversation or []:
        text = item.get("text") if isinstance(item, dict) else None
        if isinstance(text, str):
            parts.append(text)
    hay = " ".join(parts).casefold()
    texts = [
        message
        for message in index.messages
        if message.kind == "text" and message.body_text
    ]
    elena = [
        message
        for message in texts
        if message.from_person
        and "elena" in (message.from_person.display_name or "").casefold()
    ]
    if any(token in hay for token in ("parent", "coming", "saturday")):
        for message in reversed(elena):
            body = (message.body_text or "").casefold()
            if "definitely coming" in body or "coming saturday" in body:
                return message
    if "elena" in hay or "she" in hay:
        return elena[-1] if elena else None
    return texts[-1] if texts else None
