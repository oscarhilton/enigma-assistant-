"""Deterministic authority over LLM Judge proposals (ADR-011)."""

from __future__ import annotations

from dataclasses import dataclass, field

from personal_enigma.evaluation.llm_judge.payload import JudgeCheckpointRequest
from personal_enigma.evaluation.llm_judge.schema import (
    JudgementAttention,
    JudgeResponse,
    StructuredJudgement,
)
from personal_enigma.reasoning.errors import PrivacyGateError
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.transformation import TransformedContext


class JudgeAuthorityError(ValueError):
    """Raised when code rejects a Judge proposal."""


@dataclass(frozen=True, slots=True)
class AuthorityResult:
    """Policy output: accepted judgements plus rejection reasons."""

    accepted: list[StructuredJudgement]
    rejected: list[tuple[str, str]] = field(default_factory=list)
    privacy_violations: int = 0
    schema_failures: int = 0

    @property
    def ok(self) -> bool:
        return self.privacy_violations == 0 and self.schema_failures == 0


def apply_code_authority(
    request: JudgeCheckpointRequest,
    response: JudgeResponse,
    *,
    must_suppress_ids: frozenset[str] | set[str] | None = None,
    max_judgements: int | None = None,
) -> AuthorityResult:
    """Validate schema-level response already parsed; enforce evidence + policy.

    Code retains final authority: invent evidence → reject; MUST_SUPPRESS
    candidates cannot keep ``must_surface`` attention.
    """
    evidence_ids = request.evidence_id_set()
    candidate_ids = request.candidate_id_set()
    suppress = set(must_suppress_ids or ())
    accepted: list[StructuredJudgement] = []
    rejected: list[tuple[str, str]] = []
    schema_failures = 0
    privacy_violations = 0

    if request.context is not None:
        try:
            _assert_context_safe(request.context)
        except PrivacyGateError as exc:
            privacy_violations += 1
            rejected.append(("*", f"privacy: {exc}"))
            return AuthorityResult(
                accepted=[],
                rejected=rejected,
                privacy_violations=privacy_violations,
                schema_failures=0,
            )

    seen: set[str] = set()
    for judgement in response.judgements:
        if max_judgements is not None and len(accepted) >= max_judgements:
            rejected.append((judgement.candidate_id, "budget: max_judgements"))
            continue
        if judgement.candidate_id not in candidate_ids:
            schema_failures += 1
            rejected.append((judgement.candidate_id, "unknown candidate_id"))
            continue
        if judgement.candidate_id in seen:
            schema_failures += 1
            rejected.append((judgement.candidate_id, "duplicate candidate_id"))
            continue
        bad_evidence = [eid for eid in judgement.evidence_ids if eid not in evidence_ids]
        if bad_evidence:
            schema_failures += 1
            rejected.append(
                (
                    judgement.candidate_id,
                    f"invented evidence_ids: {bad_evidence}",
                )
            )
            continue

        final = judgement
        if (
            judgement.candidate_id in suppress
            and judgement.attention is JudgementAttention.MUST_SURFACE
        ):
            # Policy wins: clamp to suppress rather than honouring model.
            final = judgement.model_copy(update={"attention": JudgementAttention.SUPPRESS})

        seen.add(judgement.candidate_id)
        accepted.append(final)

    return AuthorityResult(
        accepted=accepted,
        rejected=rejected,
        privacy_violations=privacy_violations,
        schema_failures=schema_failures,
    )


def _assert_context_safe(context: TransformedContext) -> TransformedContext:
    return assert_remote_safe(context)


__all__ = [
    "AuthorityResult",
    "JudgeAuthorityError",
    "apply_code_authority",
]
