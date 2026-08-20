"""Authenticated MCP relay to the Cursor Cloud Agents API.

Trust chain: ChatGPT (caller identity) → this relay → Cursor Cloud Agents API.
``CURSOR_API_KEY`` lives only in the relay process environment / secret store.
"""

from personal_enigma.cursor_relay.relay import RelayService

__all__ = ["RelayService"]
