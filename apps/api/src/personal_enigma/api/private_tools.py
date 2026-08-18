"""My Enigma conversation tools — READ + SUPPORT authority ceiling only (P03)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.demo_tools import (
    AgendaGetInput,
    AvailabilityCheckInput,
    ToolExecutionResult,
)
from personal_enigma.api.private_calendar_read import (
    format_agenda_message,
    format_private_availability_message,
)
from personal_enigma.api.private_calendar_store import CalendarReadAdapter
from personal_enigma.attention.projection import AttentionState

PrivateToolName = Literal[
    "agenda.get",
    "availability.check",
    "attention.get_current",
    "world.explain",
]

PRIVATE_ALLOWED_TOOL_NAMES: frozenset[str] = frozenset(
    (
        "agenda.get",
        "availability.check",
        "attention.get_current",
        "world.explain",
    )
)

PRIVATE_DENIED_TOOL_NAMES: frozenset[str] = frozenset(
    (
        "assist.propose",
        "assist.approve",
        "world.record_user_attestation",
        "source.recent",
        "source.quote",
        "gmail.search",
        "gmail.send",
        "calendar.sync",
    )
)


@dataclass
class PrivateToolSession:
    state: AttentionState
    context: ConversationContext
    at: str
    adapter: CalendarReadAdapter
    user_message: str = ""
    last_calendar_facts: list[dict[str, Any]] = field(default_factory=list)


def is_private_allowed_tool(name: str) -> bool:
    return name in PRIVATE_ALLOWED_TOOL_NAMES


def private_capability_contract() -> dict[str, list[str]]:
    allowed = sorted(PRIVATE_ALLOWED_TOOL_NAMES)
    unavailable = sorted(PRIVATE_DENIED_TOOL_NAMES)
    return {"allowed": allowed, "unavailable": unavailable}


def _deny(name: str, at: str, *, reason: str) -> ToolExecutionResult:
    return ToolExecutionResult(
        name=name,  # type: ignore[arg-type]
        ok=False,
        data={"denied": True, "reason": reason},
        turn_items=[
            {
                "kind": "enigma_message",
                "text": "That action is not available in My Enigma yet.",
                "at": at,
            }
        ],
    )


def execute_private_tool(
    session: PrivateToolSession,
    name: str,
    arguments: dict[str, Any],
) -> ToolExecutionResult:
    if not is_private_allowed_tool(name):
        return _deny(name, session.at, reason="private_authority_ceiling")

    at = session.at
    reference = datetime.fromisoformat(at.replace("Z", "+00:00"))
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)

    if name == "attention.get_current":
        if session.state.needs_you or session.state.context:
            titles = [row.title for row in session.state.needs_you[:3]]
            text = (
                "Here's what needs you: " + "; ".join(titles) + "."
                if titles
                else "Nothing needs you right now — calendar is the main source connected."
            )
        else:
            text = "Nothing needs you right now — calendar is the main source connected."
        return ToolExecutionResult(
            name=name,  # type: ignore[arg-type]
            data={"state": session.state.model_dump(mode="json")},
            turn_items=[{"kind": "enigma_message", "text": text, "at": at}],
        )

    if name == "world.explain":
        return ToolExecutionResult(
            name=name,  # type: ignore[arg-type]
            data={"support_only": True},
            turn_items=[
                {
                    "kind": "enigma_message",
                    "text": (
                        "I can read your calendar and talk through what's on — "
                        "I can't prepare or change calendar events yet."
                    ),
                    "at": at,
                }
            ],
        )

    if name == "availability.check":
        parsed = AvailabilityCheckInput.model_validate(arguments)
        period = parsed.period or session.context.temporal_constraint
        text, facts = format_private_availability_message(
            adapter=session.adapter,
            reference=reference,
            period=period,
        )
        session.last_calendar_facts = facts
        return ToolExecutionResult(
            name=name,  # type: ignore[arg-type]
            data={"period": period, "calendar_items": facts},
            turn_items=[{"kind": "enigma_message", "text": text, "at": at}],
        )

    if name == "agenda.get":
        parsed = AgendaGetInput.model_validate(arguments)
        text, facts = format_agenda_message(
            adapter=session.adapter,
            reference=reference,
            period=parsed.period,
        )
        session.last_calendar_facts = facts
        return ToolExecutionResult(
            name=name,  # type: ignore[arg-type]
            data={"period": parsed.period, "calendar_items": facts},
            turn_items=[{"kind": "enigma_message", "text": text, "at": at}],
        )

    return _deny(name, session.at, reason="unknown_private_tool")


__all__ = [
    "PRIVATE_ALLOWED_TOOL_NAMES",
    "PRIVATE_DENIED_TOOL_NAMES",
    "PrivateToolName",
    "PrivateToolSession",
    "execute_private_tool",
    "is_private_allowed_tool",
    "private_capability_contract",
]
