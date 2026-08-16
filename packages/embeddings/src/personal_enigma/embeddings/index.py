"""In-memory vector index for local retrieval."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vector dimensions must match")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


@dataclass
class _Entry:
    id: str
    vector: list[float]
    payload: dict


@dataclass
class InMemoryVectorIndex:
    """Cosine-similarity vector store kept entirely in process memory."""

    _entries: dict[str, _Entry] = field(default_factory=dict)

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors, and payloads must have the same length")
        expected_dim: int | None = None
        if self._entries:
            expected_dim = len(next(iter(self._entries.values())).vector)
        for item_id, vector, payload in zip(ids, vectors, payloads, strict=True):
            if expected_dim is None:
                expected_dim = len(vector)
            elif len(vector) != expected_dim:
                raise ValueError(
                    f"vector dimension mismatch: expected {expected_dim}, got {len(vector)}"
                )
            self._entries[item_id] = _Entry(id=item_id, vector=list(vector), payload=dict(payload))

    def search(self, vector: list[float], limit: int = 10) -> list[dict]:
        if limit < 1:
            return []
        scored: list[dict] = []
        for entry in self._entries.values():
            score = _cosine(vector, entry.vector)
            result = dict(entry.payload)
            result["id"] = entry.id
            result["score"] = score
            scored.append(result)
        scored.sort(key=lambda row: float(row["score"]), reverse=True)
        return scored[:limit]

    def __len__(self) -> int:
        return len(self._entries)
