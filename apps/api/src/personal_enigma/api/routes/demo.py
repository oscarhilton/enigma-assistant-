"""Demo Mode environment banner and status routes (D1 stub)."""

from __future__ import annotations

from fastapi import FastAPI

from personal_enigma.simulation import (
    DEMO_BANNER_TEXT,
    DemoEnvironment,
    EnvironmentMode,
    environment_mode_from_env,
)


def install_demo_routes(application: FastAPI) -> None:
    """Register ``/demo/banner`` and ``/demo/environment`` stubs."""

    @application.get("/demo/banner")
    def demo_banner() -> dict[str, str | bool]:
        mode = environment_mode_from_env()
        active = mode is EnvironmentMode.DEMO
        return {
            "active": active,
            "mode": mode.value,
            "text": DEMO_BANNER_TEXT if active else "",
        }

    @application.get("/demo/environment")
    def demo_environment(scenario: str = "alex-v1") -> dict[str, str | None]:
        mode = environment_mode_from_env()
        if mode is EnvironmentMode.DEMO:
            env = DemoEnvironment(scenario=scenario)
            return {
                "mode": env.mode.value,
                "scenario": env.scenario,
                "banner": env.banner_text,
                "storage_root": str(env.storage_root),
            }
        return {
            "mode": mode.value,
            "scenario": None,
            "banner": None,
            "storage_root": None,
        }
