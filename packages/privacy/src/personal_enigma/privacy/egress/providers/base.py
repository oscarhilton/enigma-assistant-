"""Provider response from audited egress — no direct HTTP outside this package subtree."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from personal_enigma.privacy.egress.classification import RemoteSafeContext


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Normalised provider outcome after wire transmission."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, str] = field(default_factory=dict)
    blocked: bool = False
    block_reason: str | None = None
    request_body: dict[str, Any] | None = None


@runtime_checkable
class EgressProvider(Protocol):
    """Internal provider adapter — invoked only by ``AuditedEgressGate``."""

    provider_name: str

    def send(
        self,
        context: RemoteSafeContext,
        *,
        transformed_context: Any | None = None,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
    ) -> ProviderResponse: ...
