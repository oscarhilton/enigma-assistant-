"""Context compilation — SELECT → TRANSFORM → TRANSMIT (C09 / ADR-028 / ADR-029).

Not: huge prompt → delete until the window fits.
Yes: request → determine requirements → fetch allowed contexts → compile.

The request chooses the context. The existence of context does not justify sending it.
Context should be earned by the request.
Context that is not required for this request does not enter the prompt.

Long memory underneath. Short attention above.
Once conversation has safely changed structured state, the words that caused
the change should usually become disposable.

Objective (not a new intent_router):
  recall of required capabilities: HIGH
  irrelevant private context: LOW
  authority escalation: ZERO
Never prune away the capability needed to answer.
Never include private context merely because it might help.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from personal_enigma.api.conversation_context import (
    RECENT_DIALOGUE_LIMIT,
    ConversationContext,
    match_named_referent,
    project_recent_dialogue_for_egress,
    referent_candidates,
    remember_turn_local_constraint,
)
from personal_enigma.api.demo_intents import build_support_payload
from personal_enigma.api.demo_tools import tool_schemas
from personal_enigma.api.intent_router import ConversationIntentKind, resolve_intent
from personal_enigma.api.speech_acts import (
    SpeechAct,
    classify_speech_act,
    is_support_not_authority,
)
from personal_enigma.attention.projection import AttentionState
from personal_enigma.privacy.egress.disclosure import (
    CompiledTurnManifest,
    ContextModuleDecision,
)

RequestProfileName = Literal[
    "CONVERSATION",
    "GENERAL_KNOWLEDGE",
    "PRIVATE_QUERY",
    "SUPPORT",
    "USER_ATTESTATION",
    "PREPARE_ACTION",
    "AUTHORITATIVE_ACTION",
]

EvidenceDomain = Literal[
    "PRIVATE_WORLD",
    "GENERAL_KNOWLEDGE",
    "EXTERNAL_WORLD",
    "CONVERSATION_ONLY",
]

Authority = Literal[
    "NONE",
    "READ",
    "SUPPORT",
    "ATTEST",
    "PREPARE",
    "APPROVE",
    "EXECUTE",
]

CapabilityFamily = Literal[
    "agenda",
    "attention",
    "availability",
    "source",
    "explain",
    "attestation",
    "assist_prepare",
    "assist",
]

_PRIVATE_QUERY_INTENTS = frozenset(
    {
        ConversationIntentKind.ATTENTION_QUERY,
        ConversationIntentKind.NEXT_ACTION_QUERY,
        ConversationIntentKind.REJECT_NEXT_ACTION,
        ConversationIntentKind.ALTERNATE_TASK_QUERY,
        ConversationIntentKind.DURATION_QUERY,
        ConversationIntentKind.TIME_FIT_QUERY,
        ConversationIntentKind.CHANGES_QUERY,
        ConversationIntentKind.WAITING_ON_QUERY,
        ConversationIntentKind.CAN_WAIT_QUERY,
        ConversationIntentKind.AVAILABILITY_QUERY,
        ConversationIntentKind.WHY_QUERY,
        ConversationIntentKind.UNSUPPORTED_WORLD_QUERY,
    }
)

_SOURCE_NEEDLES = ("email", "whatsapp", "chat", "said", "quote", "exactly")

# Epistemic private-world cues — not intent_router phrase families.
_FIRST_PERSON = re.compile(
    r"\b(i|i['’]m|i['’]ve|i['’]d|i['’]ll|me|my|mine|we|we['’]re|our|ours|us)\b",
    re.IGNORECASE,
)
_PERSONAL_HORIZON = re.compile(
    r"\b(this week|next week|this weekend|today|tomorrow|right now|"
    r"later today|this afternoon|this evening|saturday|sunday|friday|"
    r"my week|my day|this morning)\b",
    re.IGNORECASE,
)
_PRIVATE_ARTIFACTS = re.compile(
    r"\b(email|emails|inbox|mail|calendar|agenda|schedule|plans?|"
    r"focus(?:ed)?|attention|need to do|needs me|next action|"
    r"what['’]?s on|whats on|on this week|on for (?:today|this)|"
    r"at work|for work|my work|obligations?|what i (?:need|should))\b",
    re.IGNORECASE,
)
_ENIGMA_CAPABILITY_CHALLENGE = re.compile(
    r"\b(don['’]?t you know|do you (?:not )?know|can['’]?t you|"
    r"can we (?:check|see|look)|the whole point|"
    r"can you (?:see|check|look(?: at)?|read|access))\b",
    re.IGNORECASE,
)
_FOLLOW_UP = re.compile(
    r"^\s*(what about|how about|and (?:at|what|the)|at work|at home)\b",
    re.IGNORECASE,
)
_SHORT_CLARIFY = re.compile(r"^\s*(what|huh|wait|sorry|hm+)\s*[?.!]?\s*$", re.IGNORECASE)
_GENERIC_EXPLANATION = re.compile(
    r"^\s*(how do(?:es)?\b.+\bwork\b|why is (?:the |a )?\w+"
    r"|what is (?:a |an |the )?(?!on\b|next\b|urgent\b|important\b))",
    re.IGNORECASE | re.DOTALL,
)
_FOCUS_NOW = re.compile(
    r"\b(focus(?:ed)? on|what should i (?:be )?(?:doing|focused)|"
    r"should be focused|what i should be focused)\b",
    re.IGNORECASE,
)
_WORK_SCOPE = re.compile(
    r"\b(at work|for work|work(?:ing)? (?:week|calendar|schedule))\b",
    re.IGNORECASE,
)
_PERIOD_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bthis week\b", re.IGNORECASE), "this_week"),
    (re.compile(r"\bnext week\b", re.IGNORECASE), "next_week"),
    (re.compile(r"\bthis weekend\b", re.IGNORECASE), "this_weekend"),
    (re.compile(r"\blater today\b", re.IGNORECASE), "later_today"),
    (re.compile(r"\bthis afternoon\b", re.IGNORECASE), "this_afternoon"),
    (re.compile(r"\bthis evening\b", re.IGNORECASE), "this_evening"),
    (re.compile(r"\btomorrow\b", re.IGNORECASE), "tomorrow"),
    (re.compile(r"\btoday\b", re.IGNORECASE), "today"),
    (re.compile(r"\bsaturday\b", re.IGNORECASE), "saturday"),
    (re.compile(r"\bfriday night\b", re.IGNORECASE), "friday_night"),
)

BASE_CONSTITUTION = (
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
    "Once conversation has safely changed structured state, the words that caused "
    "the change should usually become disposable. "
    "Never invent world facts — only tools provide truth. "
    "Do not recite next actions from recent_dialogue or conversation state — call a tool. "
    "Context compilation should remove irrelevant knowledge, not remove Enigma. "
    "Never prune away the capability needed to answer. "
    "Never include private context merely because it might help. "
    "If a tool is listed, you may call it. Never deny an Enigma capability that is "
    "in your tool list. If a requested source is missing, use the closest listed "
    "private-world tool or defer honestly — do not claim Enigma has no calendar, "
    "attention, or email capability when those tools are present."
)

_PROFILE_INSTRUCTIONS: dict[str, str] = {
    "CONVERSATION": (
        "Ordinary conversation. No private-world facts. No tools. "
        "recent_dialogue is anaphora only, not truth."
    ),
    "GENERAL_KNOWLEDGE": (
        "General knowledge. Private context: NONE. Tools: NONE. "
        "Do not use or invent brunch, Atlas, Elena, attention state, or personal facts."
    ),
    "PRIVATE_QUERY": (
        "Private-world query. Ground every personal fact in a tool. "
        "The compiled working set is not a schedule and not a biography."
    ),
    "SUPPORT": (
        "SUPPORT: reduce friction before delegation. "
        "Distress may increase supportiveness, never authority. "
        "Prefer explanation, decomposition, attention, and a first step. "
        "Call attention.get_current / next_action.get when the user asks what "
        "to focus on. Prefer world.explain for a named subject. "
        "Only propose Assist if the user explicitly asks to prepare or do. "
        "ADHD or difficulty must never silently change what Enigma is allowed to do."
    ),
    "USER_ATTESTATION": (
        "USER_ATTESTATION: the user is reporting a possible world-state change. "
        "Resolve the referent. Call world.record_user_attestation before responding. "
        "Conversational acknowledgement is not persistence. "
        "Recording a report is not Assist and needs no approval. "
        "Do not perform external mutations. next_action.get is not the primary write."
    ),
    "PREPARE_ACTION": (
        "PREPARE: the user asked Enigma to draft or prepare. Call assist.propose. "
        "Never skip to execute. Explicit approval is a later ceremony."
    ),
    "AUTHORITATIVE_ACTION": (
        "AUTHORITATIVE_ACTION: proposal plus explicit approval ceremony, never silent execute. "
        "'do it' / 'help me do that' → assist.propose then assist.approve after the card. "
        "'Go on then' after a proposal card → assist.approve. "
        "Distress does not imply consent."
    ),
}

_PRIVATE_QUERY_TOOLS: tuple[str, ...] = (
    "attention.get_current",
    "next_action.get",
    "next_action.get_alternatives",
    "next_action.reject",
    "referent.get_duration",
    "availability.check",
    "agenda.get",
    "world.get_changes",
    "world.get_blockers",
    "world.explain",
)

_SOURCE_TOOLS: tuple[str, ...] = ("source.recent", "source.quote")

_FAMILY_TOOLS: dict[str, tuple[str, ...]] = {
    "agenda": ("agenda.get",),
    "attention": (
        "attention.get_current",
        "next_action.get",
        "next_action.get_alternatives",
        "next_action.reject",
    ),
    "availability": ("availability.check", "referent.get_duration"),
    "source": ("source.recent", "source.quote"),
    "explain": ("world.explain", "world.get_changes", "world.get_blockers"),
    "attestation": ("world.record_user_attestation",),
    "assist_prepare": ("assist.propose",),
    "assist": ("assist.propose", "assist.approve"),
}

_PROFILE_TOOLS: dict[str, tuple[str, ...]] = {
    "CONVERSATION": (),
    "GENERAL_KNOWLEDGE": (),
    "PRIVATE_QUERY": _PRIVATE_QUERY_TOOLS,
    "SUPPORT": (
        "world.explain",
        "attention.get_current",
        "next_action.get",
        "referent.get_duration",
        "availability.check",
    ),
    "USER_ATTESTATION": ("world.record_user_attestation",),
    "PREPARE_ACTION": ("assist.propose",),
    "AUTHORITATIVE_ACTION": ("assist.propose", "assist.approve"),
}

_AUTHORITY_FORBIDDEN: dict[str, frozenset[str]] = {
    "NONE": frozenset(_PRIVATE_QUERY_TOOLS + _SOURCE_TOOLS + ("assist.propose", "assist.approve")),
    "READ": frozenset({"assist.propose", "assist.approve", "world.record_user_attestation"}),
    "SUPPORT": frozenset({"assist.propose", "assist.approve", "world.record_user_attestation"}),
    "ATTEST": frozenset(
        set(_PRIVATE_QUERY_TOOLS + _SOURCE_TOOLS + ("assist.propose", "assist.approve"))
        - {"world.record_user_attestation"}
    ),
    "PREPARE": frozenset({"assist.approve"}),
    "APPROVE": frozenset(),
    "EXECUTE": frozenset(),
}

_PROFILE_PROVIDERS: dict[str, tuple[str, ...]] = {
    "CONVERSATION": ("recent_dialogue", "current_subject", "pending_act", "local_constraints"),
    "GENERAL_KNOWLEDGE": (),
    "PRIVATE_QUERY": (
        "recent_dialogue",
        "current_subject",
        "pending_act",
        "local_constraints",
        "attention_working_set",
        "simulated_time",
    ),
    "SUPPORT": (
        "recent_dialogue",
        "current_subject",
        "pending_act",
        "local_constraints",
        "support_state",
        "attention_working_set",
        "simulated_time",
    ),
    "USER_ATTESTATION": (
        "recent_dialogue",
        "current_subject",
        "pending_act",
        "referent_candidates",
        "simulated_time",
    ),
    "PREPARE_ACTION": (
        "recent_dialogue",
        "current_subject",
        "pending_act",
        "local_constraints",
        "assist_proposal",
    ),
    "AUTHORITATIVE_ACTION": (
        "recent_dialogue",
        "current_subject",
        "pending_act",
        "local_constraints",
        "assist_proposal",
    ),
}

_UNEARNED = (
    "No request-derived justification. Context that is not required for this request "
    "does not enter the prompt."
)

_ALL_MODULES: tuple[str, ...] = (
    "recent_dialogue",
    "current_subject",
    "pending_act",
    "local_constraints",
    "attention",
    "calendar",
    "source_raw",
    "referent_candidates",
    "support_state",
    "assist_proposal",
    "simulated_time",
)

_PROVIDER_TO_MODULE: dict[str, str] = {
    "recent_dialogue": "recent_dialogue",
    "current_subject": "current_subject",
    "pending_act": "pending_act",
    "local_constraints": "local_constraints",
    "attention_working_set": "attention",
    "referent_candidates": "referent_candidates",
    "support_state": "support_state",
    "assist_proposal": "assist_proposal",
    "simulated_time": "simulated_time",
}

_INCLUDED_JUSTIFICATION: dict[str, str] = {
    "recent_dialogue": (
        "Chat history explains meaning; it does not become world truth. "
        "Working-set anaphora only (remote-safe, size-bounded)."
    ),
    "current_subject": (
        "Active subject is the hot working set for this request. "
        "Conversation state resolves language; tools establish truth."
    ),
    "pending_act": "Pending dialogue act is required to keep authority transitions explicit.",
    "local_constraints": "Turn-local constraints (period/location) help interpret this request.",
    "attention": (
        "This private-world query earned the current needs_you / next_action projection. "
        "Context may help the model understand the question. It may not answer the question."
    ),
    "support_state": (
        "SUPPORT earned a current-subject summary so Enigma can explain, decompose, "
        "and name a first step without raising authority."
    ),
    "referent_candidates": (
        "The request named or reported a referent; thin {id, label, kind} rows are "
        "required to bind language. They are not a schedule."
    ),
    "assist_proposal": "An existing Assist proposal is pending; authority transition needs its id.",
    "simulated_time": "Demo clock is required to interpret this private-world query.",
}

_EXCLUDED_JUSTIFICATION: dict[str, str] = {
    "calendar": _UNEARNED,
    "source_raw": (
        "Raw sources never enter the remote prompt. Verbatim quotation is local-only. "
        "That is successful forgetting, not memory failure."
    ),
}

_PROVIDER_MAX_BYTES: dict[str, int] = {
    "recent_dialogue": 2048,
    "current_subject": 512,
    "pending_act": 256,
    "local_constraints": 512,
    "support_state": 1024,
    "attention_working_set": 1536,
    "referent_candidates": 1536,
    "assist_proposal": 256,
    "simulated_time": 128,
}


class _SessionLike(Protocol):
    context: ConversationContext
    state: AttentionState


@dataclass(frozen=True)
class RequestConstraints:
    """Turn-local domain constraints. Horizon may inherit; it is not an intent."""

    period: str | None = None
    scope: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class RequestInterpretation:
    """Interpret → evidence domain → authority → families. Not classify-then-strip-tools."""

    evidence_domain: EvidenceDomain
    authority: Authority
    profile: RequestProfileName
    speech_act: SpeechAct
    constraints: RequestConstraints
    capability_families: tuple[str, ...]


@dataclass(frozen=True)
class RequestProfile:
    """Authority / evidence regime — not a classic intent and not English routing."""

    name: RequestProfileName
    context_providers: tuple[str, ...]
    tools: tuple[str, ...]
    instructions: str


@dataclass(frozen=True)
class CompiledRemoteContext:
    """Hot working set for this request. Not a transcript. Not the whole world."""

    profile: RequestProfileName
    speech_act: SpeechAct
    system_prompt: str
    context_summary: dict[str, Any]
    tools: list[dict[str, Any]]
    working_set: dict[str, Any]
    providers_used: tuple[str, ...]
    manifest: CompiledTurnManifest
    evidence_domain: EvidenceDomain = "PRIVATE_WORLD"
    authority: Authority = "READ"
    capability_families: tuple[str, ...] = ()

    def wire_context(self) -> dict[str, Any]:
        """Model payload only. The manifest is audit, not prompt."""
        payload = dict(self.context_summary)
        payload["request_profile"] = self.profile
        payload["evidence_domain"] = self.evidence_domain
        payload["authority"] = self.authority
        payload["system_prompt"] = self.system_prompt
        payload["working_set"] = self.working_set
        return payload

    @property
    def tool_names(self) -> list[str]:
        return [
            str((row.get("function") or {}).get("name"))
            for row in self.tools
            if (row.get("function") or {}).get("name")
        ]


def _is_generic_knowledge(utterance: str) -> bool:
    """Syntactic question about the public world — not the user's private world."""
    if _FIRST_PERSON.search(utterance) or _PERSONAL_HORIZON.search(utterance):
        return False
    if _FOLLOW_UP.search(utterance) or _ENIGMA_CAPABILITY_CHALLENGE.search(utterance):
        return False
    if _PRIVATE_ARTIFACTS.search(utterance) and not _GENERIC_EXPLANATION.search(utterance):
        return False
    return _GENERIC_EXPLANATION.search(utterance) is not None


