"""Demo Assist — propose, approve, synthetic execute, verify.

Takes an already-resolved next action or attention item, returns a structured
``assist_proposal``, and executes **only** against in-session synthetic services
after explicit approval. Frozen checkpoint JSON and policy scores are never
mutated. Verified Assist is not the same as completing the target
obligation (ASSIST COMPLETED ≠ TASK COMPLETED). Only a SATISFIES effect
may join the session overlay (``completed_item_ids``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from personal_enigma.attention.projection import (
    AttentionState,
    NextActionView,
    build_presentation_plan,
)

ActionKind = Literal["calendar_book", "synthetic_note"]
SourceKind = Literal["attention_item", "next_action"]
AssistEffect = Literal["SUPPORT_ONLY", "ADVANCES", "SATISFIES", "UNRELATED"]

BRUNCH_ITEM_ID = "item-obligation_brunch_book"
_STRUCTURED_THAT = frozenset({"attention_item", "next_action", "attention_summary"})


@dataclass(frozen=True)
class AssistTarget:
    source_kind: SourceKind
    source_id: str
    title: str
    attention_item_id: str


@dataclass(frozen=True)
class AssistPlan:
    proposal_id: str
    title: str
    description: str
    action_label: str
    source_item_id: str
    action_kind: ActionKind

    def public_proposal(self) -> dict[str, str]:
        return {
            "id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "action_label": self.action_label,
        }


@dataclass
class SyntheticDemoServices:
    """In-session synthetic calendar + notes. Never writes a real calendar."""

    calendar_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: dict[str, dict[str, Any]] = field(default_factory=dict)
    fail_writes: bool = False

    def book_event(
        self,
        *,
        title: str,
        start_at: str,
        end_at: str,
        location: str | None = None,
    ) -> dict[str, Any]:
        event_id = f"syn-cal-{uuid4().hex[:10]}"
        event = {
            "id": event_id,
            "provider": "synthetic_calendar",
            "title": title,
            "start_at": start_at,
            "end_at": end_at,
            "location": location,
        }
        if not self.fail_writes:
            self.calendar_events[event_id] = event
        return event

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        return self.calendar_events.get(event_id)

    def write_note(self, *, title: str, body: str) -> dict[str, Any]:
        note_id = f"syn-note-{uuid4().hex[:10]}"
        note = {
            "id": note_id,
            "provider": "synthetic_notes",
            "title": title,
            "body": body,
            "completed": True,
        }
        if not self.fail_writes:
            self.notes[note_id] = note
        return note

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        return self.notes.get(note_id)

    def clear(self) -> None:
        self.calendar_events.clear()
        self.notes.clear()
        self.fail_writes = False


def assist_effect_for(plan: AssistPlan) -> AssistEffect:
    """How a verified Assist should change the target obligation.

    ASSIST COMPLETED ≠ TASK COMPLETED. A draft write ADVANCES the
    obligation (TOKEN stays open; next action becomes review). Booking
    brunch SATISFIES the booking obligation.
    """
    if plan.action_kind == "calendar_book":
        return "SATISFIES"
    if plan.action_kind == "synthetic_note":
        return "ADVANCES"
    return "UNRELATED"


def review_draft_next_action(plan: AssistPlan) -> NextActionView:
    """Derived next action after a SUPPORT/ADVANCES draft Assist."""
    return NextActionView(
        id=f"next-review-{plan.source_item_id}",
        title="Review the draft",
        reason="A synthetic draft is ready.",
        optional=True,
        estimated_minutes=10,
        source_candidate_id=plan.source_item_id,
    )


def apply_verified_assist_effect(
    plan: AssistPlan,
    *,
    completed_item_ids: set[str],
    advances: dict[str, NextActionView],
) -> AssistEffect:
    """Mutate session overlays from a verified Assist. Frozen snapshots untouched."""
    effect = assist_effect_for(plan)
    if effect == "SATISFIES":
        completed_item_ids.add(plan.source_item_id)
        advances.pop(plan.source_item_id, None)
    elif effect == "ADVANCES":
        advances[plan.source_item_id] = review_draft_next_action(plan)
    return effect


def _next_action_completed(row: NextActionView, completed_item_ids: set[str]) -> bool:
    source = row.source_candidate_id or ""
    return (
        row.id in completed_item_ids
        or source in completed_item_ids
        or row.id.removeprefix("next-") in completed_item_ids
        or (source != "" and f"next-{source}" in completed_item_ids)
    )


def overlay_completed_items(
    state: AttentionState,
    completed_item_ids: set[str],
) -> AttentionState:
    """Filter SATISFIES / attested-complete ids. Does not touch snapshots."""
    if not completed_item_ids:
        return state
    needs_you = [row for row in state.needs_you if row.id not in completed_item_ids]
    context = [row for row in state.context if row.id not in completed_item_ids]
    next_actions = [
        row for row in state.next_actions if not _next_action_completed(row, completed_item_ids)
    ]
    return state.model_copy(
        update={
            "needs_you": needs_you,
            "context": context,
            "next_actions": next_actions,
            "presentation": build_presentation_plan(len(needs_you)),
        }
    )


def overlay_session_world(
    state: AttentionState,
    completed_item_ids: set[str],
    advances: dict[str, NextActionView] | None = None,
) -> AttentionState:
    """SATISFIES overlay, then ADVANCES next-action replacement. Context stays."""
    overlaid = overlay_completed_items(state, completed_item_ids)
    if not advances:
        return overlaid
    remaining = [
        row
        for row in overlaid.next_actions
        if (row.source_candidate_id or row.id) not in advances
    ]
    return overlaid.model_copy(update={"next_actions": remaining + list(advances.values())})


def _is_completed(target: AssistTarget, completed_item_ids: set[str]) -> bool:
    return (
        target.source_id in completed_item_ids
        or target.attention_item_id in completed_item_ids
    )


def _target_from_attention(item: dict[str, Any]) -> AssistTarget | None:
    payload = item.get("item") or {}
    item_id = payload.get("id")
    title = payload.get("title")
    if not item_id or not title:
        return None
    return AssistTarget(
        source_kind="attention_item",
        source_id=str(item_id),
        title=str(title),
        attention_item_id=str(item_id),
    )


def _target_from_next_action(item: dict[str, Any]) -> AssistTarget | None:
    payload = item.get("action") or {}
    action_id = payload.get("id")
    title = payload.get("title")
    if not action_id or not title:
        return None
    source = payload.get("source_candidate_id") or action_id
    return AssistTarget(
        source_kind="next_action",
        source_id=str(action_id),
        title=str(title),
        attention_item_id=str(source),
    )


def _target_from_summary(state: AttentionState) -> AssistTarget | None:
    """``that`` after an attention_summary: needs_you first, else next_actions."""
    if state.needs_you:
        item = state.needs_you[0]
        return AssistTarget(
            source_kind="attention_item",
            source_id=item.id,
            title=item.title,
            attention_item_id=item.id,
        )
    if state.next_actions:
        action = state.next_actions[0]
        return AssistTarget(
            source_kind="next_action",
            source_id=action.id,
            title=action.title,
            attention_item_id=action.source_candidate_id or action.id,
        )
    return None


def _fallback_target(state: AttentionState) -> AssistTarget | None:
    """No structured 'that' in session: prefer next_actions, then needs_you."""
    if state.next_actions:
        action = state.next_actions[0]
        return AssistTarget(
            source_kind="next_action",
            source_id=action.id,
            title=action.title,
            attention_item_id=action.source_candidate_id or action.id,
        )
    if state.needs_you:
        item = state.needs_you[0]
        return AssistTarget(
            source_kind="attention_item",
            source_id=item.id,
            title=item.title,
            attention_item_id=item.id,
        )
    return None


def assist_target_from_id(
    state: AttentionState,
    item_id: str | None,
    completed_item_ids: set[str] | None = None,
) -> AssistTarget | None:
    """Resolve an explicit attention-item / next-action id to an AssistTarget."""
    if not item_id:
        return None
    done = completed_item_ids or set()
    for item in (*state.needs_you, *state.context):
        if item.id != item_id:
            continue
        target = AssistTarget(
            source_kind="attention_item",
            source_id=item.id,
            title=item.title,
            attention_item_id=item.id,
        )
        if _is_completed(target, done):
            return None
        return target
    for action in state.next_actions:
        if action.id != item_id and action.source_candidate_id != item_id:
            continue
        target = AssistTarget(
            source_kind="next_action",
            source_id=action.id,
            title=action.title,
            attention_item_id=action.source_candidate_id or action.id,
        )
        if _is_completed(target, done):
            return None
        return target
    return None


def resolve_assist_target(
    state: AttentionState,
    conversation: list[dict[str, Any]],
    completed_item_ids: set[str] | None = None,
) -> AssistTarget | None:
    """Resolve 'that' from the last structured item Enigma presented.

    Walks conversation newest-first. Free-text chat is never searched.
    ``attention_summary`` uses current (overlaid) world state.
    If nothing structured was presented, prefer ``next_actions[]``.
    """
    done = completed_item_ids or set()
    for item in reversed(conversation):
        kind = item.get("kind")
        if kind not in _STRUCTURED_THAT:
            continue
        if kind == "attention_item":
            target = _target_from_attention(item)
        elif kind == "next_action":
            target = _target_from_next_action(item)
        else:
            target = _target_from_summary(state)
        if target is None or _is_completed(target, done):
            continue
        return target
    fallback = _fallback_target(state)
    if fallback is None or _is_completed(fallback, done):
        return None
    return fallback


def _action_kind_for(target: AssistTarget) -> ActionKind:
    haystack = f"{target.attention_item_id} {target.title}".lower()
    if "brunch" in haystack:
        return "calendar_book"
    return "synthetic_note"


def make_assist_plan(target: AssistTarget, *, proposal_id: str | None = None) -> AssistPlan:
    action_kind = _action_kind_for(target)
    if action_kind == "calendar_book":
        description = (
            "I'll book this on the synthetic demo calendar. "
            "Nothing is written until you approve."
        )
    else:
        description = (
            "I'll record a synthetic demo draft for this. "
            "Nothing is written until you approve."
        )
    return AssistPlan(
        proposal_id=proposal_id or f"assist-{uuid4().hex[:12]}",
        title=target.title,
        description=description,
        action_label="Approve",
        source_item_id=target.attention_item_id,
        action_kind=action_kind,
    )


def execute_and_verify(
    plan: AssistPlan,
    services: SyntheticDemoServices,
) -> tuple[bool, str]:
    """Write to synthetic services, then read back. Never claims success on miss."""
    if plan.action_kind == "calendar_book":
        event = services.book_event(
            title=plan.title,
            start_at="2026-01-24T11:00:00+00:00",
            end_at="2026-01-24T13:00:00+00:00",
            location="Demo (synthetic)",
        )
        stored = services.get_event(event["id"])
        if stored is None or stored.get("title") != plan.title:
            return (
                False,
                "I couldn't verify the demo calendar write. Nothing was booked.",
            )
        return True, "Done — Saturday brunch is booked on the demo calendar."

    note = services.write_note(
        title=plan.title,
        body=f"Synthetic demo draft for {plan.title}.",
    )
    stored_note = services.get_note(note["id"])
    if stored_note is None or stored_note.get("title") != plan.title:
        return (
            False,
            "I couldn't verify the synthetic draft. Nothing was recorded.",
        )
    return True, f"Done — I recorded a synthetic draft for {plan.title}."


def assist_proposal_item(plan: AssistPlan, at: str) -> dict[str, Any]:
    return {
        "kind": "assist_proposal",
        "at": at,
        "proposal_id": plan.proposal_id,
        "proposal": plan.public_proposal(),
    }


def assist_result_item(
    *,
    proposal_id: str,
    ok: bool,
    message: str,
    at: str,
) -> dict[str, Any]:
    return {
        "kind": "assist_result",
        "at": at,
        "proposal_id": proposal_id,
        "ok": ok,
        "message": message,
    }


__all__ = [
    "BRUNCH_ITEM_ID",
    "AssistEffect",
    "AssistPlan",
    "AssistTarget",
    "SyntheticDemoServices",
    "apply_verified_assist_effect",
    "assist_effect_for",
    "assist_proposal_item",
    "assist_target_from_id",
    "assist_result_item",
    "execute_and_verify",
    "make_assist_plan",
    "overlay_completed_items",
    "overlay_session_world",
    "resolve_assist_target",
    "review_draft_next_action",
]
