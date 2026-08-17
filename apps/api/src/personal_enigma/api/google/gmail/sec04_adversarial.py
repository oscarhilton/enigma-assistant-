"""SEC-04 adversarial containment through real Gmail parser + vault path."""

from __future__ import annotations

from personal_enigma.api.google.gmail.pipeline import (
    assert_transform_excludes_body,
    build_test_egress_gate,
    transform_message_for_remote,
)
from personal_enigma.api.sec03_adversarial import (
    CaseVerdict,
    LayerVerdict,
    run_adversarial_case,
)
from personal_enigma.fixtures.adversarial_email_cases import (
    ADVERSARIAL_EMAIL_CASES,
    AdversarialEmailCase,
    ContainmentLayer,
)
from personal_enigma.ingestion.gmail_fixture import adversarial_case_to_gmail_json
from personal_enigma.ingestion.sources.gmail import GmailSource


def assert_parser_path_containment(case: AdversarialEmailCase) -> LayerVerdict:
    """SEC-03 case must survive real Gmail MIME parser — injection must not win."""
    raw = adversarial_case_to_gmail_json(case)
    source = GmailSource(access_token="fixture-token")
    parsed = source.parse_payload(raw.get("payload"))
    message = source.message_from_gmail(raw, parsed=parsed)

    assert parsed.untrusted is True
    assert message.body_text is not None

    # Parser must not drop synthetic marker — proves real path, not demo shortcut.
    if case.body_plain[:80] not in (message.body_text or ""):
        # HTML-only injection cases may differ in visible text extraction.
        if case.body_html is None:
            return LayerVerdict(
                ContainmentLayer.PROMPT_INJECTION,
                False,
                "parser dropped adversarial plain body content",
            )

    remote = transform_message_for_remote(message)
    if case.body_plain in remote.summary:
        return LayerVerdict(
            ContainmentLayer.EGRESS,
            False,
            "wholesale adversarial body in remote summary",
        )

    try:
        assert_transform_excludes_body(message, forbidden_substrings=())
    except AssertionError as exc:
        return LayerVerdict(ContainmentLayer.EGRESS, False, str(exc))

    gate = build_test_egress_gate()
    blocked = gate.send(message.body_text or "", purpose="conversation.orchestrate")
    if blocked.sent:
        return LayerVerdict(
            ContainmentLayer.EGRESS,
            False,
            "raw parsed body must not be sent via egress",
        )

    return LayerVerdict(
        ContainmentLayer.PROMPT_INJECTION,
        True,
        "real Gmail parser path; body untrusted and not promoted to remote summary",
    )


def run_adversarial_case_through_parser(case: AdversarialEmailCase) -> CaseVerdict:
    """Re-run one SEC-03 case through Gmail parser ingestion path."""
    base = run_adversarial_case(case)
    parser_verdict = assert_parser_path_containment(case)
    layers = (*base.layers, parser_verdict)
    passed = base.passed and parser_verdict.passed
    failure = base.failure_taxonomy
    if not parser_verdict.passed and failure is None:
        failure = f"parser_path: {parser_verdict.detail}"
    return CaseVerdict(
        case_id=case.case_id,
        passed=passed,
        layers=layers,
        failure_taxonomy=failure,
    )


def run_adversarial_parser_benchmark() -> list[CaseVerdict]:
    """All SEC-03 adversarial cases through real Gmail parser path."""
    return [run_adversarial_case_through_parser(case) for case in ADVERSARIAL_EMAIL_CASES]


__all__ = [
    "assert_parser_path_containment",
    "run_adversarial_case_through_parser",
    "run_adversarial_parser_benchmark",
]