def _prior_turn_was_private(session: _SessionLike | None) -> bool:
    if session is None:
        return False
    ctx = session.context
    if ctx.temporal_constraint:
        return True
    if ctx.last_intent is not None and ctx.last_intent.kind in _PRIVATE_QUERY_INTENTS:
        return True
    private_acts = {
        "question",
        "support",
        "user_attestation",
        "prepare",
        "action_request",
        "correction",
    }
    return any(row.act in private_acts for row in ctx.recent_dialogue[-4:])


def _live_approve_authorized(session: _SessionLike | None) -> bool:
    """Bare yes is not EXECUTE. Only a live APPROVE_CONFIRMATION authorizes approve."""
    return session is not None and session.context.approval_authorized()


def _has_private_world_cues(utterance: str, session: _SessionLike | None) -> bool:
    """Recall first: this needs private truth. Precision (which tools) comes later."""
    if _is_generic_knowledge(utterance):
        return False
    if _FIRST_PERSON.search(utterance) and (
        _PERSONAL_HORIZON.search(utterance)
        or _PRIVATE_ARTIFACTS.search(utterance)
        or _FOCUS_NOW.search(utterance)
        or _ENIGMA_CAPABILITY_CHALLENGE.search(utterance)
    ):
        return True
    if _PERSONAL_HORIZON.search(utterance) and (
        _PRIVATE_ARTIFACTS.search(utterance) or _FOLLOW_UP.search(utterance)
    ):
        return True
    if _PRIVATE_ARTIFACTS.search(utterance) or _ENIGMA_CAPABILITY_CHALLENGE.search(utterance):
        return True
    if _FOLLOW_UP.search(utterance) and _prior_turn_was_private(session):
        return True
    if _FOCUS_NOW.search(utterance):
        return True
    return False


