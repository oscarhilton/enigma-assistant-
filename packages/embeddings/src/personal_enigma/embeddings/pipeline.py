"""Chunk → embed → local vector index → retrieve pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from personal_enigma.embeddings.corpus import Passage
from personal_enigma.embeddings.protocol import EmbeddingModel, VectorIndex


@dataclass(frozen=True)
class RetrievedPassage:
    """Top passage returned to callers (local retrieval only; not remote-safe by itself)."""

    id: str
    text: str
    score: float
    source_type: str
    metadata: dict[str, str] = field(default_factory=dict)

    def for_transformation(self) -> str:
        """Return passage text for local Enigma transformation input.

        Callers must still run the privacy/transform gate before any remote send;
        this text may contain raw Notes/email content.
        """
        return self.text


@dataclass
class RetrievalPipeline:
    """Local-only retrieval: embed passages into a vector index, then search by query."""

    model: EmbeddingModel
    index: VectorIndex

    def index_passages(self, passages: list[Passage]) -> int:
        if not passages:
            return 0
        vectors = self.model.embed([p.text for p in passages])
        ids = [p.id for p in passages]
        payloads = [
            {
                "text": p.text,
                "source_type": p.source_type,
                "metadata": dict(p.metadata),
            }
            for p in passages
        ]
        self.index.upsert(ids, vectors, payloads)
        return len(passages)

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievedPassage]:
        if not query.strip() or limit < 1:
            return []
        query_vector = self.model.embed([query])[0]
        hits = self.index.search(query_vector, limit=limit)
        results: list[RetrievedPassage] = []
        for hit in hits:
            metadata = hit.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            results.append(
                RetrievedPassage(
                    id=str(hit.get("id", "")),
                    text=str(hit.get("text", "")),
                    score=float(hit.get("score", 0.0)),
                    source_type=str(hit.get("source_type", "")),
                    metadata={str(k): str(v) for k, v in metadata.items()},
                )
            )
        return results
