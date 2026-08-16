"""D4 synthetic DataSource adapter tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivateReminder,
)
from personal_enigma.ingestion.sources.gmail import GmailSource
from personal_enigma.simulation import DemoEnvironment, RealSourceAccessError, load_scenario
from personal_enigma.simulation.sources import (
    SyntheticCalendarSource,
    SyntheticContactsSource,
    SyntheticMailSource,
    SyntheticNotesSource,
    SyntheticReminderSource,
)

REPO = Path(__file__).resolve().parents[4]
FEATURE = REPO / "scenarios" / "feature" / "commitment-basic"


def test_round_trip_mail_and_reminders() -> None:
    pkg = load_scenario(FEATURE)

    async def _run() -> None:
        mail = SyntheticMailSource(pkg)
        reminders = SyntheticReminderSource(pkg)
        mail_batch = await mail.get_changes(None)
        rem_batch = await reminders.get_changes(None)
        assert mail_batch.items
        assert rem_batch.items
        msg = PrivateMessage.model_validate(mail_batch.items[0])
        rem = PrivateReminder.model_validate(rem_batch.items[0])
        assert msg.subject
        assert rem.title

    asyncio.run(_run())


def test_all_adapters_emit_domain_shapes() -> None:
    pkg = load_scenario(REPO / "scenarios" / "feature" / "cross-source-merge")

    async def _run() -> None:
        adapters = [
            (SyntheticMailSource(pkg), PrivateMessage),
            (SyntheticCalendarSource(pkg), PrivateCalendarEvent),
            (SyntheticReminderSource(pkg), PrivateReminder),
            (SyntheticNotesSource(pkg), PrivateNote),
            (SyntheticContactsSource(pkg), PrivatePerson),
        ]
        for source, model in adapters:
            batch = await source.get_changes(None)
            assert batch.exhausted
            assert batch.items
            model.model_validate(batch.items[0])

    asyncio.run(_run())


def test_demo_environment_registers_synthetic_not_real() -> None:
    pkg = load_scenario(FEATURE)
    env = DemoEnvironment(scenario="commitment-basic")
    env.register_source(SyntheticMailSource(pkg))
    with pytest.raises(RealSourceAccessError):
        env.register_source(GmailSource(access_token="x"))