def _infer_period(utterance: str) -> str | None:
    for pattern, period in _PERIOD_PATTERNS:
        if pattern.search(utterance):
            return period
    return None


def _infer_scope(utterance: str) -> str | None:
    if _WORK_SCOPE.search(utterance):
        return "work"
    return None


def _infer_source(utterance: str) -> str | None:
    hay = utterance.casefold()
    if "email" in hay or "inbox" in hay or "mail" in hay:
        return "email"
    if "whatsapp" in hay:
        return "whatsapp"
    return None


def _infer_constraints(
    utterance: str,
    session: _SessionLike | None,
) -> RequestConstraints:
    period = _infer_period(utterance)
    scope = _infer_scope(utterance)
    source = _infer_source(utterance)
    inherit = _FOLLOW_UP.search(utterance) is not None or (
        period is None and scope is not None
    )
    if period is None and inherit and session is not None:
        period = session.context.temporal_constraint
    return RequestConstraints(period=period, scope=scope, source=source)


def _infer_evidence_domain(
    utterance: str,
    session: _SessionLike | None,
    act: SpeechAct,
) -> EvidenceDomain:
    # Do not default every sentence to PRIVATE_WORLD "just in case."
    if act in {"USER_ATTESTATION", "SUPPORT", "PREPARE", "ACTION_REQUEST", "CORRECTION"}:
        return "PRIVATE_WORLD"
    if act == "APPROVAL":
        if _live_approve_authorized(session):
            return "PRIVATE_WORLD"
        return "CONVERSATION_ONLY"
    if is_support_not_authority(utterance):
        return "PRIVATE_WORLD"
    intent = resolve_intent(utterance)
    if (
        (intent.kind in _PRIVATE_QUERY_INTENTS or intent.kind == ConversationIntentKind.HELP_QUERY)
        and not _is_generic_knowledge(utterance)
    ):
        return "PRIVATE_WORLD"
    if _has_private_world_cues(utterance, session):
        return "PRIVATE_WORLD"
    if _SHORT_CLARIFY.search(utterance) or intent.kind == ConversationIntentKind.GREETING:
        return "CONVERSATION_ONLY"
    if _is_generic_knowledge(utterance) or act == "QUESTION":
        return "GENERAL_KNOWLEDGE"
    if intent.kind == ConversationIntentKind.GREETING or act == "ORDINARY_CONVERSATION":
        return "CONVERSATION_ONLY"
    if act == "QUESTION":
        return "GENERAL_KNOWLEDGE"
    return "CONVERSATION_ONLY"


