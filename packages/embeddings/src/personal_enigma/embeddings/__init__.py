"""Local embedding interfaces — never send raw corpora to hosted APIs."""

from personal_enigma.embeddings.chunking import chunk_text
from personal_enigma.embeddings.corpus import (
    IndexConfig,
    Passage,
    filter_passages,
    passages_from_calendar,
    passages_from_email,
    passages_from_note,
    passages_from_reminder,
)
from personal_enigma.embeddings.index import InMemoryVectorIndex
from personal_enigma.embeddings.model import (
    FakeEmbeddingModel,
    LocalEmbeddingModel,
    create_embedding_model,
)
from personal_enigma.embeddings.pipeline import RetrievalPipeline, RetrievedPassage
from personal_enigma.embeddings.protocol import EmbeddingModel, VectorIndex

__all__ = [
    "EmbeddingModel",
    "FakeEmbeddingModel",
    "InMemoryVectorIndex",
    "IndexConfig",
    "LocalEmbeddingModel",
    "Passage",
    "RetrievalPipeline",
    "RetrievedPassage",
    "VectorIndex",
    "chunk_text",
    "create_embedding_model",
    "filter_passages",
    "passages_from_calendar",
    "passages_from_email",
    "passages_from_note",
    "passages_from_reminder",
]
