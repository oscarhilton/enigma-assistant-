"""Apple Bridge client for Enigma Core (owned by ticket M07)."""

from __future__ import annotations


class AppleBridgeClient:
    """Thin localhost / Unix-socket client. Implemented in M07."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765", token: str | None = None) -> None:
        self.base_url = base_url
        self.token = token

    async def get_capabilities(self) -> dict[str, object]:
        raise NotImplementedError("Implemented in ticket M07")
