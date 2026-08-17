"""Documented allowlist for remote LLM / hosted-model payloads.

Governing rule: select first → transform second → transmit last.

Remote payloads are JSON-shaped dicts derived from sanitised
``TransformedContext`` (or equivalent). Anything not listed here is forbidden
on the wire to a hosted model.

## Allowed top-level keys

| Key | Meaning |
| --- | --- |
| ``summary`` | Sanitised text; may include ``PERSON_*`` opaque tokens |
| ``entities`` | List of ``PERSON_*`` opaque IDs only |
| ``relations`` | Privacy-safe causal graph (``SemanticRelation`` shapes) |
| ``metadata`` | Subset of :data:`REMOTE_METADATA_KEYS` |
| ``may_transmit_remotely`` | Gate bit; still requires remote inference enabled |

## Allowed metadata keys

See :data:`REMOTE_METADATA_KEYS`. Values must not reintroduce raw PII.

## Forbidden in remote payloads

- Raw ``PrivatePerson`` fields: display names, aliases, emails, phones,
  organisations, provider IDs, or a full person model dump
- Raw attendee / sender email addresses or phone numbers in any string leaf
- Wholesale note bodies (Notes default HIGH; passage-only with explicit policy)
- Keys outside this allowlist
"""

from __future__ import annotations

from typing import Final

REMOTE_PAYLOAD_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "summary",
        "entities",
        "relations",
        "metadata",
        "may_transmit_remotely",
    }
)

REMOTE_RELATION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "type",
        "subject",
        "object",
        "state",
        "resolved_by",
        "resolved_at",
        "since",
        "due",
        "causal",
    }
)

REMOTE_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "source_type",
        "record_id",
        "provider",
        "all_day",
        "is_completed",
        "passage_chars",
        "body_chars",
        "wholesale_body_included",
    }
)

PERSON_PSEUDONYM_PREFIX: Final[str] = "PERSON_"

REMOTE_PAYLOAD_ALLOWLIST_DOC: Final[str] = __doc__ or ""
