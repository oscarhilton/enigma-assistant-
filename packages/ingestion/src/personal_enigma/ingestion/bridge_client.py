"""Apple Bridge client for Enigma Core (ticket M07 / ADR-002)."""

from __future__ import annotations

from typing import Any

import httpx


class AppleBridgeError(RuntimeError):
    """Raised when the local Apple Bridge cannot be reached or rejects the call."""


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
        return await self._get_json("/health")

    async def get_capabilities(self) -> dict[str, object]:
        return await self._get_json("/capabilities")

    async def _get_json(self, path: str) -> dict[str, object]:
        async with self._client() as client:
            try:
                response = await client.get(path, headers=self._headers())
            except httpx.HTTPError as exc:
                raise AppleBridgeError(f"Apple Bridge request failed: {exc}") from exc

        if response.status_code == 401:
            raise AppleBridgeError("Apple Bridge rejected bearer token")
        if response.status_code >= 400:
            raise AppleBridgeError(
                f"Apple Bridge returned HTTP {response.status_code}: {response.text}"
            )

        payload: Any = response.json()
        if not isinstance(payload, dict):
            raise AppleBridgeError("Apple Bridge returned a non-object JSON body")
        return payload
