from __future__ import annotations

import socket

import pytest

from personal_enigma.embeddings import (
    EmbeddingModel,
    FakeEmbeddingModel,
    IndexConfig,
    InMemoryVectorIndex,
    LocalEmbeddingModel,
    Passage,
    RetrievalPipeline,
    VectorIndex,
    chunk_text,
    create_embedding_model,
    passages_from_calendar,
    passages_from_email,
    passages_from_note,
    passages_from_reminder,
)


def test_protocols_are_importable() -> None:
    assert EmbeddingModel is not None
    assert VectorIndex is not None


def test_fake_embedder_is_deterministic() -> None:
    model = FakeEmbeddingModel(dimensions=32)
    a = model.embed(["Project kickoff with Alex"])
    b = model.embed(["Project kickoff with Alex"])
    assert a == b
    assert len(a[0]) == 32


def test_fake_embedder_satisfies_protocol() -> None:
    model: EmbeddingModel = FakeEmbeddingModel()
    vectors = model.embed(["hello", "world"])
    assert len(vectors) == 2
    assert all(isinstance(v, list) for v in vectors)


def test_local_model_fails_closed_without_path() -> None:
    with pytest.raises(NotImplementedError, match="model_path"):
        LocalEmbeddingModel()


def test_create_embedding_model_defaults_to_fake() -> None:
    model = create_embedding_model()
    assert isinstance(model, FakeEmbeddingModel)


def test_chunk_text_overlaps() -> None:
    text = "a" * 120
    chunks = chunk_text(text, max_chars=50, overlap=10)
    assert len(chunks) >= 3
    assert chunks[0] == "a" * 50


def test_corpus_helpers_build_passages() -> None:
    email = passages_from_email(
        message_id="m1",
        subject="Invoice",
        body_text="Please pay the contractor invoice by Friday.",
    )
    note = passages_from_note(note_id="n1", title="Ideas", body_text="Local-first notes memory.")
    reminder = passages_from_reminder(reminder_id="r1", title="Call dentist", notes="Tuesday")
    calendar = passages_from_calendar(
        event_id="c1",
        title="Standup",
        description="Daily team sync about retrieval layer",
    )
    assert email[0].source_type == "email"
    assert note[0].source_type == "note"
    assert reminder[0].source_type == "reminder"
    assert calendar[0].source_type == "calendar"


def test_integration_corpus_retrieve_relevant_chunk() -> None:
    model = FakeEmbeddingModel(dimensions=64)
    index: VectorIndex = InMemoryVectorIndex()
    pipeline = RetrievalPipeline(model=model, index=index)

    passages = [
        *passages_from_email(
            message_id="m-noise",
            subject="Lunch plans",
            body_text="Want to grab tacos near the office tomorrow?",
        ),
        *passages_from_calendar(
            event_id="c-hit",
            title="Embedding design review",
            description="Discuss local vector index and retrieval for private notes.",
        ),
        *passages_from_reminder(
            reminder_id="r-noise",
            title="Buy oat milk",
            notes="Grocery store",
        ),
    ]
    assert pipeline.index_passages(passages) == len(passages)

    hits = pipeline.retrieve("local vector index for private notes", limit=2)
    assert hits
    assert "vector index" in hits[0].text.lower() or "embedding" in hits[0].text.lower()
    assert hits[0].for_transformation() == hits[0].text
    assert hits[0].score >= hits[-1].score


def test_index_config_can_exclude_notes() -> None:
    from personal_enigma.embeddings import filter_passages

    passages = [
        Passage(id="e", text="email body", source_type="email"),
        Passage(id="n", text="note body", source_type="note"),
    ]
    kept = filter_passages(passages, IndexConfig(include_notes=False))
    assert [p.id for p in kept] == ["e"]


def test_embed_path_makes_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def _block_connect(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network connect attempted during local embed path")

    monkeypatch.setattr(socket.socket, "connect", _block_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _block_connect)

    model = FakeEmbeddingModel()
    index = InMemoryVectorIndex()
    pipeline = RetrievalPipeline(model=model, index=index)
    passages = passages_from_note(
        note_id="n1",
        title="Private",
        body_text="Raw note content must stay local while embedding.",
    )
    pipeline.index_passages(passages)
    hits = pipeline.retrieve("raw note content local embedding", limit=1)
    assert hits
    assert "local" in hits[0].text.lower()
