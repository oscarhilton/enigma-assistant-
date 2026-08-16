"""F-import-boundary zero-tolerance gates (mini fixtures only).

These are hard fails — not soft quality metrics. Any real domain, live URL,
secret-like string, or dense unexpected real-entity leakage fails the gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage
from personal_enigma.simulation.corpus.sanitise import (
    ImportBoundaryError,
    assert_import_boundary_clean,
    find_import_boundary_violations,
    is_reserved_demo_domain,
    sanitise_conversation,
    sanitise_conversation_detailed,
)

FIXTURE_ROOT = (
    Path(__file__).resolve().parent / "fixtures" / "corpus" / "import-boundary"
)


def _conversation_from_fixture(name: str) -> CorpusConversation:
    raw = json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
    emails = raw["emails"]
    messages: list[CorpusMessage] = []
    for index, email in enumerate(emails):
        messages.append(
            CorpusMessage(
                corpus_id="import-boundary-mini",
                conversation_id=str(raw["id"]),
                message_index=index,
                sender_name=str(email["sender_name"]),
                sender_email=str(email["sender_email"]),
                recipient_names=list(email.get("recipient_names") or []),
                recipient_emails=list(email.get("recipient_emails") or []),
                subject=str(email.get("subject") or ""),
                body_text=str(email.get("body_text") or ""),
            )
        )
    return CorpusConversation(id=str(raw["id"]), messages=messages)


def test_reserved_demo_domain_helpers() -> None:
    assert is_reserved_demo_domain("company-001.example")
    assert is_reserved_demo_domain("example.com")
    assert is_reserved_demo_domain("portal.test")
    assert not is_reserved_demo_domain("acme-widgets.com")
    assert not is_reserved_demo_domain("partner-docs.corp")


def test_corpus_real_domain_rewrite_zero_tolerance() -> None:
    dirty = _conversation_from_fixture("real-domain.json")
    # Pre-sanitise surface still has live domains — gate would fail hard.
    pre = find_import_boundary_violations(
        "\n".join(
            [
                dirty.messages[0].sender_email,
                dirty.messages[0].subject,
                dirty.messages[0].body_text,
            ]
        )
    )
    assert any(v.startswith("real_domain:") for v in pre)

    cleaned = sanitise_conversation(dirty, rewrite_seed="f-import-domain")
    for msg in cleaned.messages:
        assert msg.sender_email.endswith(".example")
        assert all(addr.endswith(".example") for addr in msg.recipient_emails)
        assert "acme-widgets.com" not in msg.body_text
        assert "riverside-college.edu" not in msg.body_text
        assert "northstar-design.io" not in msg.subject
        assert "@" not in msg.body_text or all(
            is_reserved_demo_domain(part.rsplit("@", 1)[-1])
            for part in msg.body_text.split()
            if "@" in part
        )
    assert_import_boundary_clean(cleaned)


def test_corpus_live_url_zero_tolerance() -> None:
    dirty = _conversation_from_fixture("live-url.json")
    pre = find_import_boundary_violations(dirty.messages[0].body_text)
    assert any(v.startswith("live_url:") for v in pre)

    cleaned = sanitise_conversation(dirty, rewrite_seed="f-import-url")
    body = cleaned.messages[0].body_text
    assert "partner-docs.corp" not in body
    assert "intranet.acme-widgets.com" not in body
    assert "portal.company-" in body
    assert "https://" in body
    for match_host in ("partner-docs.corp", "intranet.acme-widgets.com"):
        assert match_host not in body
    assert_import_boundary_clean(cleaned)


def test_corpus_secret_like_string_rejected_with_diagnostics() -> None:
    dirty = _conversation_from_fixture("secret-like.json")
    result = sanitise_conversation_detailed(dirty, rewrite_seed="f-import-secret")
    assert result.conversation is None
    assert result.diagnostics.rejected is True
    secret_reasons = [r for r in result.diagnostics.reasons if r.startswith("secret:")]
    assert secret_reasons, "rejection reason must record secret:* diagnostics"
    assert any("password" in r or "openai" in r or "github" in r for r in secret_reasons)

    with pytest.raises(ValueError, match="secret:"):
        sanitise_conversation(dirty)


def test_corpus_unexpected_real_entity_rejected() -> None:
    dirty = _conversation_from_fixture("unexpected-real-entity.json")
    result = sanitise_conversation_detailed(
        dirty, rewrite_seed="f-import-entity", reject_real_entities=True
    )
    assert result.conversation is None
    assert result.diagnostics.rejected is True
    assert any(
        r.startswith("unexpected_real_entity:") for r in result.diagnostics.reasons
    )

    # Hard gate on the raw fixture also fails (zero tolerance, not a soft metric).
    with pytest.raises(ImportBoundaryError, match="unexpected_real_entity"):
        assert_import_boundary_clean(dirty)


def test_clean_mini_background_still_passes_import_boundary() -> None:
    """Ordinary FinePersonas-shaped chatter must remain acceptable after rewrite."""
    conv = CorpusConversation(
        id="benign-background",
        messages=[
            CorpusMessage(
                corpus_id="import-boundary-mini",
                conversation_id="benign-background",
                message_index=0,
                sender_name="Casey Ng",
                sender_email="casey@riverside-college.edu",
                recipient_names=["Alex Morgan"],
                recipient_emails=["alex@morgan.example"],
                subject="Alumni newsletter",
                body_text="Here is this month's alumni update. No action needed.",
            )
        ],
    )
    cleaned = sanitise_conversation(conv, rewrite_seed="f-import-benign")
    assert_import_boundary_clean(cleaned)
    assert cleaned.messages[0].sender_email.endswith(".example")