def _infer_authority(
    utterance: str,
    act: SpeechAct,
    domain: EvidenceDomain,
    session: _SessionLike | None = None,
) -> Authority:
    if act == "USER_ATTESTATION":
        return "ATTEST"
    if act == "PREPARE":
        return "PREPARE"
    if act == "APPROVAL":
        return "APPROVE" if _live_approve_authorized(session) else "NONE"
    if act == "ACTION_REQUEST":
        return "APPROVE"
    if act == "SUPPORT" or is_support_not_authority(utterance) or _FOCUS_NOW.search(utterance):
        return "SUPPORT"
    if domain == "PRIVATE_WORLD":
        return "READ"
    return "NONE"


def _infer_capability_families(
    *,
    domain: EvidenceDomain,
    authority: Authority,
    utterance: str,
    constraints: RequestConstraints,
) -> tuple[str, ...]:
    if domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"} or authority == "NONE":
        return ()
    if authority == "ATTEST":
        return ("attestation",)
    if authority == "PREPARE":
        return ("assist_prepare",)
    if authority in {"APPROVE", "EXECUTE"}:
        return ("assist",)
    families: list[str] = []
    hay = utterance.casefold()
    if constraints.source or any(needle in hay for needle in ("email", "inbox", "mail")):
        families.append("source")
        families.append("attention")
    if constraints.period or "what's on" in hay or "whats on" in hay or "on this week" in hay:
        families.append("agenda")
    if _FOCUS_NOW.search(utterance) or "right now" in hay or "urgent" in hay:
        families.append("attention")
    if authority == "SUPPORT":
        families.append("explain")
        families.append("attention")
    if not families and domain == "PRIVATE_WORLD":
        families.extend(["agenda", "attention", "availability", "explain"])
    # Recall before precision: a private-world read still needs a query surface.
    if domain == "PRIVATE_WORLD" and authority == "READ" and "agenda" not in families:
        if constraints.period:
            families.insert(0, "agenda")
    return tuple(dict.fromkeys(families))


