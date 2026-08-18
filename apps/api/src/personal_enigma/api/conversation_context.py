"""Session-scoped dialogue referents — not world state.

Conversation context resolves "it", "that", and "this" from structured turns
Enigma already presented. It never mutates AttentionState or checkpoints.

Recent dialogue is interpretive working memory (2–6 turns). It is not world
truth. Chat history remembers the conversation; world state remembers the world.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from personal_enigma.api.intent_router import (
    ConversationIntent,
    ConversationIntentKind,
    compose_follow_up_intent,
)
from personal_enigma.attention.projection import AttentionState, NextActionView

# 2–6 recent turns — enough to understand meaning, not enough to recreate a life.
RECENT_DIALOGUE_LIMIT = 6
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

DialogueRole = Literal["user", "assistant"]
DialogueEgressClassification = Literal["remote_safe", "local_only"]
_LOCAL_QUOTATION_KINDS = frozenset(
    {"source_quotation", "source_quote", "quoted_message", "note_excerpt"}
)

_REMEMBERED_INTENT_KINDS = frozenset(
    {
        ConversationIntentKind.ATTENTION_QUERY,
        ConversationIntentKind.NEXT_ACTION_QUERY,
        ConversationIntentKind.AVAILABILITY_QUERY,
        ConversationIntentKind.TIME_FIT_QUERY,
        ConversationIntentKind.DURATION_QUERY,
        ConversationIntentKind.WAITING_ON_QUERY,
        ConversationIntentKind.CAN_WAIT_QUERY,
        ConversationIntentKind.CHANGES_QUERY,
        ConversationIntentKind.WHY_QUERY,
        ConversationIntentKind.HELP_QUERY,
        ConversationIntentKind.ALTERNATE_TASK_QUERY,
    }
)

# Alex-v1 support-contract preferred_effort max_minutes (evaluator ground truth).
_OBLIGATION_ESTIMATED_MINUTES: dict[str, int] = {
    "item-obligation_token_audit": 30,
    "item-obligation_atlas_review": 15,
    "item-obligation_brunch_book": 15,
    "item-obligation_empty_states": 10,
}

DialogueActKind = Literal[
    "SHOW_CONFIRMATION",
    "APPROVE_CONFIRMATION",
    "EXPLAIN_CONFIRMATION",
    "ADVISE_CONFIRMATION",
    "CLARIFY_CONFIRMATION",
]

# Answering these does not authorize PREPARE / ACT.
_NON_ACTION_DIALOGUE_ACTS: frozenset[str] = frozenset(
    {
        "SHOW_CONFIRMATION",
        "EXPLAIN_CONFIRMATION",
        "ADVISE_CONFIRMATION",
        "CLARIFY_CONFIRMATION",
    }
)

_STRUCTURED_SUBJECT_KINDS: frozenset[str] = frozenset(
    {"attention_item", "next_action", "attention_summary"}
)

_LOCATION_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "my",
        "the",
        "this",
        "that",
        "our",
        "your",
        "their",
        "his",
        "her",
        "some",
        "any",
        "town",
        "city",
        "mind",
        "fact",
        "order",
        "case",
        "front",
        "back",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "today",
        "tomorrow",
        "weekend",
        "morning",
        "afternoon",
        "evening",
        "night",
    }
)


_PENDING_ACT_TTL: dict[str, int] = {
    "APPROVE_CONFIRMATION": 6,
    "SHOW_CONFIRMATION": 1,
    "EXPLAIN_CONFIRMATION": 1,
    "ADVISE_CONFIRMATION": 1,
    "CLARIFY_CONFIRMATION": 1,
}

# Grounded conversational frame decays. Requests resolve independently.
_FRAME_TTL_TURNS = 6

RequestKind = Literal[
    "agenda",
    "next_work",
    "catch_up",
    "important_from_source",
    "support_explain",
    "subject_details",
    "attest",
]
RequestSatisfaction = Literal["SATISFIED", "PARTIAL", "UNSATISFIED"]
UnresolvedRequestStatus = Literal["UNANSWERED", "PARTIAL"]
EvidenceNeed = Literal["attention", "agenda", "source", "world_explain", "referent"]
CapsuleEvidenceDomain = Literal[
    "PRIVATE_WORLD",
    "GENERAL_KNOWLEDGE",
    "EXTERNAL_WORLD",
    "CONVERSATION_ONLY",
]
CapsuleAuthority = Literal[
    "NONE",
    "READ",
    "SUPPORT",
    "ATTEST",
    "PREPARE",
    "APPROVE",
    "EXECUTE",
]


@dataclass(frozen=True)
class UnresolvedRequest:
    """The conversational request still in play — not world truth."""

    kind: RequestKind
    status: UnresolvedRequestStatus


@dataclass(frozen=True)
class LastToolOutcome:
    """Tool plumbing vs whether the human request was answered."""

    capability: str | None
    request_satisfied: bool


@dataclass(frozen=True)
class RepairState:
    misunderstanding_signalled: bool = False


@dataclass(frozen=True)
class TurnHandoff:
    """Compact non-authoritative carry-over for the next model invocation."""

    current_goal: RequestKind | None = None
    progress_made: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    evidence_needed: tuple[EvidenceNeed, ...] = ()
    natural_continuation: str | None = None
    caveats: tuple[str, ...] = ()

    def public_view(self) -> dict[str, Any]:
        return {
            "current_goal": self.current_goal,
            "progress_made": list(self.progress_made),
            "unresolved": list(self.unresolved),
            "evidence_needed": list(self.evidence_needed),
            "natural_continuation": self.natural_continuation,
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class ConversationCapsule:
    """Ephemeral discourse state for the next utterance.

    The capsule carries continuity. The compiler grants context. The world
    establishes truth. Evidence and constraints may inherit; authority is
    previous-turn metadata, never a grant. Requests resolve; frames decay.
    The capsule may recover the question. It may not recover the answer.
    """

    active_goal: RequestKind | None = None
    previous_authority: CapsuleAuthority | None = None
    unresolved_request: UnresolvedRequest | None = None
    last_outcome: LastToolOutcome | None = None
    repair_state: RepairState | None = None
    evidence_domain: CapsuleEvidenceDomain | None = None
    temporal_constraint: str | None = None
    scope: str | None = None
    source: str | None = None
    current_subject_id: str | None = None
    frame_created_turn: int = 0
    frame_expires_after_turns: int = _FRAME_TTL_TURNS

    def public_view(self) -> dict[str, Any]:
        """Wire projection. No previous_authority grant, no source bodies."""
        unresolved = None
        if self.unresolved_request is not None:
            unresolved = {
                "kind": self.unresolved_request.kind,
                "status": self.unresolved_request.status,
            }
        last = None
        if self.last_outcome is not None:
            last = {
                "capability": self.last_outcome.capability,
                "request_satisfied": self.last_outcome.request_satisfied,
            }
        return {
            "active_goal": self.active_goal,
            "evidence_domain": self.evidence_domain,
            "temporal_frame": self.temporal_constraint,
            "scope": self.scope,
            "source_scope": self.source,
            "unresolved_request": unresolved,
            "last_outcome": last,
        }

    @property
    def authority(self) -> CapsuleAuthority | None:
        """Previous-turn metadata. Never a grant."""
        return self.previous_authority


@dataclass(frozen=True)
class PendingConfirmation:
    """Speech act the previous Enigma turn asked the user to answer.

    ``yes`` inherits this act. It never upgrades it.
    SHOW? → yes → SHOW. APPROVE THIS ACTION? → yes → APPROVE.

    Only a *live* pending act is compiled. ``created_turn`` /
    ``consumed_by`` / ``expires_after_turns`` keep SHOW from leaking
    into a later unrelated question.
    """

    kind: DialogueActKind
    subject_id: str | None = None
    created_turn: int = 0
    consumed_by: int | None = None
    expires_after_turns: int = 1


@dataclass(frozen=True)
class TurnLocalConstraint:
    """Session-only constraint. Evaporates with the session — not user memory.

    Same philosophy as turn-local tone (ADR-025): this-turn location is not
    “Alex lives in Shoreditch.”
    """

    key: str
    value: str
    applies_to: str | None = None
    durable: bool = False


@dataclass
class DialogueTurn:
    """One bounded conversational turn. Visible locally; egress-filtered remotely.

    ``text`` is what the user saw. Remote working memory uses ``remote_safe_text``
    or ``summary`` when ``egress_classification`` is ``local_only``.
    """

    role: DialogueRole
    text: str
    act: str | None = None
    subject_id: str | None = None
    egress_classification: DialogueEgressClassification = "remote_safe"
    summary: str | None = None
    remote_safe_text: str | None = None


@dataclass
class ConversationContext:
    current_attention_item_id: str | None = None
    current_next_action_id: str | None = None
    current_world_object_id: str | None = None
    current_assist_proposal_id: str | None = None
    # Invisible discourse subject — populated from structured Enigma turns (C09).
    current_subject_id: str | None = None
    current_subject_kind: str | None = None
    # Why focus last changed. Not a classifier label for the next turn.
    focus_reason: str | None = None
    # Useful period constraint ("saturday") — not last_intent_kind.
    temporal_constraint: str | None = None
    pending_confirmation: PendingConfirmation | None = None
    pending_dialogue_act: DialogueActKind | None = None
    # User-turn counter for pending-act TTL. Incremented at begin_user_turn.
    turn_index: int = 0
    turn_local_constraints: list[TurnLocalConstraint] = field(default_factory=list)
    suppressed_next_action_ids: list[str] = field(default_factory=list)
    last_intent: ConversationIntent | None = None
    # Interpretive working memory — not world truth, not tone memory, not a biography.
    recent_dialogue: list[DialogueTurn] = field(default_factory=list)
    # Ephemeral request capsule (ADR-030). Not a parallel state machine.
    capsule: ConversationCapsule | None = None
    # Compact non-authoritative handoff (C27). Sibling of capsule, not truth.
    handoff: TurnHandoff | None = None
    # Set for this user turn only; never a durable trait.
    named_referent_changed_this_turn: bool = False
    turn_local_recorded_this_turn: bool = False

    def live_pending_confirmation(self) -> PendingConfirmation | None:
        """Pending act that is still unanswered and unexpired."""
        pending = self.pending_confirmation
        if pending is None or pending.consumed_by is not None:
            return None
        age = self.turn_index - pending.created_turn
        if age > pending.expires_after_turns:
            return None
        return pending

    def live_grounded_frame(self) -> ConversationCapsule | None:
        """Still-live PRIVATE_WORLD frame. Independent of request satisfaction."""
        capsule = self.capsule
        if capsule is None or capsule.evidence_domain != "PRIVATE_WORLD":
            return None
        age = self.turn_index - capsule.frame_created_turn
        if age > capsule.frame_expires_after_turns:
            return None
        return capsule

    def live_capsule(self) -> ConversationCapsule | None:
        """Compilation path: a grounded frame that has not yet decayed."""
        return self.live_grounded_frame()

    def set_pending_confirmation(
        self,
        kind: DialogueActKind | None,
        subject_id: str | None = None,
    ) -> None:
        current = self.pending_confirmation
        if current is not None and current.consumed_by is None:
            self.pending_confirmation = replace(current, consumed_by=self.turn_index)
        if kind is None:
            self.pending_dialogue_act = None
            return
        pending = PendingConfirmation(
            kind=kind,
            subject_id=subject_id,
            created_turn=self.turn_index,
            expires_after_turns=_PENDING_ACT_TTL.get(kind, 1),
        )
        self.pending_confirmation = pending
        self.pending_dialogue_act = kind

    def begin_user_turn(self) -> None:
        """Evaporate this-turn flags. Session constraints stay until reset."""
        self.turn_index += 1
        self.named_referent_changed_this_turn = False
        self.turn_local_recorded_this_turn = False
        live = self.live_pending_confirmation()
        if live is None:
            self.pending_dialogue_act = None
        else:
            self.pending_dialogue_act = live.kind
        if self.live_grounded_frame() is None:
            self.capsule = None

    def remember_dialogue_turn(self, turn: DialogueTurn) -> None:
        """Append a turn and drop anything older than ``RECENT_DIALOGUE_LIMIT``."""
        self.recent_dialogue.append(turn)
        overflow = len(self.recent_dialogue) - RECENT_DIALOGUE_LIMIT
        if overflow > 0:
            self.recent_dialogue = self.recent_dialogue[overflow:]

    def approval_authorized(self) -> bool:
        pending = self.live_pending_confirmation()
        return pending is not None and pending.kind == "APPROVE_CONFIRMATION"

    def propose_authorized(self) -> bool:
        """PREPARE is not the answer to SHOW / EXPLAIN / ADVISE / CLARIFY."""
        pending = self.live_pending_confirmation()
        if pending is None:
            return True
        return pending.kind not in _NON_ACTION_DIALOGUE_ACTS

    def suppress_next_action(self, action_id: str) -> None:
        if action_id and action_id not in self.suppressed_next_action_ids:
            self.suppressed_next_action_ids.append(action_id)

    def remember_intent(self, intent: ConversationIntent) -> None:
        if intent.period is not None:
            self.temporal_constraint = intent.period.value
        if intent.kind in _REMEMBERED_INTENT_KINDS:
            self.last_intent = intent

    def compose_intent(self, text: str) -> ConversationIntent:
        """Resolve utterance, composing period-only follow-ups with last intent."""
        resolved = compose_follow_up_intent(text, self.last_intent)
        self.remember_intent(resolved)
        return resolved


def referent_candidates(state: AttentionState) -> list[dict[str, str]]:
    """Ids the model may bind language to — not a schedule or world answer.

    Shape is ``{id, label, kind}`` only. Kind is the referent class
    (attention_item / next_action), not a bucket, urgency, or status.
    """
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in (*state.needs_you, *state.context):
        if item.id in seen:
            continue
        seen.add(item.id)
        rows.append({"id": item.id, "label": item.title, "kind": "attention_item"})
    for action in state.next_actions:
        source = action.source_candidate_id
        if not source or source in seen:
            continue
        seen.add(source)
        rows.append({"id": source, "label": action.title, "kind": "next_action"})
    return rows


def update_pending_dialogue_act(
    context: ConversationContext,
    turn_items: list[dict[str, Any]],
) -> None:
    """Pending act is the last Enigma turn's speech act — not the user's 'yes'.

    An assist_proposal card is an explicit approval affordance.
    Any other Enigma turn replaces that affordance. ``yes`` cannot upgrade
    SHOW / CLARIFY into APPROVE.
    """
    kinds = [str(item.get("kind") or "") for item in turn_items]
    if "assist_proposal" in kinds:
        proposal_id = context.current_assist_proposal_id
        for item in turn_items:
            if item.get("kind") != "assist_proposal":
                continue
            proposal = item.get("proposal") or {}
            plan = item.get("plan") or {}
            proposal_id = str(
                item.get("proposal_id")
                or proposal.get("id")
                or plan.get("proposal_id")
                or proposal_id
                or ""
            )
            break
        context.set_pending_confirmation(
            "APPROVE_CONFIRMATION",
            proposal_id or context.current_assist_proposal_id,
        )
        return
    if "assist_result" in kinds:
        context.set_pending_confirmation(None)
        context.current_assist_proposal_id = None
        return
    if any(kind in _STRUCTURED_SUBJECT_KINDS for kind in kinds):
        context.set_pending_confirmation(None)
        return
    texts = [
        str(item.get("text") or item.get("message") or "")
        for item in turn_items
        if item.get("kind") == "enigma_message"
    ]
    blob = " ".join(texts)
    # Empty-horizon copy is not a live SHOW exchange, even if it contains "?".
    if "?" in blob and context.focus_reason != "empty_horizon":
        context.set_pending_confirmation(
            "SHOW_CONFIRMATION",
            context.current_subject_id,
        )
        return
    context.set_pending_confirmation(None)


def update_context_from_turn_items(
    context: ConversationContext,
    turn_items: list[dict[str, Any]],
) -> None:
    """Refresh referents from structured items Enigma just presented.

    A referent candidate may be available for resolution without becoming
    the current subject. Empty horizon results and secondary radar cards
    must not write ``current_subject_id``.
    """
    kinds = [str(item.get("kind") or "") for item in turn_items]
    structured = any(kind in _STRUCTURED_SUBJECT_KINDS for kind in kinds)
    if not structured:
        context.focus_reason = (
            "empty_horizon" if context.current_subject_id is None else "preserved"
        )
        update_pending_dialogue_act(context, turn_items)
        return

    for item in turn_items:
        kind = item.get("kind")
        if kind == "attention_item":
            # objects_in_response ≠ conversation_focus. Radar / leftover
            # referent_candidates stay resolvable without becoming the subject.
            continue
        elif kind == "next_action":
            action = item.get("action", {})
            action_id = action.get("id")
            if action_id:
                context.current_next_action_id = action_id
            source_id = action.get("source_candidate_id")
            if source_id:
                context.current_attention_item_id = source_id
                context.current_subject_id = source_id
                context.current_subject_kind = "next_action"
                context.focus_reason = "primary_answer"
            elif action_id:
                context.current_subject_id = action_id
                context.current_subject_kind = "next_action"
                context.focus_reason = "primary_answer"
        elif kind == "assist_proposal":
            proposal = item.get("proposal") or {}
            plan = item.get("plan") or {}
            proposal_id = (
                item.get("proposal_id")
                or proposal.get("id")
                or plan.get("proposal_id")
            )
            if proposal_id:
                context.current_assist_proposal_id = str(proposal_id)
        elif kind == "attention_summary":
            state = item.get("state") or {}
            actions = state.get("next_actions") or []
            if actions:
                action = actions[0]
                action_id = action.get("id")
                if action_id:
                    context.current_next_action_id = action_id
                source_id = action.get("source_candidate_id")
                if source_id:
                    context.current_attention_item_id = source_id
                    context.current_subject_id = source_id
                    context.current_subject_kind = "next_action"
                    context.focus_reason = "primary_answer"
                elif action_id:
                    context.current_subject_id = action_id
                    context.current_subject_kind = "next_action"
                    context.focus_reason = "primary_answer"
    update_pending_dialogue_act(context, turn_items)


def estimated_minutes_for_action(action: NextActionView) -> int | None:
    if action.estimated_minutes is not None:
        return action.estimated_minutes
    if action.source_candidate_id:
        return _OBLIGATION_ESTIMATED_MINUTES.get(action.source_candidate_id)
    return None


def find_next_action_by_id(
    state: AttentionState,
    action_id: str | None,
) -> NextActionView | None:
    if not action_id:
        return None
    for row in state.next_actions:
        if row.id == action_id:
            return row
    for row in context_derived_alternates(state, set()):
        if row.id == action_id:
            return row
    return None


def find_attention_item_by_id(
    state: AttentionState,
    item_id: str | None,
) -> tuple[str, str] | None:
    """Return (title, item_id) for a context or needs_you item."""
    if not item_id:
        return None
    for item in (*state.needs_you, *state.context):
        if item.id == item_id:
            return item.title, item.id
    return None


def context_derived_alternates(
    state: AttentionState,
    suppressed_ids: set[str],
) -> list[NextActionView]:
    """Context items as next-action-shaped alternates when support layer is exhausted."""
    primary_sources = {
        row.source_candidate_id
        for row in state.next_actions
        if row.source_candidate_id
    }
    alternates: list[NextActionView] = []
    for item in state.context:
        action_id = f"next-{item.id}"
        if action_id in suppressed_ids:
            continue
        if item.id in primary_sources:
            continue
        alternates.append(
            NextActionView(
                id=action_id,
                title=item.title,
                reason="Could work if you want something else.",
                optional=True,
                estimated_minutes=_OBLIGATION_ESTIMATED_MINUTES.get(item.id),
                source_candidate_id=item.id,
            )
        )
    return alternates


def available_next_actions(
    state: AttentionState,
    suppressed_ids: set[str],
) -> list[NextActionView]:
    """Next actions from support layer, then context-derived alternates."""
    actions: list[NextActionView] = [
        row for row in state.next_actions if row.id not in suppressed_ids
    ]
    if actions:
        return actions
    return context_derived_alternates(state, suppressed_ids)


def pick_alternate_next_action(
    state: AttentionState,
    suppressed_ids: set[str],
) -> NextActionView | None:
    actions = available_next_actions(state, suppressed_ids)
    return actions[0] if actions else None


_REFERENT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "can",
        "could",
        "do",
        "for",
        "from",
        "get",
        "got",
        "help",
        "i",
        "is",
        "it",
        "me",
        "my",
        "need",
        "of",
        "on",
        "or",
        "please",
        "that",
        "the",
        "this",
        "to",
        "we",
        "with",
        "you",
    }
)


def _referent_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-z0-9]+", text.lower()):
        word = raw[:-1] if raw.endswith("s") and len(raw) > 3 else raw
        if word not in _REFERENT_STOPWORDS and len(word) >= 3:
            tokens.add(word)
    return tokens


def match_named_referent(
    utterance: str,
    candidates: list[dict[str, str]],
) -> str | None:
    """Bind a named lexical mention to a unique referent_candidates id.

    Discourse grounding against labels Enigma already surfaced — not an
    intent_router phrase family. Ambiguous or stopword-only utterances
    return None so implicit current_subject can apply.
    """
    uttered = _referent_tokens(utterance)
    if not uttered:
        return None
    scored: list[tuple[int, str]] = []
    for row in candidates:
        label = row.get("label") or row.get("title") or ""
        item_id = row.get("id")
        if not item_id:
            continue
        overlap = uttered & _referent_tokens(label)
        if overlap:
            scored.append((len(overlap), item_id))
    if not scored:
        return None
    best = max(score for score, _item_id in scored)
    winners = [item_id for score, item_id in scored if score == best]
    if len(winners) != 1:
        return None
    return winners[0]


def apply_named_referent_focus(
    context: ConversationContext,
    utterance: str,
    candidates: list[dict[str, str]],
) -> str | None:
    """Bind a named mention to discourse focus. Not an action.

    A conversational correction may change what Enigma is talking about;
    it may never by itself authorize Enigma to do something.
    SUBJECT SELECTION ≠ CAPABILITY SELECTION.
    """
    bound = match_named_referent(utterance, candidates)
    if not bound:
        return None
    if bound != context.current_subject_id:
        context.named_referent_changed_this_turn = True
        context.current_subject_id = bound
        context.current_attention_item_id = bound
        context.current_subject_kind = context.current_subject_kind or "attention_item"
        context.focus_reason = "user_selected"
    return bound


def capture_turn_local_location(utterance: str) -> str | None:
    """Optional session location. Not durable memory. Not a search tool."""
    match = re.search(
        r"\bin\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)",
        utterance,
    )
    if not match:
        return None
    value = match.group(1).strip()
    first = value.split()[0].lower()
    if first in _LOCATION_STOPWORDS or value.lower() in _LOCATION_STOPWORDS:
        return None
    return value


_KIND_FAMILIES: dict[RequestKind, tuple[str, ...]] = {
    "agenda": ("agenda",),
    "next_work": ("attention", "agenda"),
    "catch_up": ("attention", "explain", "agenda"),
    "important_from_source": ("source", "attention"),
    "support_explain": ("explain", "attention"),
    "subject_details": ("explain", "source", "attention"),
    "attest": ("attestation",),
}

_AUTHORITATIVE_QUERY_TOOLS = frozenset(
    {
        "agenda.get",
        "attention.get_current",
        "next_action.get",
        "next_action.get_alternatives",
    }
)


def families_for_request_kind(kind: RequestKind | None) -> tuple[str, ...]:
    if kind is None:
        return ()
    return _KIND_FAMILIES[kind]


def assess_request_satisfaction(
    kind: RequestKind | None,
    ok_tool_names: list[str] | tuple[str, ...],
) -> RequestSatisfaction:
    """Did the tools answer the human request? Not: did a tool return 200."""
    names = set(ok_tool_names)
    if kind is None:
        return "SATISFIED"
    if kind == "agenda":
        return "SATISFIED" if "agenda.get" in names else "UNSATISFIED"
    if kind == "important_from_source":
        if names & _AUTHORITATIVE_QUERY_TOOLS:
            return "SATISFIED"
        if "source.recent" in names:
            return "PARTIAL"
        return "UNSATISFIED"
    if kind == "next_work":
        return "SATISFIED" if names & _AUTHORITATIVE_QUERY_TOOLS else "UNSATISFIED"
    if kind == "catch_up":
        required = {"attention.get_current", "agenda.get"}
        if required.issubset(names):
            return "SATISFIED"
        if names & _AUTHORITATIVE_QUERY_TOOLS:
            return "PARTIAL"
        return "UNSATISFIED"
    if kind == "attest":
        return "SATISFIED" if "world.record_user_attestation" in names else "UNSATISFIED"
    if kind == "support_explain":
        if "world.explain" in names or names & _AUTHORITATIVE_QUERY_TOOLS:
            return "SATISFIED"
        return "UNSATISFIED"
    if kind == "subject_details":
        if "world.explain" in names:
            return "SATISFIED"
        if "source.recent" in names:
            return "PARTIAL"
        return "UNSATISFIED"
    return "PARTIAL"


def reduce_conversation_capsule(
    context: ConversationContext,
    *,
    evidence_domain: str,
    authority: str,
    request_kind: RequestKind | None,
    satisfaction: RequestSatisfaction,
    temporal_constraint: str | None,
    scope: str | None = None,
    source: str | None = None,
    last_capability: str | None = None,
    repair: bool = False,
) -> None:
    """Write the next capsule. SATISFIED clears the request, not necessarily the frame."""
    if evidence_domain == "GENERAL_KNOWLEDGE":
        context.capsule = None
        return
    if evidence_domain != "PRIVATE_WORLD":
        return

    if request_kind not in {
        "agenda",
        "next_work",
        "catch_up",
        "important_from_source",
        "support_explain",
        "subject_details",
        "attest",
    }:
        request_kind = None
    previous = context.capsule
    frame_created = context.turn_index
    if (
        previous is not None
        and previous.evidence_domain == "PRIVATE_WORLD"
        and previous.temporal_constraint == (temporal_constraint or previous.temporal_constraint)
        and previous.frame_created_turn
    ):
        frame_created = previous.frame_created_turn

    unresolved: UnresolvedRequest | None = None
    active_goal: RequestKind | None = None
    if satisfaction == "SATISFIED":
        unresolved = None
        active_goal = None
    elif request_kind is not None:
        status: UnresolvedRequestStatus = "PARTIAL" if satisfaction == "PARTIAL" else "UNANSWERED"
        unresolved = UnresolvedRequest(kind=request_kind, status=status)
        active_goal = request_kind

    granted_authority: CapsuleAuthority | None = None
    if authority in {"NONE", "READ", "SUPPORT", "ATTEST", "PREPARE", "APPROVE", "EXECUTE"}:
        granted_authority = authority  # type: ignore[assignment]

    domain: CapsuleEvidenceDomain = "PRIVATE_WORLD"
    context.capsule = ConversationCapsule(
        active_goal=active_goal,
        previous_authority=granted_authority,
        unresolved_request=unresolved,
        last_outcome=LastToolOutcome(
            capability=last_capability,
            request_satisfied=satisfaction == "SATISFIED",
        ),
        repair_state=RepairState(misunderstanding_signalled=True) if repair else None,
        evidence_domain=domain,
        temporal_constraint=temporal_constraint or (
            previous.temporal_constraint if previous is not None else None
        ),
        scope=scope or (previous.scope if previous is not None else None),
        source=source or (previous.source if previous is not None else None),
        current_subject_id=context.current_subject_id,
        frame_created_turn=frame_created,
        frame_expires_after_turns=_FRAME_TTL_TURNS,
    )


def remember_turn_local_constraint(
    context: ConversationContext,
    *,
    key: str,
    value: str,
    applies_to: str | None,
) -> TurnLocalConstraint:
    constraint = TurnLocalConstraint(
        key=key,
        value=value,
        applies_to=applies_to,
        durable=False,
    )
    context.turn_local_constraints = [
        row
        for row in context.turn_local_constraints
        if not (row.key == key and row.applies_to == applies_to)
    ]
    context.turn_local_constraints.append(constraint)
    context.turn_local_recorded_this_turn = True
    return constraint


def reconcile_action_focus(context: ConversationContext, state: AttentionState) -> None:
    """Clear current_next_action_id when it no longer names a live next action.

    Discourse subject may survive completion (``what did you just do?``).
    Action focus must not point at a non-action. Same family as
    objects_in_response ≠ conversation_focus: product projection and
    conversation focus have separate lifetimes.
    """
    action_id = context.current_next_action_id
    if not action_id:
        return
    if any(row.id == action_id for row in state.next_actions):
        return
    context.current_next_action_id = None


def resolve_referent(
    state: AttentionState,
    context: ConversationContext,
) -> tuple[NextActionView | None, str | None]:
    """Resolve duration/time-fit referent from explicit context ids only."""
    if context.current_next_action_id:
        action = find_next_action_by_id(state, context.current_next_action_id)
        if action is not None:
            return action, action.title
    if context.current_attention_item_id:
        attention = find_attention_item_by_id(state, context.current_attention_item_id)
        if attention is not None:
            title, item_id = attention
            action_id = f"next-{item_id}"
            action = find_next_action_by_id(state, action_id)
            if action is None:
                action = NextActionView(
                    id=action_id,
                    title=title,
                    reason="",
                    optional=True,
                    estimated_minutes=_OBLIGATION_ESTIMATED_MINUTES.get(item_id),
                    source_candidate_id=item_id,
                )
            return action, title
    return None, None


def assistant_visible_text(turn_items: list[dict[str, Any]]) -> str:
    """Local visible copy from this Enigma turn — not a world fact."""
    parts: list[str] = []
    for item in turn_items:
        text = item.get("text") or item.get("message")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
            continue
        if item.get("kind") == "next_action":
            title = (item.get("action") or {}).get("title")
            if isinstance(title, str) and title.strip():
                parts.append(title.strip())
        elif item.get("kind") == "assist_proposal":
            title = (item.get("proposal") or {}).get("title")
            if isinstance(title, str) and title.strip():
                parts.append(title.strip())
    return " ".join(parts)


def classify_assistant_dialogue_egress(
    turn_items: list[dict[str, Any]],
    text: str,
) -> tuple[DialogueEgressClassification, str | None]:
    """Assistant copy that rendered local HIGH/private content must not be replayed raw."""
    local = False
    for item in turn_items:
        if item.get("local_only") or item.get("egress_classification") == "local_only":
            local = True
            break
        level = str(item.get("privacy_level") or "").lower()
        if level in {"high", "very_high"}:
            local = True
            break
        if str(item.get("kind") or "") in _LOCAL_QUOTATION_KINDS:
            local = True
            break
    if _EMAIL_RE.search(text):
        local = True
    if not local:
        return "remote_safe", None
    return "local_only", "Displayed a local quotation about the current subject"


def project_recent_dialogue_for_egress(turns: list[DialogueTurn]) -> list[dict[str, Any]]:
    """Remote working memory: acts + ids + remote-safe text or summary. Never raw local quotes.

    QUOTE ≠ REMOTE CONTEXT: a ``source_quote`` / ``local_only`` assistant turn may
    be remembered as a summary. The verbatim body stays off the Fireworks wire.
    """
    rows: list[dict[str, Any]] = []
    for turn in turns:
        row: dict[str, Any] = {"role": turn.role}
        if turn.act:
            row["act"] = turn.act
        if turn.subject_id:
            row["subject_id"] = turn.subject_id
        if turn.role == "assistant" and turn.egress_classification == "local_only":
            row["summary"] = (
                turn.summary or "Displayed a local quotation about the current subject"
            )
        else:
            text = turn.remote_safe_text or turn.text
            row["text"] = text
        rows.append(row)
    return rows


__all__ = [
    "RECENT_DIALOGUE_LIMIT",
    "ConversationCapsule",
    "ConversationContext",
    "DialogueTurn",
    "EvidenceNeed",
    "LastToolOutcome",
    "PendingConfirmation",
    "RepairState",
    "RequestKind",
    "RequestSatisfaction",
    "TurnLocalConstraint",
    "TurnHandoff",
    "UnresolvedRequest",
    "apply_named_referent_focus",
    "assess_request_satisfaction",
    "assistant_visible_text",
    "available_next_actions",
    "capture_turn_local_location",
    "classify_assistant_dialogue_egress",
    "context_derived_alternates",
    "estimated_minutes_for_action",
    "families_for_request_kind",
    "find_next_action_by_id",
    "match_named_referent",
    "pick_alternate_next_action",
    "project_recent_dialogue_for_egress",
    "reconcile_action_focus",
    "reduce_conversation_capsule",
    "referent_candidates",
    "remember_turn_local_constraint",
    "resolve_referent",
    "update_context_from_turn_items",
    "update_pending_dialogue_act",
]