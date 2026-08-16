"""Worker reasoning wiring stays disabled by default."""

from personal_enigma.reasoning import ReasoningMode
from personal_enigma.worker.reasoning import get_reasoning_client


def test_worker_reasoning_client_defaults_disabled(monkeypatch) -> None:
    monkeypatch.delenv("ENIGMA_REASONING_MODE", raising=False)
    client = get_reasoning_client()
    assert client.mode is ReasoningMode.DISABLED
