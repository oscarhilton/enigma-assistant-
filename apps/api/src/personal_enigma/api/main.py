"""FastAPI application entrypoint (scaffold)."""

from __future__ import annotations

from fastapi import FastAPI

from personal_enigma.api.routes.demo import install_demo_routes
from personal_enigma.api.routes.disclosure import install_disclosure_routes
from personal_enigma.api.routes.external import install_external_routes
from personal_enigma.api.routes.forget import install_forget_routes
from personal_enigma.api.routes.privacy_inspector import install_privacy_inspector_routes
from personal_enigma.api.routes.settings import install_settings_routes
from personal_enigma.api.routes.shadow import install_shadow_routes


def create_app() -> FastAPI:
    application = FastAPI(
        title="personal-enigma",
        version="0.1.0",
        description="Enigma Core — private personal context API",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "enigma-core"}

    install_settings_routes(application)
    install_privacy_inspector_routes(application)
    install_external_routes(application)
    install_disclosure_routes(application)
    install_forget_routes(application)
    install_demo_routes(application)
    install_shadow_routes(application)
    return application


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("personal_enigma.api.main:app", host="127.0.0.1", port=8000, reload=False)
