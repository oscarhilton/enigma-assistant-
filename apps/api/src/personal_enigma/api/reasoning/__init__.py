"""API wiring for the PAYG reasoning client (disabled by default)."""

from __future__ import annotations

import os

from personal_enigma.reasoning import (
    PaygReasoningClient,
    PaygReasoningService,
    ReasoningMode,
    build_reasoning_client,
)

__all__ = ["PaygReasoningClient", "PaygReasoningService", "get_reasoning_client"]


def get_reasoning_client() -> PaygReasoningService:
    """Return the process reasoning client.

    Defaults to DISABLED so remote inference never opens a network connection
    unless explicitly enabled via ``ENIGMA_REASONING_MODE``.
    """
    mode = os.environ.get("ENIGMA_REASONING_MODE", ReasoningMode.DISABLED.value)
    return build_reasoning_client(mode=mode)
