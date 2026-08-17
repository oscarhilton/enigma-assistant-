"""Demo chat index stub — empty until synthetic WhatsApp lands on main.

C09 LLM front door reads DemoSession.chat_index. Missing this module/property
was HTTP 500. Chat tools see an empty world rather than pulling unlanded
WhatsApp ingestion into this PR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class _EmptyChatWorld:
    blockers: list[Any] = field(default_factory=list)
    facts: list[Any] = field(default_factory=list)


@dataclass
class DemoChatIndex:
    messages: list[Any] = field(default_factory=list)
    mail: list[Any] = field(default_factory=list)
    world: _EmptyChatWorld = field(default_factory=_EmptyChatWorld)
    expired_ids: set[str] = field(default_factory=set)

    def is_expired(self, message: Any) -> bool:
        message_id = getattr(message, "id", None)
        provider_id = getattr(message, "provider_message_id", None)
        return message_id in self.expired_ids or provider_id in self.expired_ids


def load_demo_chat_index(
    scenario_id: str,
    *,
    until: datetime | None = None,
) -> DemoChatIndex:
    del scenario_id, until
    return DemoChatIndex()


def find_chat_quote(
    index: DemoChatIndex,
    *,
    source_id: str | None = None,
    user_message: str = "",
    conversation: list[dict[str, object]] | None = None,
) -> Any | None:
    del index, source_id, user_message, conversation
    return None


__all__ = [
    "DemoChatIndex",
    "find_chat_quote",
    "load_demo_chat_index",
]
