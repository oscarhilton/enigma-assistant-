"""Synthetic HIGH-sensitivity canaries for Alex demo security crash-testing.

**FICTIONAL / SYNTHETIC ONLY** — never real personal data. Part of the
**security overlay** (``alex_security_overlay``), not Alex v0.2.1 behavioural
truth under ``scenarios/alex-v1/``. Used by SEC-02 (egress wire assertions),
SEC-07 (shadow reconstruction benchmark), and grep-based CI regression.

Threat IDs reference docs/architecture/personal-data-security.md (SEC-00).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_SYNTHETIC_MARKER = "FICTIONAL_SYNTHETIC_CANARY_ENIGMA_FIXTURE_ONLY"

_DATA_ROOT = Path(__file__).resolve().parent / "data" / "security_canaries"

SensitivityTier = Literal["LOW", "MODERATE", "HIGH"]


@dataclass(frozen=True, slots=True)
class SensitiveCanary:
    """One deliberately sensitive fictional record for security regression."""

    id: str
    category: str
    sensitivity: SensitivityTier
    raw_marker: str
    sentinel_strings: tuple[str, ...]
    allowed_shadow_features: tuple[str, ...]
    forbidden_remote_semantics: tuple[str, ...]
    title: str
    body_text: str
    source_type: str
    synthetic_marker: str = _SYNTHETIC_MARKER
    content_ref: str | None = None
    sec_ticket_refs: tuple[str, ...] = ("SEC-02", "SEC-07")

    # Backward-compatible aliases used by existing manifest/tests.
    @property
    def canary_id(self) -> str:
        return self.id

    @property
    def sensitivity_tier(self) -> SensitivityTier:
        return self.sensitivity


# Legacy alias — prefer ``SensitiveCanary``.
AlexSensitiveCanary = SensitiveCanary


def _read_body(filename: str, *, inline_fallback: str) -> str:
    path = _DATA_ROOT / filename
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return inline_fallback


ALEX_SENSITIVE_CANARIES: tuple[SensitiveCanary, ...] = (
    SensitiveCanary(
        id="canary-medical-diagnosis",
        category="medical",
        sensitivity="HIGH",
        raw_marker="SYNTHETIC_CANARY_MEDICAL_DIAGNOSIS_FICTADHD_v1",
        sentinel_strings=(
            "SYNTHETIC_CANARY_MEDICAL_DIAGNOSIS_FICTADHD_v1",
            "Dr Fictional Practice — appointment 2026-02-14",
        ),
        allowed_shadow_features=(),
        forbidden_remote_semantics=(
            "diagnosis",
            "medical_condition",
            "anxiety_disorder",
            "gp_appointment",
        ),
        title="GP follow-up (FICTIONAL)",
        body_text=_read_body(
            "medical_appointment.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "Subject: GP follow-up — fictional test case only.\n"
                "Discussion notes: Generalised anxiety disorder (fictional).\n"
                "SYNTHETIC_CANARY_MEDICAL_DIAGNOSIS_FICTADHD_v1\n"
                "Dr Fictional Practice — appointment 2026-02-14\n"
            ),
        ),
        source_type="note",
        content_ref="data/security_canaries/medical_appointment.md",
    ),
    SensitiveCanary(
        id="canary-payroll-salary",
        category="payroll",
        sensitivity="HIGH",
        raw_marker="SYNTHETIC_CANARY_SALARY_GBP_87420_FICTIONAL",
        sentinel_strings=(
            "SYNTHETIC_CANARY_SALARY_GBP_87420_FICTIONAL",
            "Annual base: £87,420.00 (fictional payroll slip)",
        ),
        allowed_shadow_features=(),
        forbidden_remote_semantics=(
            "salary",
            "compensation",
            "payroll_amount",
            "annual_income",
        ),
        title="January payroll (FICTIONAL)",
        body_text=_read_body(
            "payroll_notice.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "Northwind Example Ltd — fictional payroll notice.\n"
                "SYNTHETIC_CANARY_SALARY_GBP_87420_FICTIONAL\n"
                "Annual base: £87,420.00 (fictional payroll slip)\n"
            ),
        ),
        source_type="mail",
        content_ref="data/security_canaries/payroll_notice.md",
    ),
    SensitiveCanary(
        id="canary-home-address",
        category="location",
        sensitivity="MODERATE",
        raw_marker="SYNTHETIC_CANARY_ADDRESS_48_EXAMPLE_STREET",
        sentinel_strings=(
            "SYNTHETIC_CANARY_ADDRESS_48_EXAMPLE_STREET",
            "48 Example Street, Fictionalborough, FB1 2XY",
        ),
        allowed_shadow_features=("city_region",),
        forbidden_remote_semantics=(
            "street_address",
            "postcode",
            "home_location",
            "delivery_address",
        ),
        title="Delivery address (FICTIONAL)",
        body_text=_read_body(
            "home_address.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "Ship to: Alex Morgan (fictional persona)\n"
                "SYNTHETIC_CANARY_ADDRESS_48_EXAMPLE_STREET\n"
                "48 Example Street, Fictionalborough, FB1 2XY\n"
            ),
        ),
        source_type="note",
        content_ref="data/security_canaries/home_address.md",
    ),
    SensitiveCanary(
        id="canary-bank-account",
        category="finance",
        sensitivity="HIGH",
        raw_marker="SYNTHETIC_CANARY_SORT_40-00-00_ACCT_12345678",
        sentinel_strings=(
            "SYNTHETIC_CANARY_SORT_40-00-00_ACCT_12345678",
            "Sort 40-00-00 · Account 12345678 (fictional)",
        ),
        allowed_shadow_features=(),
        forbidden_remote_semantics=(
            "bank_account",
            "sort_code",
            "account_number",
            "direct_debit",
        ),
        title="Direct debit setup (FICTIONAL)",
        body_text=_read_body(
            "bank_account.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "Fictional direct-debit mandate — not a real account.\n"
                "SYNTHETIC_CANARY_SORT_40-00-00_ACCT_12345678\n"
                "Sort 40-00-00 · Account 12345678 (fictional)\n"
            ),
        ),
        source_type="mail",
        content_ref="data/security_canaries/bank_account.md",
    ),
    SensitiveCanary(
        id="canary-relationship-private",
        category="relationship",
        sensitivity="MODERATE",
        raw_marker="SYNTHETIC_CANARY_RELATIONSHIP_ELENA_FICTIONAL",
        sentinel_strings=(
            "SYNTHETIC_CANARY_RELATIONSHIP_ELENA_FICTIONAL",
            "I don't want my parents to know we're trying IVF (fictional)",
        ),
        allowed_shadow_features=("OPEN_WORK_COMMITMENT",),
        forbidden_remote_semantics=(
            "ivf",
            "relationship_status",
            "partner_name",
            "family_secret",
        ),
        title="Private message draft (FICTIONAL)",
        body_text=_read_body(
            "relationship_private.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "Draft to Elena (fictional partner) — synthetic only.\n"
                "SYNTHETIC_CANARY_RELATIONSHIP_ELENA_FICTIONAL\n"
                "I don't want my parents to know we're trying IVF (fictional)\n"
            ),
        ),
        source_type="note",
        content_ref="data/security_canaries/relationship_private.md",
    ),
    SensitiveCanary(
        id="canary-api-token",
        category="credentials",
        sensitivity="HIGH",
        raw_marker="sk_test_FAKE_SECRET_SYNTHETIC_CANARY_123",
        sentinel_strings=(
            "sk_test_FAKE_SECRET_SYNTHETIC_CANARY_123",
            "SYNTHETIC_CANARY_PASSWORD_DemoOnly_NeverReal",
        ),
        allowed_shadow_features=(),
        forbidden_remote_semantics=(
            "api_key",
            "password",
            "secret_token",
            "credential",
        ),
        title="Local dev credentials (FICTIONAL)",
        body_text=_read_body(
            "api_token.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "Rotate these fictional credentials immediately in any real env.\n"
                "ENIGMA_DEMO_API_KEY=sk_test_FAKE_SECRET_SYNTHETIC_CANARY_123\n"
                "db_password=SYNTHETIC_CANARY_PASSWORD_DemoOnly_NeverReal\n"
            ),
        ),
        source_type="note",
        content_ref="data/security_canaries/api_token.md",
    ),
    SensitiveCanary(
        id="canary-confidential-company-doc",
        category="confidential_work",
        sensitivity="HIGH",
        raw_marker="SYNTHETIC_CANARY_CONFIDENTIAL_NORTHWIND_Q2_LAYOFFS",
        sentinel_strings=(
            "SYNTHETIC_CANARY_CONFIDENTIAL_NORTHWIND_Q2_LAYOFFS",
            "CONFIDENTIAL — Project Nightingale headcount reduction (fictional)",
        ),
        allowed_shadow_features=("OPEN_WORK_COMMITMENT", "due_bucket"),
        forbidden_remote_semantics=(
            "layoff",
            "headcount_reduction",
            "project_nightingale",
            "confidential_codename",
            "workforce_reduction",
        ),
        title="Leadership deck excerpt (FICTIONAL)",
        body_text=_read_body(
            "confidential_company_doc.md",
            inline_fallback=(
                f"{_SYNTHETIC_MARKER}\n\n"
                "CONFIDENTIAL — Project Nightingale headcount reduction (fictional)\n"
                "SYNTHETIC_CANARY_CONFIDENTIAL_NORTHWIND_Q2_LAYOFFS\n"
                "Draft only — 12 fictional roles under review in Q2.\n"
            ),
        ),
        source_type="mail",
        content_ref="data/security_canaries/confidential_company_doc.md",
    ),
)

ALL_CANARY_SENTINELS: tuple[str, ...] = tuple(
    sentinel
    for canary in ALEX_SENSITIVE_CANARIES
    for sentinel in canary.sentinel_strings
)

CANARY_BY_ID: dict[str, SensitiveCanary] = {
    canary.id: canary for canary in ALEX_SENSITIVE_CANARIES
}


def assert_canary_pack_complete() -> None:
    """Validate manifest shape — called from pytest."""
    required_categories = {
        "medical",
        "payroll",
        "location",
        "finance",
        "relationship",
        "credentials",
        "confidential_work",
    }
    seen = {canary.category for canary in ALEX_SENSITIVE_CANARIES}
    missing = required_categories - seen
    if missing:
        raise AssertionError(f"Missing canary categories: {sorted(missing)}")
    for canary in ALEX_SENSITIVE_CANARIES:
        if canary.synthetic_marker != _SYNTHETIC_MARKER:
            raise AssertionError(f"{canary.id}: missing shared synthetic marker")
        if _SYNTHETIC_MARKER not in canary.body_text:
            raise AssertionError(f"{canary.id}: body missing synthetic marker")
        if not canary.sentinel_strings:
            raise AssertionError(f"{canary.id}: no sentinel strings")
        if canary.raw_marker not in canary.sentinel_strings:
            raise AssertionError(f"{canary.id}: raw_marker must appear in sentinel_strings")
        if not canary.forbidden_remote_semantics:
            raise AssertionError(f"{canary.id}: forbidden_remote_semantics required")


__all__ = [
    "ALL_CANARY_SENTINELS",
    "ALEX_SENSITIVE_CANARIES",
    "AlexSensitiveCanary",
    "CANARY_BY_ID",
    "SensitiveCanary",
    "SensitivityTier",
    "assert_canary_pack_complete",
]
