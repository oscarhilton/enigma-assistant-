from personal_enigma.reasoning.openai_transport import OpenAIChatTransport
from personal_enigma.transformation import TransformedContext


def test_openai_transport_no_key_stays_local() -> None:
    transport = OpenAIChatTransport(api_key="")
    result = transport.complete(
        model="gpt-4o-mini",
        prompt="What matters?",
        context=TransformedContext(
            summary="Review proposal",
            entities=["PERSON_A4F91C"],
            may_transmit_remotely=True,
        ),
    )
    assert result.metadata["left_machine"] == "false"
    assert "no api key" in result.text.lower() or "stub" in result.text.lower()
