"""Tests for evidence-based relation inference (R-L09)."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.transformation.relation_inference import infer_relations_from_evidence


def test_token_audit_supply_plus_reminder_yields_resolved_blocker() -> None:
    relations = infer_relations_from_evidence(
        obligation_id="obligation_token_audit",
        evidence_ids=["mail-jordan-tokens", "rem-token-audit", "mail-alex-tokens"],
        checkpoint_at=datetime(2026, 1, 19, 10, 0, tzinfo=UTC),
    )
    blocked = [r for r in relations if r.type == "BLOCKED_BY"]
    assert len(blocked) == 1
    rel = blocked[0]
    assert rel.subject == "TASK_TOKEN_AUDIT"
    assert rel.object == "RESOURCE_TOKENS"
    assert rel.state == "resolved"
    assert rel.resolved_by is not None
    assert "jordan" not in (rel.resolved_by or "").lower()
    assert rel.causal and "actionable" in rel.causal.lower()
    waiting = [r for r in relations if r.type == "WAITING_ON"]
    assert not waiting


def test_reminder_only_yields_waiting_on() -> None:
    relations = infer_relations_from_evidence(
        obligation_id="obligation_atlas_review",
        evidence_ids=["mail-atlas-ask"],
    )
    assert len(relations) == 0 or relations[0].type == "WAITING_ON"
