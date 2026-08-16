"""FastAPI application entrypoint (scaffold)."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    application = FastAPI(
        title="personal-enigma",
        version="0.1.0",
        description="Enigma Core — private personal context API",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "enigma-core"}

    return application


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("personal_enigma.api.main:app", host="127.0.0.1", port=8000, reload=False)
