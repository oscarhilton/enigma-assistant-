"""Privacy inspector API — preview only; never uploads (M17)."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from personal_enigma.domain import SourceType
from personal_enigma.privacy import (
    InspectionResult,
    RemoteInferenceConfig,
    inspect_transformed_context,
)
from personal_enigma.transformation import TransformedContext


class InspectRequest(BaseModel):
    summary: str
    entities: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    may_transmit_remotely: bool = False
    source_type: SourceType | None = None
    remote_enabled: bool = False
    cancel: bool = False


def install_privacy_inspector_routes(app: FastAPI) -> None:
    @app.post("/privacy/inspect", response_model=InspectionResult)
    def privacy_inspect(body: InspectRequest) -> InspectionResult:
        ctx = TransformedContext(
            summary=body.summary,
            entities=body.entities,
            metadata=dict(body.metadata),
            may_transmit_remotely=body.may_transmit_remotely,
        )
        return inspect_transformed_context(
            ctx,
            source_type=body.source_type,
            remote=RemoteInferenceConfig(enabled=body.remote_enabled),
            cancel=body.cancel,
        )
