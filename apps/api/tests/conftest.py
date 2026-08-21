"""Shared pytest fixtures for API tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from personal_enigma.api.semantic_bootstrap import FixtureSemanticBootstrap, set_semantic_bootstrap


@pytest.fixture(autouse=True)
def kernel_semantic_router_oracle() -> Iterator[None]:
    """My Enigma kernel tests route semantic domain via the small-LLM router oracle."""
    set_semantic_bootstrap(FixtureSemanticBootstrap())
    yield
    set_semantic_bootstrap(None)
