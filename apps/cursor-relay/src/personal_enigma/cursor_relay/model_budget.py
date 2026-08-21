"""Model budgeting policy — default/green via omission; premium escalation gated."""

from __future__ import annotations

from typing import Any

from personal_enigma.cursor_relay.approval import ApprovalError

# Observed 2026-08-21 daily mix (212.8M tokens) — reference for operators/conductors.
OBSERVED_DAILY_USAGE_2026_08_21: tuple[tuple[str, float, float], ...] = (
    ("default (green)", 34.2, 16.1),
    ("composer-2.5-fast", 98.7, 46.4),
    ("cursor-grok-4.6-high-fast", 29.2, 13.7),
    ("Bugbot", 13.6, 6.4),
    ("cursor-grok-4.6-medium-fast", 21.3, 10.0),
    ("gpt-5.3-codex", 15.8, 7.4),
)

TARGET_DEFAULT_GREEN_SHARE_MIN = 60.0
TARGET_PREMIUM_SHARE_MAX = 30.0

_MIN_ESCALATION_REASON_LEN = 8
_MAX_ESCALATION_REASON_LEN = 240


def is_premium_model(model: str) -> bool:
    """True for explicit models that count as premium escalation (not default/green)."""

    mid = model.strip().lower()
    if not mid or mid == "composer-2":
        return False
    if mid.startswith("composer-2.5"):
        return True
    if "grok" in mid:
        return True
    if mid.startswith("gpt-5"):
        return True
    if "thinking" in mid:
        return True
    return False


def extract_model_escalation_reason(params: dict[str, Any]) -> str | None:
    """Read concise escalation reason from dispatch params or job brief."""

    direct = params.get("model_escalation_reason")
    if direct is not None and str(direct).strip():
        return str(direct).strip()

    brief = params.get("job_brief")
    if isinstance(brief, dict):
        top = brief.get("model_escalation_reason")
        if top is not None and str(top).strip():
            return str(top).strip()
        nested = brief.get("model_escalation")
        if isinstance(nested, dict):
            reason = nested.get("reason")
            if reason is not None and str(reason).strip():
                return str(reason).strip()
    return None


def enforce_model_escalation_policy(
    params: dict[str, Any],
    *,
    model: str | None,
) -> str | None:
    """Require a concise reason when a premium model is explicitly requested."""

    if not model or not is_premium_model(model):
        return extract_model_escalation_reason(params)

    reason = extract_model_escalation_reason(params)
    if reason is None:
        msg = (
            f"Premium model '{model}' requires model_escalation_reason "
            "(concise justification for escalation beyond default/green)"
        )
        raise ApprovalError(msg, code="model_escalation_reason_required")
    if len(reason) < _MIN_ESCALATION_REASON_LEN:
        msg = (
            f"model_escalation_reason too short (min {_MIN_ESCALATION_REASON_LEN} chars)"
        )
        raise ApprovalError(msg, code="model_escalation_reason_required")
    if len(reason) > _MAX_ESCALATION_REASON_LEN:
        msg = (
            f"model_escalation_reason too long (max {_MAX_ESCALATION_REASON_LEN} chars)"
        )
        raise ApprovalError(msg, code="model_escalation_reason_required")
    return reason


def model_budget_observed_fields(
    *,
    model: str | None,
    escalation_reason: str | None,
) -> dict[str, Any]:
    """Optional handoff fields for model budgeting audit."""

    fields: dict[str, Any] = {}
    if model and is_premium_model(model):
        fields["model_escalation"] = True
    if escalation_reason:
        fields["model_escalation_reason"] = escalation_reason
    return fields
