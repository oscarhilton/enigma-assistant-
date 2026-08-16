from personal_enigma.transformation import TransformedContext


def test_transformed_context_defaults_no_remote() -> None:
    ctx = TransformedContext(summary="placeholder")
    assert ctx.may_transmit_remotely is False
    assert ctx.entities == []
