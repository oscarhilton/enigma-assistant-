"""Apple Bridge client for Enigma Core (ticket M07 / ADR-002)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class AppleBridgeError(RuntimeError):
    """Raised when the local Apple Bridge cannot be reached or rejects the call."""


def _assert_local_base_url(base_url: str) -> None:
    """ADR-002: bearer token must only ever be sent to loopback (or UDS)."""
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        return
    raise AppleBridgeError(
        f"Apple Bridge base_url must be loopback (127.0.0.1 / localhost); got {base_url!r}"
    )


class AppleBridgeClient:
    """Thin localhost / Unix-socket client with bearer auth."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8765",
        token: str | None = None,
        *,
        unix_socket: str | None = None,
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.unix_socket = unix_socket
        self.timeout = timeout
        self._transport = transport
        # Injected transports are for tests; UDS never uses TCP host routing.
        if transport is None and unix_socket is None:
            _assert_local_base_url(self.base_url)

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise AppleBridgeError("Apple Bridge token is not configured")
        return {"Authorization": f"Bearer {self.token}"}

    def _client(self) -> httpx.AsyncClient:
        if self._transport is not None:
            return httpx.AsyncClient(
                base_url=self.base_url,
                transport=self._transport,
                timeout=self.timeout,
            )
        if self.unix_socket:
            transport = httpx.AsyncHTTPTransport(uds=self.unix_socket)
            # Host is ignored for UDS; keep a placeholder base URL.
            return httpx.AsyncClient(
                base_url="http://localhost",
                transport=transport,
                timeout=self.timeout,
            )
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def get_health(self) -> dict[str, object]:
        return await self.get_json("/health")

    async def get_capabilities(self) -> dict[str, object]:
        return await self.get_json("/capabilities")

    async def get_json(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> dict[str, object]:
        """GET a JSON object from the local bridge (public for source adapters)."""
        return await self._get_json(path, params=params)

    async def _get_json(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> dict[str, object]:
        async with self._client() as client:
            try:
                response = await client.get(path, headers=self._headers(), params=params)
            except httpx.HTTPError as exc:
                raise AppleBridgeError(f"Apple Bridge request failed: {exc}") from exc

        if response.status_code == 401:
            raise AppleBridgeError("Apple Bridge rejected bearer token")
        if response.status_code >= 400:
            raise AppleBridgeError(
                f"Apple Bridge returned HTTP {response.status_code}: {response.text}"
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise AppleBridgeError("Apple Bridge returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise AppleBridgeError("Apple Bridge returned a non-object JSON body")
        return payload
