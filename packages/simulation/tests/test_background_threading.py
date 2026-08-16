"""F-background-threading — stable thread_id and reply order after sanitiser + timeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from personal_enigma.simulation.corpus.background import build_background_stream
from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage
from personal_enigma.simulation.corpus.sanitise import sanitise_conversation_detailed
from personal_enigma.simulation.corpus.timeline import place_conversation_on_timeline
from personal_enigma.simulation.scenario import load_scenario

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature"


def test_background_threading_stable_ids_and_order() -> None:
    pkg = load_scenario(FEATURE / "background-threading")
    assert pkg.manifest.id == "background-threading"
    built = build_background_stream(pkg, profile="feature")
    assert built.events

    by_thread: dict[str, list] = {}
    for event in built.events:
        thread = str(event.payload["thread_id"])
        by_thread.setdefault(thread, []).append(event)
        # Payload id shares the conversation id prefix used as thread_id.
        assert str(event.payload["id"]).startswith(f"{thread}-")

    multi = {tid: evs for tid, evs in by_thread.items() if len(evs) > 1}
    assert multi, "expected at least one multi-message mini thread"

    for thread_id, events in multi.items():
        assert all(e.payload["thread_id"] == thread_id for e in events)
        stamps = [e.at for e in events]
        assert stamps == sorted(stamps)
        assert all(a < b for a, b in zip(stamps, stamps[1:], strict=False))


def test_background_threading_window_edge_preserves_reply_order() -> None:
    """Tight window still yields strictly increasing reply stamps."""
    conv = CorpusConversation(
        id="edge-thread",
        messages=[
            CorpusMessage(
                corpus_id="finepersonas-mini",
                conversation_id="edge-thread",
                message_index=i,
                sender_name="Casey Ng",
                sender_email="casey@riverside-college.edu",
                recipient_names=["Alex Morgan"],
                recipient_emails=["alex.morgan@northwind.example"],
                subject=f"Re: edge {i}",
                body_text=f"reply {i}",
            )
            for i in range(5)
        ],
    )
    cleaned = sanitise_conversation_detailed(
        conv,
        rewrite_seed="f-threading-edge",
        self_email="alex.morgan@northwind.example",
    ).conversation
    assert cleaned is not None
    start = datetime(2026, 4, 6, 16, 0, tzinfo=UTC)
    end = start + timedelta(minutes=2)
    placed = place_conversation_on_timeline(
        cleaned,
        window_start=start,
        window_end=end,
        seed="f-threading-edge",
        self_email="alex.morgan@northwind.example",
    )
    assert len(placed) == 5
    assert all(e.payload["thread_id"] == "edge-thread" for e in placed)
    stamps = [e.at for e in placed]
    assert stamps == sorted(stamps)
    assert all(a < b for a, b in zip(stamps, stamps[1:], strict=False))
