"""External sanitised API surface (M18) — never expose raw private tables."""

from __future__ import annotations

import hmac
import os
import re
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from personal_enigma.attention import AttentionKind
from personal_enigma.privacy import (
    PrivacyInvariantError,
    RemoteInferenceConfig,
    assert_remote_payload_safe,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?!\w)"
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
    expected = f"Bearer {os.environ.get('ENIGMA_API_TOKEN', 'local-dev-token')}"
    provided = authorization or ""
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing local bearer token",
        )


def _assert_item_sanitised(item: SanitisedAttentionItem) -> None:
    blob = f"{item.title}\n{item.body}"
    if _EMAIL_RE.search(blob) or _PHONE_RE.search(blob):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="External attention item contains unsanitised PII",
        )
    payload = {
        "summary": f"{item.title}\n{item.body}",
        "entities": [],
        "metadata": {"source_type": "reminder"},
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


def install_external_routes(app: FastAPI) -> None:
    from personal_enigma.api.routes.external.chat import install_chat_routes

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
        for item in _DEMO_ATTENTION:
            _assert_item_sanitised(item)
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

    install_chat_routes(app)
