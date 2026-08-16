"""Remote inference enablement — default off so Apple paths stay local-testable."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RemoteInferenceConfig:
    """Whether hosted-model transmission is permitted at all.

    Default ``enabled=False``: Apple Calendar / Reminders / Contacts / Notes
    ingestion and local transformation remain usable without any remote call.
    """

    enabled: bool = False


def may_send_remotely(
    config: RemoteInferenceConfig,
    *,
    payload_allows_remote: bool,
) -> bool:
    """Return True only when both the global switch and payload gate are open."""
    return config.enabled and payload_allows_remote
