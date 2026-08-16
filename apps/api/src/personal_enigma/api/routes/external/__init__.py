"""External sanitised API surface (M18) — never expose raw private tables."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from personal_enigma.attention import AttentionKind
from personal_enigma.privacy import (
    PrivacyInvariantError,
    RemoteInferenceConfig,
    assert_remote_payload_safe,
)


class CapabilityStatus(BaseModel):
    calendar: dict[str, Any] = Field(
        default_factory=lambda: {"available": True, "authorised": False}
    )
    reminders: dict[str, Any] = Field(
        default_factory=lambda: {"available": True, "authorised": False}
    )
    contacts: dict[str, Any] = Field(
        default_factory=lambda: {"available": True, "authorised": False}
    )
    notes: dict[str, Any] = Field(
        default_factory=lambda: {
            "available": True,
            "authorised": False,
            "quality": "best_effort",
        }
    )


class SanitisedAttentionItem(BaseModel):
    title: str
    body: str
    kind: AttentionKind
    score: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)


_DEMO_ATTENTION: list[SanitisedAttentionItem] = [
    SanitisedAttentionItem(
        title="Review proposal",
        body="Due Friday; already in Reminders.",
        kind=AttentionKind.EXPLICIT_REMINDER,
        score=0.9,
        evidence_ids=["rem_fixture_1"],
    )
]


def _require_local_auth(authorization: str | None) -> None:
    expected = os.environ.get("ENIGMA_API_TOKEN", "local-dev-token")
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing local bearer token",
        )


def install_external_routes(app: FastAPI) -> None:
    @app.get("/external/capabilities", response_model=CapabilityStatus)
    def external_capabilities(
        authorization: str | None = Header(default=None),
    ) -> CapabilityStatus:
        _require_local_auth(authorization)
        return CapabilityStatus()

    @app.get("/external/attention", response_model=list[SanitisedAttentionItem])
    def external_attention(
        authorization: str | None = Header(default=None),
    ) -> list[SanitisedAttentionItem]:
        _require_local_auth(authorization)
        # Ensure list items are structurally safe as remote-shaped dicts.
        for item in _DEMO_ATTENTION:
            payload = {
                "summary": item.title,
                "entities": [],
                "metadata": {},
                "may_transmit_remotely": False,
            }
            try:
                assert_remote_payload_safe(
                    payload,
                    remote=RemoteInferenceConfig(enabled=False),
                )
            except PrivacyInvariantError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                ) from exc
        return list(_DEMO_ATTENTION)

    @app.get("/external/private-person/{person_id}")
    def refuse_private_person(
        person_id: str,
        authorization: str | None = Header(default=None),
    ) -> None:
        _require_local_auth(authorization)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PrivatePerson records are not exposed on the external API",
        )
