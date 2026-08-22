"""In-memory durable assertion store stub for C29 gate tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from personal_enigma.domain.grounding import GroundedAssertion
from personal_enigma.domain.retention_gate import (
    ForgetCascadeResult,
    RetentionDecision,
    RetentionOutcome,
)


@dataclass
class _RetainedRow:
    assertion: GroundedAssertion
    decision: RetentionDecision
    derived_from_assertion_id: str | None = None


@dataclass
class InMemoryDurableAssertionStore:
    """Minimal store stub — maps retention decisions to retained rows with lineage."""

    _rows: dict[str, _RetainedRow] = field(default_factory=dict)
    _derivatives: dict[str, list[str]] = field(default_factory=dict)

    def store(self, assertion: GroundedAssertion, decision: RetentionDecision) -> str:
        if decision.outcome not in (RetentionOutcome.DURABLE, RetentionOutcome.TTL):
            msg = f"Store rejected non-durable outcome: {decision.outcome.value}"
            raise ValueError(msg)
        parent_ids = list(assertion.derived_from)
        parent_assertion_id = parent_ids[0] if len(parent_ids) == 1 else None
        self._rows[assertion.id] = _RetainedRow(
            assertion=assertion,
            decision=decision,
            derived_from_assertion_id=parent_assertion_id,
        )
        if parent_assertion_id is not None:
            self._derivatives.setdefault(parent_assertion_id, []).append(assertion.id)
        return assertion.id

    def forget(self, assertion_id: str) -> ForgetCascadeResult:
        deleted_assertions: list[str] = []
        deleted_derivatives: list[str] = []

        def _cascade(root_id: str) -> None:
            for child_id in list(self._derivatives.get(root_id, [])):
                if child_id in self._rows:
                    _cascade(child_id)
                    del self._rows[child_id]
                    deleted_derivatives.append(child_id)
            self._derivatives.pop(root_id, None)

        if assertion_id in self._rows:
            _cascade(assertion_id)
            del self._rows[assertion_id]
            deleted_assertions.append(assertion_id)

        return ForgetCascadeResult(
            root_assertion_id=assertion_id,
            deleted_assertion_ids=deleted_assertions,
            deleted_derived_ids=deleted_derivatives,
        )

    def list_retained_ids(self) -> list[str]:
        return sorted(self._rows)

    def get_decision(self, assertion_id: str) -> RetentionDecision | None:
        row = self._rows.get(assertion_id)
        return row.decision if row is not None else None
