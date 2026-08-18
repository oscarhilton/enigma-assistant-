"""Relational bootstrap — continuation mechanics, not a person model.

Explicit interaction inputs → compact non-factual bootstrap segregated from
evidence and authority. Retrieval may contain culture; responses need not.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

BlockKind = Literal["relational_bootstrap"]

_FORBIDDEN_RESPONSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sounds like you(?:'|')?re feeling", re.I),
    re.compile(r"is the goose a metaphor", re.I),
    re.compile(r"goose.*metaphor", re.I),
    re.compile(r"\bplayful\b.*\bfeeling", re.I),
    re.compile(r"🦆"),
    re.compile(r"\bduck emoji\b", re.I),
)

_MANDATORY_CALLBACK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"must appear", re.I),
    re.compile(r"must reference", re.I),
    re.compile(r"required callback", re.I),
    re.compile(r"every response must", re.I),
    re.compile(r"always include (?:the )?goose", re.I),
)

_AUTHORITY_CREATING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ground truth", re.I),
    re.compile(r"authoritative(?:ly)?", re.I),
    re.compile(r"grant(?:s)? authority", re.I),
    re.compile(r"you should believe", re.I),
    re.compile(r"this is (?:the )?truth", re.I),
)


def _collect_input_text(inputs: RelationalBootstrapInputs) -> str:
    parts = [
        inputs.product_voice,
        *inputs.interaction_prefs,
        *inputs.shared_conventions,
        inputs.ephemeral_register,
        *inputs.exemplars,
    ]
    return "\n".join(p for p in parts if p)


def _reject_forbidden_bootstrap_language(inputs: RelationalBootstrapInputs) -> None:
    blob = _collect_input_text(inputs)
    for pattern in _MANDATORY_CALLBACK_PATTERNS:
        if pattern.search(blob):
            raise ValueError(
                "relational bootstrap must not encode mandatory register callback language"
            )
    for pattern in _AUTHORITY_CREATING_PATTERNS:
        if pattern.search(blob):
            raise ValueError(
                "relational bootstrap must not contain authority-creating bootstrap language"
            )


@dataclass(frozen=True, slots=True)
class RelationalBootstrapInputs:
    """Brutally small explicit inputs — no biography or relationship scores."""

    product_voice: str = ""
    interaction_prefs: tuple[str, ...] = ()
    shared_conventions: tuple[str, ...] = ()
    ephemeral_register: str = ""
    exemplars: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationalBootstrapBlock:
    kind: BlockKind
    product_voice: str
    interaction_prefs: tuple[str, ...]
    shared_conventions: tuple[str, ...]
    ephemeral_register: str
    exemplars: tuple[str, ...]
    segregated_from_evidence: bool = True
    grants_authority: bool = False

    def as_wire(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "segregated_from_evidence": self.segregated_from_evidence,
            "grants_authority": self.grants_authority,
            "continuation": {
                "product_voice": self.product_voice,
                "interaction_prefs": list(self.interaction_prefs),
                "shared_conventions": list(self.shared_conventions),
                "ephemeral_register": self.ephemeral_register,
                "exemplars": list(self.exemplars),
            },
        }


def compile_relational_bootstrap(
    inputs: RelationalBootstrapInputs | None,
    *,
    forbidden_leaks: tuple[str, ...] = (),
) -> RelationalBootstrapBlock | None:
    if inputs is None:
        return None
    _reject_forbidden_bootstrap_language(inputs)
    if not any(
        (
            inputs.product_voice.strip(),
            inputs.interaction_prefs,
            inputs.shared_conventions,
            inputs.ephemeral_register.strip(),
            inputs.exemplars,
        )
    ):
        return None
    block = RelationalBootstrapBlock(
        kind="relational_bootstrap",
        product_voice=inputs.product_voice.strip(),
        interaction_prefs=tuple(p.strip() for p in inputs.interaction_prefs if p.strip()),
        shared_conventions=tuple(c.strip() for c in inputs.shared_conventions if c.strip()),
        ephemeral_register=inputs.ephemeral_register.strip(),
        exemplars=tuple(e.strip() for e in inputs.exemplars if e.strip()),
    )
    blob = json.dumps(block.as_wire(), default=str)
    for leak in forbidden_leaks:
        if leak and leak.casefold() in blob.casefold():
            raise ValueError(
                "relational bootstrap must not contain leaked personal text: "
                f"{leak!r}"
            )
    return block


def attach_relational_bootstrap(
    working_set: dict[str, Any],
    inputs: RelationalBootstrapInputs | None,
    *,
    forbidden_leaks: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Attach under working_set without merging into evidence/handoff/capsule."""
    block = compile_relational_bootstrap(inputs, forbidden_leaks=forbidden_leaks)
    if block is None:
        return working_set
    updated = dict(working_set)
    updated["relational_bootstrap"] = block.as_wire()
    return updated


def bootstrap_mentions_register(block: RelationalBootstrapBlock | None, token: str) -> bool:
    if block is None or not token:
        return False
    hay = json.dumps(block.as_wire(), default=str).casefold()
    return token.casefold() in hay


def response_must_use_register(_block: RelationalBootstrapBlock | None) -> bool:
    """Retrieval success does not imply conversational use."""
    return False


def continuation_forbidden_phrases(response: str) -> tuple[str, ...]:
    hits: list[str] = []
    for pattern in _FORBIDDEN_RESPONSE_PATTERNS:
        if pattern.search(response):
            hits.append(pattern.pattern)
    return tuple(hits)


def participates_in_register(response: str, register: str) -> bool:
    if not register:
        return True
    return register.casefold() in response.casefold()


__all__ = [
    "RelationalBootstrapBlock",
    "RelationalBootstrapInputs",
    "attach_relational_bootstrap",
    "bootstrap_mentions_register",
    "compile_relational_bootstrap",
    "continuation_forbidden_phrases",
    "participates_in_register",
    "response_must_use_register",
]
