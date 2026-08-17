"""Conversational constitution — speech acts, not intent_router English.

User reports are evidence. User commands grant authority.

Funnel (never skip toward more authority):

    UNDERSTAND → SUPPORT → PREPARE → PROPOSE → APPROVE → EXECUTE

Distress may increase supportiveness, never authority.
Ambiguous help requests default to the least-authoritative useful interpretation.
"""

from __future__ import annotations

import re
from typing import Literal

from personal_enigma.api.demo_attestation import AttestedState

SpeechAct = Literal[
    "QUESTION",
    "ADVICE",
    "ACTION_REQUEST",
    "CORRECTION",
    "APPROVAL",
    "ORDINARY_CONVERSATION",
    "USER_ATTESTATION",
    "SUPPORT",
    "PREPARE",
]

ASSIST_FUNNEL: tuple[str, ...] = (
    "UNDERSTAND",
    "SUPPORT",
    "PREPARE",
    "PROPOSE",
    "APPROVE",
    "EXECUTE",
)

_REFERENT_CORRECTION = re.compile(
    r"\b(no,?\s+(i meant|the)|actually,?\s+i meant|not that one|the other one)\b",
    re.IGNORECASE,
)
_ATTESTATION_REOPEN = re.compile(
    r"\b(haven['’]?t|have not|didn['’]?t|did not)\s+"
    r"(done|finished|completed|sent|called|paid|booked|wrapped)\b"
    r"|\b(not done|not finished|still need to do)\b",
    re.IGNORECASE,
)
_ATTESTATION_CANCEL = re.compile(
    r"\b((don['’]?t|do not) need to do that"
    r"|no longer need to"
    r"|don['’]?t need that anymore"
    r"|forget (that|it)"
    r"|cancel that)\b",
    re.IGNORECASE,
)
_ATTESTATION_COMPLETED = re.compile(
    r"\b((i['’]?ve|i have)\s+(done|finished|completed|sent|called|paid|booked|wrapped)"
    r"|i\s+(done|finished|completed|sent|called|paid|booked)"
    r"|i just (did|finished|sent|called|paid|booked)"
    r"|tom replied|they replied|(he|she|they)\s+(replied|got back))\b",
    re.IGNORECASE,
)
_DIFFICULTY = re.compile(
    r"\b(adhd|overwhelmed|overwhelming|too much|find this hard|this is hard"
    r"|stuck|crying|cry|distressed|struggling"
    r"|i can['’]?t(?!\s+be bothered))\b",
    re.IGNORECASE,
)
_PREPARE = re.compile(
    r"\b((can you|could you|please)\s+(draft|prepare|write)"
    r"|draft (something|it|a)"
    r"|prepare (something|it|an|a)"
    r"|write (something|a draft|it) up"
    r"|make a draft)\b",
    re.IGNORECASE,
)
_DO_REQUEST = re.compile(
    r"\b((can you|could you|please)\s+(help me )?do"
    r"|help me do"
    r"|do it"
    r"|just do it"
    r"|book it"
    r"|do the"
    r"|let['’]?s (do|book|start)"
    r"|get started"
    r"|start (it|today))\b",
    re.IGNORECASE,
)
_SUPPORT = re.compile(
    r"\b(i need help|need help with|help me with|help with"
    r"|help,?\s+i['’]?m"
    r"|discuss|talk (it |this )?through|talk about"
    r"|break (it|this) down|explain"
    r"|what needs deciding|first step|i find this hard)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"^\s*(what|whats|why|when|where|how|who)\b|[?]\s*$",
    re.IGNORECASE,
)
_APPROVAL_BARE = frozenset(
    {"yes", "yep", "yeah", "go on then", "go on", "go ahead"}
)


def signals_difficulty(utterance: str) -> bool:
    """ADHD / overwhelm / stuck — changes *how*, never *what is allowed*."""
    return _DIFFICULTY.search(utterance) is not None


def is_support_not_authority(utterance: str) -> bool:
    """Ambiguous help and distress stay below PREPARE.

    Ambiguous help requests default to the least-authoritative useful
    interpretation. Distress may increase supportiveness, never authority.
    """
    act = classify_speech_act(utterance)
    if act == "SUPPORT":
        return True
    return signals_difficulty(utterance) and act not in {
        "PREPARE",
        "ACTION_REQUEST",
        "USER_ATTESTATION",
    }


def classify_speech_act(utterance: str) -> SpeechAct:
    """Constitutional act of this utterance. Not a router phrase family.

    Completion reports win over social wrapping in the same turn
    (``I've finished it! Aren't you happy for me?`` → USER_ATTESTATION).

    Ambiguous help requests default to the least-authoritative useful
    interpretation (SUPPORT, not PREPARE/PROPOSE/APPROVE/EXECUTE).
    Distress may increase supportiveness, never authority.
    """
    text = utterance.strip()
    if not text:
        return "ORDINARY_CONVERSATION"
    if _ATTESTATION_REOPEN.search(text) or _ATTESTATION_CANCEL.search(text):
        return "USER_ATTESTATION"
    if _ATTESTATION_COMPLETED.search(text):
        return "USER_ATTESTATION"
    if _REFERENT_CORRECTION.search(text):
        return "CORRECTION"
    difficulty = signals_difficulty(text)
    explicit_do = _DO_REQUEST.search(text) is not None
    explicit_prepare = _PREPARE.search(text) is not None
    if difficulty and not explicit_do and not explicit_prepare:
        return "SUPPORT"
    if explicit_prepare:
        return "PREPARE"
    if explicit_do:
        return "ACTION_REQUEST"
    if _SUPPORT.search(text):
        return "SUPPORT"
    lowered = text.lower().strip(" !.?,")
    if lowered in _APPROVAL_BARE and not difficulty:
        return "APPROVAL"
    if _QUESTION.search(text):
        return "QUESTION"
    return "ORDINARY_CONVERSATION"


def infer_attestation_state(utterance: str) -> AttestedState:
    """Map a user report onto an attested obligation state."""
    if _ATTESTATION_REOPEN.search(utterance):
        return "OPEN"
    if _ATTESTATION_CANCEL.search(utterance):
        return "CANCELLED"
    return "COMPLETED"


def dialogue_act_for_speech(act: SpeechAct) -> str:
    return {
        "USER_ATTESTATION": "user_attestation",
        "SUPPORT": "support",
        "PREPARE": "prepare",
        "ACTION_REQUEST": "action_request",
        "QUESTION": "question",
        "CORRECTION": "correction",
        "APPROVAL": "approval",
        "ADVICE": "advice",
        "ORDINARY_CONVERSATION": "ordinary_conversation",
    }.get(act, "ordinary_conversation")


__all__ = [
    "ASSIST_FUNNEL",
    "SpeechAct",
    "classify_speech_act",
    "dialogue_act_for_speech",
    "infer_attestation_state",
    "is_support_not_authority",
    "signals_difficulty",
]
