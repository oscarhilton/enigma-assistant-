"""Test-only judge-v1 mock helpers (not part of production API)."""

from __future__ import annotations

import json
import re

from personal_enigma.reasoning.protocol import ReasoningResult
from personal_enigma.reasoning.transport import MockPaygTransport
from personal_enigma.transformation import TransformedContext


def judge_v1_json(
    *,
    decision: str = "suppress",
    evidence_ids: list[str] | None = None,
    next_action: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": decision,
            "priority": 4 if decision == "surface" else 1,
            "confidence": 0.9,
            "reason_codes": ["DEADLINE_APPROACHING"],
            "evidence_ids": evidence_ids or [],
        },
        "next_action": next_action,
    }
    return json.dumps(payload)


def surface_expenses_json() -> str:
    return judge_v1_json(
        decision="surface",
        evidence_ids=["mail-finance-expense", "rem-expenses"],
        next_action={
            "title": "Gather receipts",
            "action_type": "admin",
            "estimated_minutes": 5,
            "confidence": 0.85,
        },
    )


class PerCandidateJudgeMockTransport:
    """Returns suppress for most candidates; surfaces december expenses."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        self.calls.append({"model": model, "prompt": prompt, "context": context})
        candidate_match = re.search(
            r"Candidate:\s*\n(\{.*?\})\n\nContext snapshot:",
            prompt,
            re.DOTALL,
        )
        candidate_blob = candidate_match.group(1) if candidate_match else prompt
        evidence_match = re.search(r'"evidence_ids":\s*\[(.*?)\]', candidate_blob, re.DOTALL)
        evidence: list[str] = []
        if evidence_match:
            evidence = re.findall(r'"([^"]+)"', evidence_match.group(1))
        if "obligation_december_expenses" in candidate_blob:
            text = judge_v1_json(
                decision="surface",
                evidence_ids=evidence,
                next_action={
                    "title": "Gather receipts",
                    "action_type": "admin",
                    "estimated_minutes": 5,
                    "confidence": 0.85,
                },
            )
        else:
            text = judge_v1_json(decision="suppress", evidence_ids=evidence[:1])
        inner = MockPaygTransport(response_text=text)
        return inner.complete(model=model, prompt=prompt, context=context)
