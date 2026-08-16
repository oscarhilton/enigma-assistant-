"""D4 synthetic DataSource adapter tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from personal_enigma.domain import (
    Obligation,
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivateReminder,
)
from personal_enigma.ingestion.protocol import DataSource
from personal_enigma.ingestion.sources.apple_calendar import AppleCalendarSource
from personal_enigma.ingestion.sources.apple_contacts import AppleContactsSource
from personal_enigma.ingestion.sources.apple_notes import AppleNotesSource
from personal_enigma.ingestion.sources.apple_reminders import AppleReminderSource
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
CROSS = REPO / "scenarios" / "feature" / "cross-source-merge"

# Domain models emitted by production adapters (same shapes Demo must produce).
_PRODUCTION_DOMAIN_BY_SYNTHETIC: list[tuple[type, type]] = [
    (SyntheticMailSource, PrivateMessage),
    (SyntheticCalendarSource, PrivateCalendarEvent),
    (SyntheticReminderSource, PrivateReminder),
    (SyntheticNotesSource, PrivateNote),
    (SyntheticContactsSource, PrivatePerson),
]

_PRODUCTION_SOURCES: list[type] = [
    GmailSource,
    AppleCalendarSource,
    AppleReminderSource,
    AppleNotesSource,
    AppleContactsSource,
]


def test_synthetics_satisfy_datasource_like_production() -> None:
    pkg = load_scenario(CROSS)
    synthetics = [
        SyntheticMailSource(pkg),
        SyntheticCalendarSource(pkg),
        SyntheticReminderSource(pkg),
        SyntheticNotesSource(pkg),
        SyntheticContactsSource(pkg),
    ]
    for source in synthetics:
        assert isinstance(source, DataSource)
    for cls in _PRODUCTION_SOURCES:
        # runtime_checkable Protocol: structural check via a throwaway instance shape
        assert callable(getattr(cls, "get_changes", None))
        assert "get_changes" in cls.__dict__ or any(
            "get_changes" in base.__dict__ for base in cls.__mro__
        )


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
        assert msg.provider == "gmail"
        assert rem.provider == "apple_reminders"

    asyncio.run(_run())


def test_all_adapters_emit_domain_shapes_matching_production() -> None:
    pkg = load_scenario(CROSS)

    async def _run() -> None:
        for source_cls, model in _PRODUCTION_DOMAIN_BY_SYNTHETIC:
            source = source_cls(pkg)
            batch = await source.get_changes(None)
            assert batch.exhausted
            assert batch.items
            record = model.model_validate(batch.items[0])
            # Field set must match the production domain model (not a subset dump).
            dumped = record.model_dump(mode="json")
            assert set(dumped) == set(model.model_fields)
            assert set(batch.items[0]) == set(model.model_fields)

    asyncio.run(_run())


def test_demo_environment_registers_synthetic_not_real() -> None:
    pkg = load_scenario(FEATURE)
    env = DemoEnvironment(scenario="commitment-basic")
    env.register_source(SyntheticMailSource(pkg))
    with pytest.raises(RealSourceAccessError):
        env.register_source(GmailSource(access_token="x"))


def test_adapters_do_not_construct_obligations() -> None:
    from personal_enigma.simulation.sources import mail as mail_mod

    assert not hasattr(mail_mod, "Obligation")
    assert Obligation.__name__ == "Obligation"
    src = Path(mail_mod.__file__ or "").read_text(encoding="utf-8")
    assert "Obligation" not in src
    assert "AttentionItem" not in src


def test_module_paths_not_under_ingestion_sources() -> None:
    for cls in (
        SyntheticMailSource,
        SyntheticCalendarSource,
        SyntheticReminderSource,
        SyntheticNotesSource,
        SyntheticContactsSource,
    ):
        assert cls.__module__.startswith("personal_enigma.simulation.sources")
        assert "ingestion.sources" not in cls.__module__
