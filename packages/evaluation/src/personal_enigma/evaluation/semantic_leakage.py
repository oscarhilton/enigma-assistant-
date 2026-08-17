"""SEC-07 semantic leakage scoring — stub until shadow runner exists.

**Exact leakage:** literal canary sentinel strings in egress/shadow/stolen-dir
→ grep/hash fail (implemented in fixtures + privacy tests).

**Semantic leakage:** meaning survives despite redaction — e.g. ``£123,456`` in
source becomes ``salary around 123k`` in shadow. Scored by ``SemanticLeakageScorer``
once the shadow reconstruction benchmark runner lands (SEC-07).
"""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.fixtures.alex_sensitive_canaries import SensitiveCanary


@dataclass(frozen=True, slots=True)
class SemanticLeakageExample:
    """Documented semantic-leak pattern for SEC-07 benchmark calibration."""

    source_fragment: str
    shadow_fragment: str
    expected_score: float
    category: str


class SemanticLeakageScorer:
    """Stub scorer — full implementation pending SEC-07 shadow runner."""

    def score(self, shadow_text: str, canary: SensitiveCanary) -> float:
        """Return 0.0 when no semantic leakage; >0 when meaning survives strip."""
        raise NotImplementedError(
            "SemanticLeakageScorer requires SEC-07 shadow reconstruction runner"
        )

    def score_forbidden_semantics(
        self,
        shadow_text: str,
        forbidden: tuple[str, ...],
    ) -> float:
        """Stub — detect forbidden semantic categories in shadow export text."""
        raise NotImplementedError(
            "SemanticLeakageScorer requires SEC-07 shadow reconstruction runner"
        )

    @staticmethod
    def calibration_examples() -> tuple[SemanticLeakageExample, ...]:
        return (
            SemanticLeakageExample(
                source_fragment="£123,456",
                shadow_fragment="salary around 123k",
                expected_score=1.0,
                category="payroll",
            ),
            SemanticLeakageExample(
                source_fragment="Generalised anxiety disorder",
                shadow_fragment="recent mental health appointment",
                expected_score=1.0,
                category="medical",
            ),
            SemanticLeakageExample(
                source_fragment="Project Nightingale headcount reduction",
                shadow_fragment="Q2 workforce planning item",
                expected_score=0.5,
                category="confidential_work",
            ),
        )


__all__ = [
    "SemanticLeakageExample",
    "SemanticLeakageScorer",
]
