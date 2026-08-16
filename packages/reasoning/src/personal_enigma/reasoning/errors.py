"""Errors raised by the PAYG reasoning client."""


class PrivacyGateError(ValueError):
    """Raised when a payload is refused by the remote-transmission privacy gate."""


class ReasoningDisabledError(RuntimeError):
    """Raised when remote reasoning is disabled and a call is attempted."""
