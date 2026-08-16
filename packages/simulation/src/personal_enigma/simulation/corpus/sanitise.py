"""Corpus sanitiser — drop generation metadata; rewrite stubs for D08b."""

from __future__ import annotations

from typing import Any

from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage

# Fields that must never reach SyntheticMailSource / Enigma.
GENERATION_METADATA_KEYS = frozenset(
    {
        "prompt",
        "generation_prompt",
        "persona",
        "persona_metadata",
        "reasoning",
        "model_reasoning",
        "pipeline_metadata",
        "generated_context",
        "system_prompt",
    }
)


def strip_generation_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy without generation-pipeline keys."""
    return {k: v for k, v in raw.items() if k not in GENERATION_METADATA_KEYS}


def _rewrite_email(email: str, *, index: int) -> str:
    local = email.split("@", 1)[0] if "@" in email else email or f"person-{index}"
    safe_local = (
        "".join(ch if ch.isalnum() or ch in "-._" else "-" for ch in local)
        or f"person-{index}"
    )
    return f"{safe_local}@company-{index:04d}.example"


def sanitise_conversation(
    conversation: CorpusConversation,
    *,
    rewrite_domains: bool = True,
) -> CorpusConversation:
    """Produce a Demo-safe conversation (identity rewrite stub).

    Full URL/secret/entity filters land in later D08b/D09 work; this scaffold
    always strips generation metadata by construction (CorpusMessage has no
    such fields) and optionally rewrites addresses to ``.example``.
    """
    messages: list[CorpusMessage] = []
    for msg in conversation.messages:
        sender_email = (
            _rewrite_email(msg.sender_email, index=abs(hash(msg.sender_email)) % 10_000)
            if rewrite_domains
            else msg.sender_email
        )
        recipient_emails = [
            _rewrite_email(addr, index=abs(hash(addr)) % 10_000) if rewrite_domains else addr
            for addr in msg.recipient_emails
        ]
        messages.append(
            msg.model_copy(
                update={
                    "sender_email": sender_email,
                    "recipient_emails": recipient_emails,
                }
            )
        )
    return CorpusConversation(id=conversation.id, messages=messages)


def sanitise_raw_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Sanitise an untyped corpus row (e.g. FinePersonas JSON) before modelling."""
    cleaned = strip_generation_metadata(raw)
    emails = cleaned.get("emails")
    if isinstance(emails, list):
        cleaned["emails"] = [
            strip_generation_metadata(item) if isinstance(item, dict) else item for item in emails
        ]
    return cleaned
