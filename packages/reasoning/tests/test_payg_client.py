"""Tests for PAYG reasoning client behaviour."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from personal_enigma.reasoning import (
    InMemoryUsageLogger,
    MockPaygTransport,
    NullPaygTransport,
    PaygReasoningService,
    PrivacyGateError,
    ReasoningDisabledError,
    ReasoningMode,
    build_reasoning_client,
)
from personal_enigma.transformation import TransformedContext


def _safe_context(**overrides: Any) -> TransformedContext:
    data: dict[str, Any] = {
        "summary": "Meeting with PERSON_A4F91C about project timeline",
        "entities": ["PERSON_A4F91C"],
        "metadata": {"source_type": "email"},
        "may_transmit_remotely": True,
    }
    data.update(overrides)
    return TransformedContext(**data)


def test_mock_provider_returns_result_and_logs_usage() -> None:
    logger = InMemoryUsageLogger()
    transport = MockPaygTransport(response_text="ranked: follow up")
    client = PaygReasoningService(
        mode=ReasoningMode.ENABLED,
        transport=transport,
        usage_logger=logger,
    )

    result = client.reason(_safe_context(), prompt="What matters next?")

    assert result.text == "ranked: follow up"
    assert result.dry_run is False
    assert len(transport.calls) == 1
    assert len(logger.records) == 1
    assert logger.records[0].prompt_tokens > 0
    assert logger.records[0].completion_tokens > 0
    assert logger.records[0].estimated_cost_usd is not None


def test_disabled_mode_raises_and_never_calls_transport() -> None:
    transport = MockPaygTransport()
    # DISABLED forces NullPaygTransport internally regardless of constructor arg.
    client = PaygReasoningService(mode=ReasoningMode.DISABLED, transport=transport)

    with pytest.raises(ReasoningDisabledError):
        client.reason(_safe_context())

    assert transport.calls == []
    assert isinstance(client._transport, NullPaygTransport)  # noqa: SLF001


def test_disabled_mode_never_opens_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network must not open in disabled mode")

    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    monkeypatch.setattr(socket, "create_connection", forbid_network)

    client = build_reasoning_client(mode=ReasoningMode.DISABLED)
    with pytest.raises(ReasoningDisabledError):
        client.reason(_safe_context())


def test_dry_run_validates_but_never_opens_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network must not open in dry-run mode")

    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    monkeypatch.setattr(socket, "create_connection", forbid_network)

    logger = InMemoryUsageLogger()
    spy = MockPaygTransport()
    client = PaygReasoningService(
        mode=ReasoningMode.DRY_RUN,
        transport=spy,
        usage_logger=logger,
    )

    result = client.reason(_safe_context(), prompt="preview send")

    assert result.dry_run is True
    assert result.text == ""
    assert spy.calls == []
    assert isinstance(client._transport, NullPaygTransport)  # noqa: SLF001
    assert len(logger.records) == 1
    assert logger.records[0].dry_run is True
    assert logger.records[0].mode is ReasoningMode.DRY_RUN


def test_privacy_gate_refuses_when_may_transmit_false() -> None:
    client = PaygReasoningService(
        mode=ReasoningMode.ENABLED,
        transport=MockPaygTransport(),
    )
    ctx = _safe_context(may_transmit_remotely=False)

    with pytest.raises(PrivacyGateError, match="may_transmit_remotely"):
        client.reason(ctx)


def test_rejects_non_transformed_context() -> None:
    client = PaygReasoningService(
        mode=ReasoningMode.ENABLED,
        transport=MockPaygTransport(),
    )

    with pytest.raises(PrivacyGateError, match="TransformedContext"):
        client.reason({"summary": "sneaky dict", "may_transmit_remotely": True})  # type: ignore[arg-type]


def test_rejects_unsanitised_email_in_summary() -> None:
    client = PaygReasoningService(
        mode=ReasoningMode.ENABLED,
        transport=MockPaygTransport(),
    )
    ctx = _safe_context(summary="Email alice@example.com about lunch")

    with pytest.raises(PrivacyGateError, match="(?i)email"):
        client.reason(ctx)


def test_rejects_private_person_marker_in_metadata() -> None:
    client = PaygReasoningService(
        mode=ReasoningMode.DRY_RUN,
    )
    ctx = _safe_context(summary="PrivatePerson dump in summary")

    with pytest.raises(PrivacyGateError, match="PrivatePerson"):
        client.reason(ctx)


def test_dry_run_also_enforces_privacy_gate() -> None:
    client = build_reasoning_client(mode="dry_run")
    with pytest.raises(PrivacyGateError):
        client.reason(_safe_context(may_transmit_remotely=False))


def test_enabled_requires_explicit_transport() -> None:
    with pytest.raises(ValueError, match="AuditedEgressGate or PaygTransport"):
        PaygReasoningService(mode=ReasoningMode.ENABLED)


def test_invalid_mode_string_is_actionable() -> None:
    with pytest.raises(ValueError, match="allowed values"):
        build_reasoning_client(mode="not-a-mode")


def test_default_usage_logger_is_null() -> None:
    from personal_enigma.reasoning.logging import NullUsageLogger

    client = PaygReasoningService(mode=ReasoningMode.DRY_RUN)
    assert isinstance(client.usage_logger, NullUsageLogger)
