"""Shadow Mode API stubs (S01) — banner / environment only."""

from __future__ import annotations

from fastapi import FastAPI

from personal_enigma.simulation import (
    SHADOW_BANNER_TEXT,
    EnvironmentMode,
    ShadowEnvironment,
    environment_mode_from_env,
)


def install_shadow_routes(application: FastAPI) -> None:
    """Register ``/shadow/*`` banner and environment stubs."""

    @application.get("/shadow/banner")
    def shadow_banner() -> dict[str, str | bool]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.SHADOW
        return {
            "active": active,
            "mode": mode.value,
            "text": SHADOW_BANNER_TEXT if active else "",
        }

    @application.get("/shadow/environment")
    def shadow_environment() -> dict[str, str | bool | None]:
        mode = environment_mode_from_env()
        if mode is EnvironmentMode.SHADOW:
            env = ShadowEnvironment()
            return {
                "mode": env.mode.value,
                "banner": env.banner_text,
                "storage_root": str(env.storage_root),
                "notifications_suppressed": env.notifications_suppressed,
            }
        return {
            "mode": mode.value,
            "banner": None,
            "storage_root": None,
            "notifications_suppressed": None,
        }