def _profile_for(domain: EvidenceDomain, authority: Authority) -> RequestProfileName:
    if authority == "ATTEST":
        return "USER_ATTESTATION"
    if authority == "PREPARE":
        return "PREPARE_ACTION"
    if authority in {"APPROVE", "EXECUTE"}:
        return "AUTHORITATIVE_ACTION"
    if authority == "SUPPORT":
        return "SUPPORT"
    if domain == "PRIVATE_WORLD":
        return "PRIVATE_QUERY"
    if domain == "GENERAL_KNOWLEDGE":
        return "GENERAL_KNOWLEDGE"
    return "CONVERSATION"


def interpret_request(
    utterance: str,
    session: _SessionLike | None = None,
) -> RequestInterpretation:
    """Interpret locally: domain, then authority, then candidate families.

    Profile is the authority/evidence regime. It does not pick the exact tool
    before families are visible. Frozen intent_router is a positive private-world
    signal, not a QUESTION → GENERAL_KNOWLEDGE dump.
    """
    act = classify_speech_act(utterance)
    domain = _infer_evidence_domain(utterance, session, act)
    authority = _infer_authority(utterance, act, domain, session)
    if domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"}:
        authority = "NONE"
    constraints = _infer_constraints(utterance, session)
    families = _infer_capability_families(
        domain=domain,
        authority=authority,
        utterance=utterance,
        constraints=constraints,
    )
    return RequestInterpretation(
        evidence_domain=domain,
        authority=authority,
        profile=_profile_for(domain, authority),
        speech_act=act,
        constraints=constraints,
        capability_families=families,
    )


