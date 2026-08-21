"""Authenticated MCP relay to the Cursor Cloud Agents API.

Trust chain: ChatGPT (Secure MCP Tunnel) → this relay → Cursor Cloud Agents API.
``CURSOR_API_KEY`` and ``RELAY_TUNNEL_CALLER`` live only in the relay process
environment / secret store — never in MCP tool schemas or model arguments.
"""

from personal_enigma.cursor_relay.relay import RelayService

__all__ = ["RelayService"]
