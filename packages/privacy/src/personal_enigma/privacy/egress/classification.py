"""Egress classification types — REMOTE_SAFE is the sole wire payload class (ADR-022)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from personal_enigma.privacy.egress.disclosure import (
    CONVERSATION_EGRESS_EXCLUDED,
    CONVERSATION_EGRESS_INCLUDED,
    tool_names_from_wire,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


@dataclass(frozen=True, slots=True)
class PrivateRaw[T]:
    """PRIVATE_RAW — full MIME bodies, note bodies, attachments; never crosses egress."""

    value: T


@dataclass(frozen=True, slots=True)
class PrivateDerived[T]:
    """PRIVATE_DERIVED — embeddings, summaries, graphs; transform before egress."""

    value: T


class RemoteSafeContext(BaseModel):
    """Sole accepted payload type for ``AuditedEgressGate.submit()``."""

    model_config = ConfigDict(frozen=True)

    transformation_profile: str
    provider: str
    model: str
    prompt: str = ""
    wire_body: dict[str, Any] = Field(default_factory=dict)
    field_summary: dict[str, Any] = Field(default_factory=dict)
    may_transmit_remotely: bool = True
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    denied_capabilities: list[str] = Field(default_factory=list)

    @classmethod
    def from_transformed(
        cls,
        context: Any,
        *,
        provider: str,
        model: str,
        prompt: str = "",
    ) -> RemoteSafeContext:
        """Build a REMOTE_SAFE wire context from a validated ``TransformedContext``."""
        from personal_enigma.privacy import REMOTE_METADATA_KEYS as meta_keys
        from personal_enigma.transformation import TransformedContext

        if not isinstance(context, TransformedContext):
            raise TypeError(
                f"RemoteSafeContext.from_transformed requires TransformedContext; "
                f"got {type(context).__name__}"
            )
        safe_metadata = {
            key: str(value)
            for key, value in context.metadata.items()
            if key in meta_keys
        }
        wire_user = {
            "prompt": prompt,
            "context": {
                "summary": context.summary,
                "entities": list(context.entities),
                "metadata": safe_metadata,
            },
        }
        if context.relations:
            wire_user["context"]["relations"] = [
                rel.model_dump(mode="json") for rel in context.relations
            ]
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You reason only over the sanitised Enigma context. "
                        "Do not invent private identifiers."
                    ),
                },
                {"role": "user", "content": json.dumps(wire_user, default=str)},
            ],
        }
        return cls(
            transformation_profile="remote_safe_v1",
            provider=provider,
            model=model,
            prompt=prompt,
            wire_body=body,
            may_transmit_remotely=context.may_transmit_remotely,
            field_summary={
                "summary_word_count": len(context.summary.split()),
                "entity_count": len(context.entities),
                "relation_count": len(context.relations),
                "metadata_keys": sorted(safe_metadata.keys()),
                "pseudonym_count": sum(
                    1 for entity in context.entities if str(entity).startswith("PERSON_")
                ),
            },
        )

    @classmethod
    def for_conversation_orchestrator(
        cls,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        model: str,
        provider: str = "fireworks",
        denied_capabilities: list[str] | None = None,
    ) -> RemoteSafeContext:
        """C09 orchestrator path — utterance, conversation state, same tool schemas."""
        conversation = {
            "current_subject_id": context_summary.get("current_subject_id"),
            "current_subject_kind": context_summary.get("current_subject_kind"),
        }
        for key in (
            "referent_candidates",
            "current_attention_item_id",
            "current_next_action_id",
            "current_assist_proposal_id",
            "suppressed_next_action_ids",
            "last_intent_kind",
            "last_period",
        ):
            if key in context_summary:
                conversation[key] = context_summary[key]
        user_content: dict[str, Any] = {
            "user_message": user_message,
            "conversation": conversation,
        }
        if "simulated_time" in context_summary:
            user_content["simulated_time"] = context_summary["simulated_time"]
        if "attention_count" in context_summary:
            user_content["attention_count"] = context_summary["attention_count"]
        blob = json.dumps(user_content, default=str)
        if _EMAIL_RE.search(blob):
            raise ValueError("conversation orchestrator payload contains raw email address")
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Enigma's conversational orchestrator for a demo assistant. "
                        "Conversation state resolves language; tools establish truth. "
                        "referent_candidates are {id, label, kind} for resolving 'that' / "
                        "named subjects only — not a schedule, not urgency, not status, "
                        "not recommendations, not world claims. "
                        "A question about the user's private world must be grounded by "
                        "calling an Enigma tool. Do not answer private-world questions "
                        "from conversation state alone. "
                        "For questions about the user's personal world (attention, calendar, "
                        "what is on a period, next actions, availability, what changed), "
                        "select the matching tool. "
                        "Never invent world facts — only tools provide truth. "
                        "Mail importance is an attention question: call attention.get_current, "
                        "never a mail-search tool. "
                        "For ordinary conversation (greetings, chitchat, general knowledge "
                        "such as the colour of the sky), answer in content with no tool calls. "
                        "If the request is genuinely ambiguous, ask a brief clarifying question. "
                        "Do not default to saying you don't follow. "
                        "If no tool can ground a personal-world fact, return no tool calls "
                        "and admit ignorance — do not guess from referent_candidates. "
                        "Referents come from conversation context, not invention."
                    ),
                },
                {"role": "user", "content": blob},
            ],
            "tools": tools,
            "tool_choice": "auto",
        }
        tool_names = tool_names_from_wire(body)
        return cls(
            transformation_profile="conversation_orchestrator_v1",
            provider=provider,
            model=model,
            prompt=user_message,
            wire_body=body,
            may_transmit_remotely=True,
            included=list(CONVERSATION_EGRESS_INCLUDED),
            excluded=list(CONVERSATION_EGRESS_EXCLUDED),
            denied_capabilities=list(denied_capabilities or ()),
            field_summary={
                "message_word_count": len(user_message.split()),
                "context_keys": sorted(conversation.keys()),
                "tool_count": len(tools),
                "tool_names": tool_names,
                "simulated_time": user_content.get("simulated_time"),
                "attention_count": user_content.get("attention_count"),
            },
        )
