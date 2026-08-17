"""Disclosure routes — what left my machine? (SEC-02)."""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from personal_enigma.privacy.egress import EgressDisclosure, get_audited_egress_gate


class DisclosureListResponse(BaseModel):
    disclosures: list[EgressDisclosure] = Field(default_factory=list)


def _require_local_auth(authorization: str | None) -> None:
    expected = os.environ.get("ENIGMA_API_TOKEN", "local-dev-token")
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing local bearer token",
        )


def install_disclosure_routes(app: FastAPI) -> None:
    @app.get("/private/disclosure/recent", response_model=DisclosureListResponse)
    def recent_disclosures(
        limit: int = 20,
        authorization: str | None = Header(default=None),
    ) -> DisclosureListResponse:
        _require_local_auth(authorization)
        gate = get_audited_egress_gate()
        rows = gate.recent_disclosures(limit=min(max(limit, 1), 100))
        return DisclosureListResponse(disclosures=rows)
