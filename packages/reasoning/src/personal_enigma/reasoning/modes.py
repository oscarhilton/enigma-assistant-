"""Operating modes for remote PAYG reasoning."""

from enum import StrEnum


class ReasoningMode(StrEnum):
    """Remote inference posture.

    DISABLED — refuse remote work; never open a network connection.
    DRY_RUN — run privacy gate + usage hooks; never open a network connection.
    ENABLED — call the pluggable transport after the privacy gate passes.
    """

    DISABLED = "disabled"
    DRY_RUN = "dry_run"
    ENABLED = "enabled"
