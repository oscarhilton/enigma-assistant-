"""Local embedding models — never call hosted embedding APIs."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Literal

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class FakeEmbeddingModel:
    """Deterministic hashing embedder for CI and offline tests.

    Similar token bags produce similar vectors so retrieval tests are meaningful
    without downloading model weights or touching the network.
    """

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be >= 8")
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            tokens = ["__empty__"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            # Hashing trick: several signed feature bumps per token.
            for offset in range(0, 16, 4):
                idx = int.from_bytes(digest[offset : offset + 2], "big") % self.dimensions
                sign = 1.0 if digest[offset + 2] % 2 == 0 else -1.0
                weight = 1.0 + digest[offset + 3] / 255.0
                vec[idx] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class LocalEmbeddingModel:
    """Optional on-device model hook (ONNX / local weights).

    Not wired yet — fails closed so callers cannot accidentally fall through to a
    hosted embedding API. Use :class:`FakeEmbeddingModel` in CI.
    """

    def __init__(self, model_path: str | None = None) -> None:
        if not model_path:
            raise NotImplementedError(
                "LocalEmbeddingModel requires a local model_path; "
                "use FakeEmbeddingModel for CI / default offline use"
            )
        raise NotImplementedError(
            f"On-device embedding load is not wired yet (model_path={model_path!r})"
        )

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError("On-device embedding load is not wired yet")


def create_embedding_model(
    backend: Literal["fake", "local"] = "fake",
    *,
    dimensions: int = 64,
    model_path: str | None = None,
) -> FakeEmbeddingModel | LocalEmbeddingModel:
    """Factory for local-only embedders. ``local`` is reserved for a future on-device model."""
    if backend == "fake":
        return FakeEmbeddingModel(dimensions=dimensions)
    if backend == "local":
        return LocalEmbeddingModel(model_path=model_path)
    raise ValueError(f"unsupported embedding backend: {backend!r}")
