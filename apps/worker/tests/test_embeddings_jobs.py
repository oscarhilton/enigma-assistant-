from personal_enigma.embeddings import IndexConfig
from personal_enigma.worker.embeddings import run_embedding_index_job


def test_embedding_index_job_indexes_non_notes_corpora() -> None:
    pipeline, result = run_embedding_index_job(
        emails=[
            {
                "id": "m1",
                "subject": "Vendor contract",
                "body_text": "Please review the renewal terms for the vendor contract.",
            }
        ],
        reminders=[{"id": "r1", "title": "Follow up with vendor", "notes": "Renewal"}],
        calendar_events=[
            {
                "id": "c1",
                "title": "Contract review",
                "description": "Discuss vendor renewal with legal.",
            }
        ],
        notes=[],
        config=IndexConfig(include_notes=True),
    )
    assert result.indexed >= 3
    assert "email" in result.by_source
    assert "reminder" in result.by_source
    assert "calendar" in result.by_source

    hits = pipeline.retrieve("vendor contract renewal", limit=2)
    assert hits
    assert any("vendor" in h.text.lower() or "contract" in h.text.lower() for h in hits)


def test_embedding_index_job_respects_config() -> None:
    _pipeline, result = run_embedding_index_job(
        emails=[{"id": "m1", "subject": "Hi", "body_text": "Hello"}],
        notes=[{"id": "n1", "title": "Secret", "body_text": "Private note"}],
        config=IndexConfig(include_notes=False, include_email=True),
    )
    assert result.by_source.get("email", 0) >= 1
    assert "note" not in result.by_source
