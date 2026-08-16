from personal_enigma.domain import SourceType
from personal_enigma.privacy import (
    RemoteInferenceConfig,
    inspect_transformed_context,
)
from personal_enigma.transformation import TransformedContext


def test_inspect_notes_shows_high_and_redaction() -> None:
    ctx = TransformedContext(
        summary="Call dentist",
        entities=[],
        may_transmit_remotely=False,
    )
    result = inspect_transformed_context(
        ctx,
        source_type=SourceType.NOTE,
        remote=RemoteInferenceConfig(enabled=True),
    )
    assert result.privacy_level.value == "high"
    assert result.can_send is False
    assert any(r.field == "body_text" for r in result.redactions)
    assert "Revoking" in result.apple_permission_note


def test_cancel_blocks_send() -> None:
    ctx = TransformedContext(summary="ok", may_transmit_remotely=True)
    result = inspect_transformed_context(
        ctx,
        remote=RemoteInferenceConfig(enabled=True),
        cancel=True,
    )
    assert result.cancelled is True
    assert result.can_send is False
