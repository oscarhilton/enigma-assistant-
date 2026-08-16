"""Pinned synthetic DataSource adapters — owned by D4."""

from __future__ import annotations

from personal_enigma.simulation.sources.calendar import SyntheticCalendarSource
from personal_enigma.simulation.sources.contacts import SyntheticContactsSource
from personal_enigma.simulation.sources.mail import SyntheticMailSource
from personal_enigma.simulation.sources.notes import SyntheticNotesSource
from personal_enigma.simulation.sources.reminders import SyntheticReminderSource

__all__ = [
    "SyntheticCalendarSource",
    "SyntheticContactsSource",
    "SyntheticMailSource",
    "SyntheticNotesSource",
    "SyntheticReminderSource",
]
