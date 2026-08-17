"""Semantic gap audit for transform output vs judge evidence (R-L09)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from personal_enigma.evaluation.observations import CheckpointSnapshot
from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.relation_inference import (
    _is_resource_evidence,
    _task_subject,
)


class SemanticGapClass(StrEnum):
    DEPENDENCY_BLOCKER = "dependency_blocker"
    RESOLUTION_EVIDENCE = "resolution_evidence"
    CAUSAL_RELATION = "causal_relation"
    ACTIONABILITY_CONTEXT = "actionability_context"


@dataclass
class SemanticGap:
    gap_class: SemanticGapClass
    status: str
    task_subject: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "gap_class": self.gap_class.value,
            "status": self.status,
            "task_subject": self.task_subject,
            "notes": self.notes,
        }


@dataclass
class OfflineTransformGate:
    checkpoint_id: str
    evidence_ids_present: bool = False
    raw_identity_absent: bool = False
    generic_relation_graph_present: bool = False
    dependency_represented: bool = False
    blocker_resolution_represented: bool = False
    causal_actionability_transition: bool = False
    no_evaluator_labels: bool = True
    semantic_gaps: list[SemanticGap] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.evidence_ids_present
            and self.raw_identity_absent
            and self.generic_relation_graph_present
            and self.dependency_represented
            and self.blocker_resolution_represented
            and self.causal_actionability_transition
            and self.no_evaluator_labels
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "passed": self.passed,
            "evidence_ids_present": self.evidence_ids_present,
            "raw_identity_absent": self.raw_identity_absent,
            "generic_relation_graph_present": self.generic_relation_graph_present,
            "dependency_represented": self.dependency_represented,
            "blocker_resolution_represented": self.blocker_resolution_represented,
            "causal_actionability_transition": self.causal_actionability_transition,
            "no_evaluator_labels": self.no_evaluator_labels,
            "semantic_gaps": [g.as_dict() for g in self.semantic_gaps],
        }


_EVALUATOR_LABELS = (
    "must_surface",
    "must_stay_quiet",
    "must_suppress",
    "MUST_SURFACE",
    "MUST_STAY_QUIET",
)
_IDENTITY_MARKERS = ("alex", "elena", "maya", "jordan", "sam", "@", ".com")


def _contains_identity_marker(text: str, marker: str) -> bool:
    if marker in ("@", ".com"):
        return marker in text
    return re.search(rf"\b{re.escape(marker)}\b", text, flags=re.IGNORECASE) is not None


def _identity_leak(text: str) -> bool:
    return any(_contains_identity_marker(text, marker) for marker in _IDENTITY_MARKERS)


def _candidate_needs_blocker_resolution(
    *,
    obligation_id: str,
    evidence_ids: list[str],
) -> bool:
    reminders = [eid for eid in evidence_ids if eid.startswith("rem-")]
    if not reminders:
        return False
    mails = [eid for eid in evidence_ids if eid.startswith("mail-")]
    if not mails:
        return False
    obl = obligation_id.lower()
    for mail_id in mails:
        if _is_resource_evidence(mail_id):
            return True
        mail_topic = mail_id.split("-", 2)[-1].lower()
        if any(token in mail_topic for token in obl.replace("obligation_", "").split("_")):
            return True
        if any(token in mail_topic for rem in reminders for token in rem.split("-")):
            return True
    return False


def _relations_for_task(ctx: TransformedContext, task: str) -> list[Any]:
    return [rel for rel in ctx.relations if rel.subject == task]


def audit_offline_transform_gate(
    snapshot: CheckpointSnapshot,
    ctx: TransformedContext,
) -> OfflineTransformGate:
    """Checklist gate for regression checkpoints before live re-gate."""
    gate = OfflineTransformGate(checkpoint_id=snapshot.checkpoint_id)
    identity_blob = " ".join(ctx.entities).lower()
    for rel in ctx.relations:
        identity_blob += " " + rel.model_dump_json().lower()
    identity_blob += " " + str(ctx.metadata).lower()

    gate.evidence_ids_present = all(
        cand.evidence_ids for cand in snapshot.candidate_set[:5]
    )
    gate.raw_identity_absent = not _identity_leak(identity_blob)
    gate.generic_relation_graph_present = len(ctx.relations) > 0
    gate.no_evaluator_labels = not any(
        label in (ctx.summary + identity_blob) for label in _EVALUATOR_LABELS
    )

    blocker_tasks: list[str] = []
    for cand in snapshot.candidate_set[:5]:
        for oid in cand.obligation_ids:
            if _candidate_needs_blocker_resolution(
                obligation_id=oid, evidence_ids=list(cand.evidence_ids)
            ):
                blocker_tasks.append(_task_subject(oid))

    if not blocker_tasks:
        gate.dependency_represented = True
        gate.blocker_resolution_represented = True
        gate.causal_actionability_transition = True
        return gate

    for task in blocker_tasks:
        rels = _relations_for_task(ctx, task)
        blocked = [r for r in rels if r.type == "BLOCKED_BY"]
        resolved = [r for r in blocked if r.state == "resolved"]
        waiting_only = [r for r in rels if r.type == "WAITING_ON" and r.state == "open"]

        if not blocked:
            gate.semantic_gaps.append(
                SemanticGap(
                    gap_class=SemanticGapClass.DEPENDENCY_BLOCKER,
                    status="LOST",
                    task_subject=task,
                    notes="Expected BLOCKED_BY from supply mail + reminder evidence",
                )
            )
        else:
            gate.dependency_represented = True

        if not resolved:
            gate.semantic_gaps.append(
                SemanticGap(
                    gap_class=SemanticGapClass.RESOLUTION_EVIDENCE,
                    status="LOST",
                    task_subject=task,
                    notes="Blocker not marked resolved despite supply evidence",
                )
            )
        else:
            gate.blocker_resolution_represented = True
            if not any(r.causal and "actionable" in r.causal.lower() for r in resolved):
                gate.semantic_gaps.append(
                    SemanticGap(
                        gap_class=SemanticGapClass.CAUSAL_RELATION,
                        status="LOST",
                        task_subject=task,
                        notes="Missing causal transition to actionable state",
                    )
                )
            else:
                gate.causal_actionability_transition = True

        if waiting_only and resolved:
            gate.semantic_gaps.append(
                SemanticGap(
                    gap_class=SemanticGapClass.ACTIONABILITY_CONTEXT,
                    status="CONTRADICTS",
                    task_subject=task,
                    notes="WAITING_ON open coexists with resolved BLOCKED_BY",
                )
            )
        elif waiting_only and not resolved:
            gate.semantic_gaps.append(
                SemanticGap(
                    gap_class=SemanticGapClass.ACTIONABILITY_CONTEXT,
                    status="LOST",
                    task_subject=task,
                    notes="Only open WAITING_ON — task still framed as blocked",
                )
            )

    gate.dependency_represented = gate.dependency_represented and not any(
        g.gap_class == SemanticGapClass.DEPENDENCY_BLOCKER for g in gate.semantic_gaps
    )
    gate.blocker_resolution_represented = gate.blocker_resolution_represented and not any(
        g.gap_class == SemanticGapClass.RESOLUTION_EVIDENCE for g in gate.semantic_gaps
    )
    gate.causal_actionability_transition = (
        gate.causal_actionability_transition
        and not any(g.gap_class == SemanticGapClass.CAUSAL_RELATION for g in gate.semantic_gaps)
        and not any(
            g.gap_class == SemanticGapClass.ACTIONABILITY_CONTEXT and g.status == "LOST"
            for g in gate.semantic_gaps
        )
    )
    return gate


__all__ = [
    "OfflineTransformGate",
    "SemanticGap",
    "SemanticGapClass",
    "audit_offline_transform_gate",
]
