"""Pseudonymise display names in remote-safe titles and summaries (R-L09)."""

from __future__ import annotations

import re

from personal_enigma.domain import PrivatePersonRef
from personal_enigma.identity import EntityResolver

_POSSESSIVE_NAME = re.compile(r"\b([A-Z][a-z]+)'s\b")
_REPLY_TO_NAME = re.compile(r"\bto\s+([A-Z][a-z]+)\s+on\b", flags=re.IGNORECASE)

_TITLE_STOPWORDS = frozenset(
    {
        "arrange",
        "atlas",
        "book",
        "brunch",
        "calendar",
        "colour",
        "color",
        "confirm",
        "decision",
        "draft",
        "empty",
        "family",
        "inventory",
        "monday",
        "parents",
        "proposal",
        "reply",
        "reminder",
        "review",
        "saturday",
        "spacing",
        "state",
        "sunday",
        "task",
        "token",
        "tokens",
        "visiting",
        "weekend",
        "with",
        "for",
        "the",
        "and",
    }
)

_RAW_POSSESSIVE_LEAK = re.compile(r"\b[A-Z][a-z]+'s\b")


def _pseudo_for_name(
    name: str,
    *,
    resolver: EntityResolver | None,
    cache: dict[str, str],
    entities: list[str],
) -> str:
    if name in cache:
        return cache[name]
    if resolver is not None:
        resolved = resolver.resolve_ref(PrivatePersonRef(display_name=name))
        if resolved is not None:
            token = str(resolved)
            cache[name] = token
            if token not in entities:
                entities.append(token)
            return token
    ordinal = len(cache)
    token = f"PERSON_{chr(ord('A') + min(ordinal, 25))}"
    cache[name] = token
    if token not in entities:
        entities.append(token)
    return token


def pseudonymise_remote_text(
    text: str,
    *,
    resolver: EntityResolver | None = None,
    entities: list[str] | None = None,
) -> str:
    """Replace raw display names with opaque PERSON_* tokens."""
    if not text:
        return text
    out = text
    cache: dict[str, str] = {}
    entity_list = entities if entities is not None else []

    def replace_possessive(match: re.Match[str]) -> str:
        name = match.group(1)
        if name.lower() in _TITLE_STOPWORDS:
            return match.group(0)
        pseudo = _pseudo_for_name(
            name, resolver=resolver, cache=cache, entities=entity_list
        )
        return f"{pseudo}'s"

    out = _POSSESSIVE_NAME.sub(replace_possessive, out)

    def replace_reply_to(match: re.Match[str]) -> str:
        name = match.group(1)
        if name.lower() in _TITLE_STOPWORDS:
            return match.group(0)
        pseudo = _pseudo_for_name(
            name, resolver=resolver, cache=cache, entities=entity_list
        )
        return f"to {pseudo} on"

    out = _REPLY_TO_NAME.sub(replace_reply_to, out)
    return out


def assert_no_raw_identity_in_text(text: str) -> None:
    """Fail if text still contains possessive raw display names."""
    if _RAW_POSSESSIVE_LEAK.search(text):
        raise ValueError("remote-safe text contains raw possessive identity")


__all__ = [
    "assert_no_raw_identity_in_text",
    "pseudonymise_remote_text",
]
