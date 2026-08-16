"""Local-only embedding and vector index protocols."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts locally. Must not call hosted embedding APIs."""
        ...


@runtime_checkable
class VectorIndex(Protocol):
    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None:
        ...

    def search(self, vector: list[float], limit: int = 10) -> list[dict]:
        ...
