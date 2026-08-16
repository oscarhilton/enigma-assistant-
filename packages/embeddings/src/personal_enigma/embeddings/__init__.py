"""Local embedding interfaces — never send raw corpora to hosted APIs."""

from personal_enigma.embeddings.protocol import EmbeddingModel, VectorIndex

__all__ = ["EmbeddingModel", "VectorIndex"]
