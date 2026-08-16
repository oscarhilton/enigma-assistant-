"""ChatGPT / OpenAI chat route — inspector preview default on (M19)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from personal_enigma.privacy import (
    InspectionResult,
    RemoteInferenceConfig,
    inspect_transformed_context,
)
from personal_enigma.reasoning import (
    PaygReasoningService,
    ReasoningDisabledError,
    ReasoningMode,
)
from personal_enigma.reasoning.openai_transport import OpenAIChatTransport
from personal_enigma.transformation import TransformedContext


class ChatRequest(BaseModel):
    prompt: str = ""
    summary: str
    entities: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    may_transmit_remotely: bool = False
    confirm_send: bool = False
    preview_only: bool = True


class ChatResponse(BaseModel):
    preview: InspectionResult
    answer: str | None = None
    left_the_machine: bool = False
    remote_disabled: bool = False
    label: str


def _require_local_auth(authorization: str | None) -> None:
    expected = os.environ.get("ENIGMA_API_TOKEN", "local-dev-token")
    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing local bearer token",
        )


def install_chat_routes(app: FastAPI) -> None:
    @app.post("/external/chat", response_model=ChatResponse)
    def external_chat(
        body: ChatRequest,
        authorization: str | None = Header(default=None),
    ) -> ChatResponse:
        _require_local_auth(authorization)
        ctx = TransformedContext(
            summary=body.summary,
            entities=body.entities,
            metadata=dict(body.metadata),
            may_transmit_remotely=body.may_transmit_remotely,
        )
        mode_env = os.environ.get("ENIGMA_REASONING_MODE", "disabled").lower()
        remote_enabled = mode_env == "enabled"
        preview = inspect_transformed_context(
            ctx,
            remote=RemoteInferenceConfig(enabled=remote_enabled),
        )

        if body.preview_only or not body.confirm_send:
            return ChatResponse(
                preview=preview,
                answer=None,
                left_the_machine=False,
                remote_disabled=not remote_enabled,
                label="Preview only — nothing left the machine",
            )

        if not remote_enabled:
            return ChatResponse(
                preview=preview,
                answer=None,
                left_the_machine=False,
                remote_disabled=True,
                label="Remote inference disabled — Apple / local sources still work",
            )

        if not preview.can_send:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=preview.blocked_reason or "Privacy gate refused send",
            )

        service = PaygReasoningService(
            mode=ReasoningMode.ENABLED,
            transport=OpenAIChatTransport(),
            default_model=os.environ.get("ENIGMA_OPENAI_MODEL", "gpt-4o-mini"),
        )
        try:
            result = service.reason(ctx, prompt=body.prompt)
        except ReasoningDisabledError:
            return ChatResponse(
                preview=preview,
                answer=None,
                left_the_machine=False,
                remote_disabled=True,
                label="Remote inference disabled — Apple / local sources still work",
            )

        left = result.metadata.get("left_machine") == "true"
        return ChatResponse(
            preview=preview,
            answer=result.text,
            left_the_machine=left,
            remote_disabled=False,
            label=(
                "Response from hosted model — sanitised context only"
                if left
                else "Local stub — no hosted call"
            ),
        )