def select_request_profile(
    utterance: str,
    session: _SessionLike | None = None,
) -> RequestProfileName:
    """INTERPRET locally. Does not need Alex's entire context."""
    return interpret_request(utterance, session).profile


def profile_spec(name: RequestProfileName) -> RequestProfile:
    return RequestProfile(
        name=name,
        context_providers=_PROFILE_PROVIDERS[name],
        tools=_PROFILE_TOOLS[name],
        instructions=_PROFILE_INSTRUCTIONS[name],
    )


def compile_system_prompt(profile: RequestProfileName) -> str:
    return f"{BASE_CONSTITUTION} Profile {profile}: {_PROFILE_INSTRUCTIONS[profile]}"


def _trim(payload: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    blob = json.dumps(payload, default=str)
    if len(blob.encode("utf-8")) <= max_bytes:
        return payload
    if "recent_dialogue" in payload and isinstance(payload["recent_dialogue"], list):
        rows = list(payload["recent_dialogue"])
        while (
            rows
            and len(json.dumps({"recent_dialogue": rows}, default=str).encode("utf-8"))
            > max_bytes
        ):
            rows = rows[1:]
        return {"recent_dialogue": rows}
    if "referent_candidates" in payload and isinstance(payload["referent_candidates"], list):
        return {"referent_candidates": list(payload["referent_candidates"])[:6]}
    return payload


def _disposable_recent_dialogue(context: ConversationContext) -> list[dict[str, Any]]:
    """Raw completing sentences are not truth once structured state exists."""
    rows = project_recent_dialogue_for_egress(context.recent_dialogue)
    compiled: list[dict[str, Any]] = []
    for row in rows:
        if row.get("role") == "user" and row.get("act") == "user_attestation":
            compiled.append(
                {
                    "role": "user",
                    "act": "user_attestation",
                    "subject_id": row.get("subject_id"),
                    "summary": "User reported a world change that was recorded",
                }
            )
            continue
        compiled.append(row)
    return compiled


def _provide_recent_dialogue(session: _SessionLike) -> dict[str, Any]:
    rows = _disposable_recent_dialogue(session.context)
    return {"recent_dialogue": rows} if rows else {}


def _provide_current_subject(session: _SessionLike) -> dict[str, Any]:
    ctx = session.context
    payload: dict[str, Any] = {
        "current_subject_id": ctx.current_subject_id,
        "current_subject_kind": ctx.current_subject_kind,
    }
    # empty_horizon is local discourse residue, not a live SHOW exchange.
    if ctx.focus_reason and ctx.focus_reason != "empty_horizon":
        payload["focus_reason"] = ctx.focus_reason
    if payload.get("current_subject_id") or payload.get("focus_reason"):
        return payload
    return {}


def _provide_pending_act(session: _SessionLike) -> dict[str, Any]:
    live = session.context.live_pending_confirmation()
    if live is None:
        return {}
    payload: dict[str, Any] = {
        "pending_dialogue_act": live.kind,
        "pending_dialogue_act_created_turn": live.created_turn,
        "pending_dialogue_act_expires_after_turns": live.expires_after_turns,
    }
    payload["pending_confirmation"] = {
        "kind": live.kind,
        "subject_id": live.subject_id,
        "created_turn": live.created_turn,
        "consumed_by": live.consumed_by,
        "expires_after_turns": live.expires_after_turns,
    }
    return payload


def _provide_local_constraints(session: _SessionLike) -> dict[str, Any]:
    ctx = session.context
    payload: dict[str, Any] = {}
    if ctx.temporal_constraint:
        payload["temporal_constraint"] = ctx.temporal_constraint
    if ctx.turn_local_constraints:
        payload["turn_local_constraints"] = [
            {"key": row.key, "value": row.value, "applies_to": row.applies_to}
            for row in ctx.turn_local_constraints
        ]
    return payload


def _provide_support_state(session: _SessionLike) -> dict[str, Any]:
    support = build_support_payload(session.state, session.context)
    return {
        "current_subject_summary": {
            "id": support.get("subject_id"),
            "title": support.get("title"),
            "why_it_matters": support.get("why_it_matters"),
            "first_step": support.get("first_step"),
            "estimated_minutes": support.get("estimated_minutes"),
            "assist_offered": False,
        }
    }


def _provide_attention_working_set(session: _SessionLike) -> dict[str, Any]:
    state = session.state
    return {
        "attention_working_set": {
            "needs_you": [{"id": row.id, "title": row.title} for row in state.needs_you],
            "next_actions": [
                {
                    "id": row.id,
                    "title": row.title,
                    "source_candidate_id": row.source_candidate_id,
                }
                for row in state.next_actions
            ],
        }
    }


def _provide_referent_candidates(session: _SessionLike) -> dict[str, Any]:
    rows = referent_candidates(session.state)
    return {"referent_candidates": rows} if rows else {}


def _provide_assist_proposal(session: _SessionLike) -> dict[str, Any]:
    proposal_id = session.context.current_assist_proposal_id
    if not proposal_id:
        return {}
    return {"current_assist_proposal_id": proposal_id}


def _provide_simulated_time(session: _SessionLike) -> dict[str, Any]:
    return {"simulated_time": session.state.simulated_time}


_PROVIDERS: dict[str, Any] = {
    "recent_dialogue": _provide_recent_dialogue,
    "current_subject": _provide_current_subject,
    "pending_act": _provide_pending_act,
    "local_constraints": _provide_local_constraints,
    "support_state": _provide_support_state,
    "attention_working_set": _provide_attention_working_set,
    "referent_candidates": _provide_referent_candidates,
    "assist_proposal": _provide_assist_proposal,
    "simulated_time": _provide_simulated_time,
}


def _source_context_earned(utterance: str) -> bool:
    hay = utterance.casefold()
    return any(needle in hay for needle in _SOURCE_NEEDLES)


def _referents_earned(
    utterance: str, profile: RequestProfileName, session: _SessionLike
) -> bool:
    if profile == "USER_ATTESTATION":
        return True
    if classify_speech_act(utterance) == "CORRECTION":
        return True
    return match_named_referent(utterance, referent_candidates(session.state)) is not None


def tools_for_profile(profile: RequestProfileName, utterance: str) -> tuple[str, ...]:
    names = list(_PROFILE_TOOLS[profile])
    if profile == "PRIVATE_QUERY" and _source_context_earned(utterance):
        names.extend(_SOURCE_TOOLS)
    return tuple(names)


def tools_for_interpretation(interp: RequestInterpretation) -> tuple[str, ...]:
    """Candidate families ∪ profile floor, then authority fence.

    Minimisation may hide irrelevant capabilities. It must not hide the
    capability required to satisfy a private-world request.
    """
    names: list[str] = list(_PROFILE_TOOLS[interp.profile])
    for family in interp.capability_families:
        names.extend(_FAMILY_TOOLS[family])
    if interp.constraints.source:
        names.extend(_SOURCE_TOOLS)
        names.extend(_FAMILY_TOOLS["attention"])
    forbidden = _AUTHORITY_FORBIDDEN.get(interp.authority, frozenset())
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in forbidden or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return tuple(deduped)


def _remember_constraints(session: _SessionLike, constraints: RequestConstraints) -> None:
    if constraints.period:
        session.context.temporal_constraint = constraints.period
    if constraints.scope:
        remember_turn_local_constraint(
            session.context,
            key="scope",
            value=constraints.scope,
            applies_to=None,
        )


def tool_schemas_for(names: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
    wanted = {name: index for index, name in enumerate(names)}
    selected = [
        schema
        for schema in tool_schemas()
        if (schema.get("function") or {}).get("name") in wanted
    ]
    selected.sort(
        key=lambda schema: wanted.get(str((schema.get("function") or {}).get("name")), 99)
    )
    return selected


def _all_tool_names() -> list[str]:
    names: list[str] = []
    for schema in tool_schemas():
        name = (schema.get("function") or {}).get("name")
        if name:
            names.append(str(name))
    return names


def _module_max_bytes(module: str) -> int | None:
    for provider, mapped in _PROVIDER_TO_MODULE.items():
        if mapped == module:
            return _PROVIDER_MAX_BYTES.get(provider)
    return None


def build_compiled_turn_manifest(
    *,
    profile: RequestProfileName,
    speech_act: SpeechAct,
    earned_providers: list[str] | tuple[str, ...],
    used_providers: list[str] | tuple[str, ...],
    tool_names: list[str] | tuple[str, ...],
) -> CompiledTurnManifest:
    """Every module gets include/exclude + a request-derived justification."""
    earned_modules = {_PROVIDER_TO_MODULE[name] for name in earned_providers}
    used_modules = {_PROVIDER_TO_MODULE[name] for name in used_providers}
    context: dict[str, ContextModuleDecision] = {}
    for module in _ALL_MODULES:
        included = module in used_modules
        earned = module in earned_modules
        extra: dict[str, Any] = {}
        if included:
            max_bytes = _module_max_bytes(module)
            if max_bytes is not None:
                extra["max_bytes"] = max_bytes
            if module == "recent_dialogue":
                extra["max_turns"] = RECENT_DIALOGUE_LIMIT
                extra["remote_safe_only"] = True
            justification = _INCLUDED_JUSTIFICATION[module]
        elif module in _EXCLUDED_JUSTIFICATION:
            justification = _EXCLUDED_JUSTIFICATION[module]
        elif earned:
            justification = (
                "Permitted for this request profile, but no live values existed to fetch."
            )
        else:
            justification = _UNEARNED
        context[module] = ContextModuleDecision(
            include=included,
            justification=justification,
            **extra,
        )
    selected = list(tool_names)
    selected_set = set(selected)
    return CompiledTurnManifest(
        profile=profile,
        speech_act=speech_act,
        context=context,
        tools=selected,
        excluded_tools=[name for name in _all_tool_names() if name not in selected_set],
    )


def compile_remote_context(
    utterance: str,
    session: _SessionLike,
    *,
    profile: RequestProfileName | None = None,
) -> CompiledRemoteContext:
    """SELECT requirements → fetch allowed contexts → TRANSFORM → compile prompt.

    Internally this is context compilation / context selection, not prompt pruning.
    Profile is the authority/evidence regime. Candidate families decide tools.
    """
    interp = interpret_request(utterance, session)
    if profile is not None:
        interp = RequestInterpretation(
            evidence_domain=interp.evidence_domain,
            authority=interp.authority,
            profile=profile,
            speech_act=interp.speech_act,
            constraints=interp.constraints,
            capability_families=interp.capability_families,
        )
    _remember_constraints(session, interp.constraints)
    spec = profile_spec(interp.profile)
    providers = list(spec.context_providers)
    earn_referents = (
        interp.profile not in {"GENERAL_KNOWLEDGE", "CONVERSATION"}
        and _referents_earned(utterance, interp.profile, session)
    )
    if earn_referents and "referent_candidates" not in providers:
        providers.append("referent_candidates")
    if not earn_referents:
        providers = [name for name in providers if name != "referent_candidates"]

    summary: dict[str, Any] = {}
    used: list[str] = []
    for name in providers:
        slice_ = _PROVIDERS[name](session)
        if not slice_:
            continue
        summary.update(_trim(slice_, _PROVIDER_MAX_BYTES[name]))
        used.append(name)

    tool_names = tools_for_interpretation(interp)
    working_set = {
        "profile": interp.profile,
        "evidence_domain": interp.evidence_domain,
        "authority": interp.authority,
        "speech_act": interp.speech_act,
        "capability_families": list(interp.capability_families),
        "recent_dialogue_turns": len(summary.get("recent_dialogue") or []),
        "current_subject_id": summary.get("current_subject_id"),
        "pending_dialogue_act": summary.get("pending_dialogue_act"),
        "temporal_constraint": interp.constraints.period or summary.get("temporal_constraint"),
        "scope": interp.constraints.scope,
        "source": interp.constraints.source,
        "providers": list(used),
        "tools": list(tool_names),
    }
    if interp.constraints.period and "temporal_constraint" not in summary:
        summary["temporal_constraint"] = interp.constraints.period
    if interp.constraints.scope:
        summary.setdefault("turn_local_constraints", [])
        rows = list(summary.get("turn_local_constraints") or [])
        if not any(row.get("key") == "scope" for row in rows):
            rows.append({"key": "scope", "value": interp.constraints.scope, "applies_to": None})
        summary["turn_local_constraints"] = rows
    manifest = build_compiled_turn_manifest(
        profile=interp.profile,
        speech_act=interp.speech_act,
        earned_providers=providers,
        used_providers=used,
        tool_names=tool_names,
    )
    return CompiledRemoteContext(
        profile=interp.profile,
        speech_act=interp.speech_act,
        system_prompt=compile_system_prompt(interp.profile),
        context_summary=summary,
        tools=tool_schemas_for(tool_names),
        working_set=working_set,
        providers_used=tuple(used),
        manifest=manifest,
        evidence_domain=interp.evidence_domain,
        authority=interp.authority,
        capability_families=interp.capability_families,
    )


def compiled_envelope_blob(compiled: CompiledRemoteContext) -> str:
    return json.dumps(
        {
            "prompt": compiled.system_prompt,
            "context": compiled.context_summary,
            "tools": compiled.tool_names,
        },
        default=str,
    ).casefold()


__all__ = [
    "BASE_CONSTITUTION",
    "CompiledRemoteContext",
    "RequestConstraints",
    "RequestInterpretation",
    "RequestProfile",
    "RequestProfileName",
    "build_compiled_turn_manifest",
    "compile_remote_context",
    "compile_system_prompt",
    "compiled_envelope_blob",
    "interpret_request",
    "profile_spec",
    "select_request_profile",
    "tool_schemas_for",
    "tools_for_interpretation",
    "tools_for_profile",
]
