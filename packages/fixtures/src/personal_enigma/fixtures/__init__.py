"""Synthetic private-world fixtures for Enigma tests (M02).

Builders produce deterministic domain models; scenario packs group
cross-source cases (e.g. ``review_proposal`` for M15). Load packs into
:class:`~personal_enigma.fixtures.store.InMemoryFixtureStore` for in-memory
test pipelines. See ``packages/fixtures/README.md``.
"""

from personal_enigma.fixtures.builders import (
    FIXTURE_EPOCH,
    SYNTHETIC_PERSON_ID,
    build_calendar_event,
    build_chat_message,
    build_contact,
    build_message,
    build_note,
    build_person_ref,
    build_reminder,
    sample_calendar_event,
)
from personal_enigma.fixtures.scenarios import (
    SCENARIO_REGISTRY,
    ScenarioPack,
    get_scenario,
    review_proposal_scenario,
)
from personal_enigma.fixtures.store import InMemoryFixtureStore

__all__ = [
    "FIXTURE_EPOCH",
    "SCENARIO_REGISTRY",
    "SYNTHETIC_PERSON_ID",
    "InMemoryFixtureStore",
    "ScenarioPack",
    "build_calendar_event",
    "build_chat_message",
    "build_contact",
    "build_message",
    "build_note",
    "build_person_ref",
    "build_reminder",
    "get_scenario",
    "review_proposal_scenario",
    "sample_calendar_event",
]
