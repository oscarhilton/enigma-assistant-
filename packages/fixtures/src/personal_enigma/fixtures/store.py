"""In-memory fixture stores for loading scenario packs into tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivateReminder,
)
from personal_enigma.fixtures.scenarios import ScenarioPack, get_scenario


@dataclass
class InMemoryFixtureStore:
    """Mutable in-memory collections of domain models for test pipelines.

    Call :meth:`load_scenario` (or :meth:`load_scenario_by_name`) to populate
    from a :class:`~personal_enigma.fixtures.scenarios.ScenarioPack`. Loading
    appends; call :meth:`clear` between cases when isolation is required.
    """

    calendar_events: list[PrivateCalendarEvent] = field(default_factory=list)
    reminders: list[PrivateReminder] = field(default_factory=list)
    contacts: list[PrivatePerson] = field(default_factory=list)
    notes: list[PrivateNote] = field(default_factory=list)
    messages: list[PrivateMessage] = field(default_factory=list)

    def clear(self) -> None:
        """Remove all stored entities."""
        self.calendar_events.clear()
        self.reminders.clear()
        self.contacts.clear()
        self.notes.clear()
        self.messages.clear()

    def load_scenario(self, pack: ScenarioPack) -> ScenarioPack:
        """Append all entities from ``pack`` into this store; return the pack."""
        self.calendar_events.extend(pack.calendar_events)
        self.reminders.extend(pack.reminders)
        self.contacts.extend(pack.contacts)
        self.notes.extend(pack.notes)
        self.messages.extend(pack.messages)
        return pack

    def load_scenario_by_name(self, name: str) -> ScenarioPack:
        """Load a registered scenario by name into this store."""
        return self.load_scenario(get_scenario(name))
