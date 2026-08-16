from personal_enigma.embeddings import EmbeddingModel, VectorIndex


def test_protocols_are_importable() -> None:
    assert EmbeddingModel is not None
    assert VectorIndex is not None
