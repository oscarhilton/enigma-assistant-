"""Infer privacy-safe relations from evidence id patterns (R-L09).

General heuristics only — no scenario-specific names. Uses evidence structure
(e.g. mail supply + open reminder) to express blocker resolution causality.
"""

from __future__ import annotations

import re
from datetime import datetime

from personal_enigma.transformation.relations import SemanticRelation

_RESOURCE_KEYWORDS = ("figma", "link", "attachment", "file", "tokens")
_MAIL_RE = re.compile(r"^mail-(?P<party>[^-]+)-(?P<topic>.+)$")
_REM_RE = re.compile(r"^rem-(?P<topic>.+)$")


def _topic_tokens(*parts: str) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        for segment in part.replace("_", "-").split("-"):
            slug = segment.lower().strip()
            if len(slug) >= 3:
                tokens.add(slug)
            if slug.endswith("s") and len(slug) > 3:
                tokens.add(slug[:-1])
    return tokens


def _task_subject(obligation_id: str) -> str:
    return f"TASK_{obligation_id.removeprefix('obligation_').upper()}"


def _resource_object(evidence_id: str) -> str:
    lower = evidence_id.lower()
    for keyword in _RESOURCE_KEYWORDS:
        if keyword in lower:
            return f"RESOURCE_{keyword.upper()}"
    mail_match = _MAIL_RE.match(evidence_id)
    if mail_match:
        topic = mail_match.group("topic").upper().replace("-", "_")
        return f"RESOURCE_{topic}"
    return f"RESOURCE_{evidence_id.upper().replace('-', '_')}"


def _mail_supply_score(
    mail_id: str,
    *,
    reminder_ids: list[str],
) -> tuple[int, int]:
    mail_tokens = _topic_tokens(mail_id)
    rem_tokens = _topic_tokens(*reminder_ids)
    overlap = len(mail_tokens & rem_tokens)
    resource_boost = 2 if _is_resource_evidence(mail_id) else 0
    return overlap + resource_boost, overlap


def _select_supply_mail(
    evidence_ids: list[str],
    *,
    reminder_ids: list[str],
) -> str | None:
    mails = [eid for eid in evidence_ids if eid.startswith("mail-")]
    if not mails or not reminder_ids:
        return None
    scored: list[tuple[tuple[int, int, int], str]] = []
    for mail_id in mails:
        score, overlap = _mail_supply_score(mail_id, reminder_ids=reminder_ids)
        if score > 0 and overlap > 0:
            scored.append(((score, overlap, -evidence_ids.index(mail_id)), mail_id))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def _supplier_pseudonym(*, ordinal: int) -> str:
    letter = chr(ord("A") + min(ordinal, 25))
    return f"PERSON_{letter}"


def _is_resource_evidence(evidence_id: str) -> bool:
    lower = evidence_id.lower()
    return any(keyword in lower for keyword in _RESOURCE_KEYWORDS)


def infer_relations_from_evidence(
    *,
    obligation_id: str,
    evidence_ids: list[str],
    checkpoint_at: datetime | None = None,
) -> list[SemanticRelation]:
    """Build relations[] for one obligation from observable evidence ids."""
    relations: list[SemanticRelation] = []
    task = _task_subject(obligation_id)
    reminder_ids = [eid for eid in evidence_ids if eid.startswith("rem-")]
    resource_ids = [eid for eid in evidence_ids if _is_resource_evidence(eid)]

    supply_mail = _select_supply_mail(evidence_ids, reminder_ids=reminder_ids)
    if supply_mail and reminder_ids:
        resource = _resource_object(supply_mail)
        mails_before = [eid for eid in evidence_ids if eid.startswith("mail-")]
        ordinal = mails_before.index(supply_mail) if supply_mail in mails_before else 0
        resolved_at = (
            checkpoint_at.isoformat() if checkpoint_at is not None else "DATE_T0"
        )
        relations.append(
            SemanticRelation(
                type="BLOCKED_BY",
                subject=task,
                object=resource,
                state="resolved",
                resolved_by=_supplier_pseudonym(ordinal=ordinal),
                resolved_at=resolved_at,
                causal=f"{resource} arrival made {task} actionable",
            )
        )
        relations.append(
            SemanticRelation(
                type="SUPPLIED",
                subject=_supplier_pseudonym(ordinal=ordinal),
                object=resource,
                state="delivered",
                causal=f"{resource} supplied for {task}",
            )
        )
        return relations

    explicit_resource = [eid for eid in resource_ids if not eid.startswith("rem-")]
    if explicit_resource:
        resource = _resource_object(explicit_resource[0])
        relations.append(
            SemanticRelation(
                type="BLOCKED_BY",
                subject=task,
                object=resource,
                state="resolved",
                causal="resource_evidence_present_in_candidate",
            )
        )
        return relations

    if reminder_ids:
        relations.append(
            SemanticRelation(
                type="WAITING_ON",
                subject=task,
                object=f"EVIDENCE_{reminder_ids[0].upper().replace('-', '_')}",
                state="open",
                causal="open_reminder_without_resolution_resource",
            )
        )
    return relations


__all__ = ["infer_relations_from_evidence"]
