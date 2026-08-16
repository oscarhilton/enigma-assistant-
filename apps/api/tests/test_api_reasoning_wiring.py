"""API reasoning wiring stays disabled by default."""

from personal_enigma.api.reasoning import get_reasoning_client
from personal_enigma.reasoning import ReasoningMode


def test_api_reasoning_client_defaults_disabled(monkeypatch) -> None:
    monkeypatch.delenv("ENIGMA_REASONING_MODE", raising=False)
    client = get_reasoning_client()
    assert client.mode is ReasoningMode.DISABLED
