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


def _manifest_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if dumped else None
    if isinstance(value, dict) and value:
        return value
    return None

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

_DEFAULT_CONVERSATION_PROMPT = (
    "You are Enigma's conversational orchestrator. "
    "World state is truth — not chat history. "
    "Conversation state resolves language; tools establish truth. "
    "Context may help the model understand the question. It may not answer the question. "
    "Assist funnel (never skip toward more authority): "
    "UNDERSTAND → SUPPORT → PREPARE → PROPOSE → APPROVE → EXECUTE. "
    "Distress may increase supportiveness, never authority. "
    "Ambiguous help requests default to the least-authoritative useful interpretation. "
    "The request chooses the context. The request selects what to fetch, transform, and send. "
    "The existence of context does not justify sending it. "
    "Context should be earned by the request. "
    "Every piece of remote context must have a request-derived justification. "
    "Context that is not required for this request does not enter the prompt. "
    "Recent chat helps interpret the conversation. It does not establish world truth. "
    "Chat history remembers the conversation. World state remembers the world. "
    "Chat history explains meaning; it does not become world truth. "
    "Send enough previous conversation to understand meaning — not enough to recreate their life. "
    "User reports are evidence; user commands grant authority. "
    "Long memory underneath. Short attention above. "
    "Words are working memory. State is memory. "
    "Never invent world facts — only tools provide truth."
)


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
    context_manifest: dict[str, Any] | None = None

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
        system_prompt: str | None = None,
        request_profile: str | None = None,
        context_manifest: dict[str, Any] | None = None,
    ) -> RemoteSafeContext:
        """C09 orchestrator path — compiled working set, not the whole world."""
        summary = dict(context_summary)
        prompt = system_prompt or summary.pop("system_prompt", None) or _DEFAULT_CONVERSATION_PROMPT
        profile = request_profile or summary.pop("request_profile", None)
        skip = {"system_prompt", "last_intent_kind", "last_period", "context_manifest"}
        top_level = {
            "recent_dialogue",
            "simulated_time",
            "attention_count",
            "working_set",
            "attention_working_set",
            "current_subject_summary",
        }
        conversation: dict[str, Any] = {}
        user_content: dict[str, Any] = {"user_message": user_message}
        if profile:
            user_content["request_profile"] = profile
        for key, value in summary.items():
            if key in skip:
                continue
            if key in top_level:
                if value not in (None, [], {}):
                    user_content[key] = value
            else:
                conversation[key] = value
        if conversation:
            user_content["conversation"] = conversation
        manifest = _manifest_dict(context_manifest) or _manifest_dict(
            summary.get("context_manifest")
        )
        field_manifest = manifest
        blob = json.dumps(user_content, default=str)
        if _EMAIL_RE.search(blob):
            raise ValueError("conversation orchestrator payload contains raw email address")
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
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
            context_manifest=field_manifest,
            field_summary={
                "message_word_count": len(user_message.split()),
                "context_keys": sorted(conversation.keys()),
                "tool_count": len(tools),
                "tool_names": tool_names,
                "simulated_time": user_content.get("simulated_time"),
                "attention_count": user_content.get("attention_count"),
                "request_profile": profile,
                "context_manifest": field_manifest,
            },
        )
