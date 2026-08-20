"""Handoff schema contract + secret scrubbing."""

from __future__ import annotations

import json
from pathlib import Path

from tokens import DISPATCHER, bearer

from personal_enigma.cursor_relay.handoff import (
    load_handoff_schema,
    make_handoff,
    strip_secrets,
    validate_handoff,
)
from personal_enigma.cursor_relay.relay import RelayService


def test_schema_loads_from_repo() -> None:
    schema = load_handoff_schema()
    assert schema["title"] == "CloudReleaseConductorHandoff"


def test_make_handoff_validates() -> None:
    doc = make_handoff(
        branch="cursor/cloud-02-cursor-relay-mcp-a131",
        ticket_ids=["CLOUD-02"],
        rationale="schema contract",
        action_kind="request_review",
        pr_base="main",
        pr_head="cursor/cloud-02-cursor-relay-mcp-a131",
    )
    validate_handoff(doc)


def test_dispatch_response_validates(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "schema-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "ticket/cloud-02-cursor-relay-mcp",
            "prompt": "conductor smoke",
            "ticket_ids": ["CLOUD-02"],
            "job_brief": {"authorization": {"dry_run": True}},
        },
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    text = json.dumps(result)
    assert "CURSOR_API_KEY" not in text
    assert "test-token" not in text


def test_strip_secrets_removes_keys() -> None:
    scrubbed = strip_secrets(
        {
            "cursor_api_key": "secret",
            "authorization": "Bearer x",
            "ok": True,
            "nested": {"api_key": "nope", "keep": 1},
        }
    )
    assert "cursor_api_key" not in scrubbed
    assert "authorization" not in scrubbed
    assert scrubbed["nested"] == {"keep": 1}


def test_handoff_schema_file_present() -> None:
    path = Path(__file__).resolve().parents[3] / "docs" / "cloud-agents" / "handoff-schema.json"
    assert path.is_file()
