"""D2 simulation clock and domain injection tests."""

from __future__ import annotations

import ast
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.attention import overdue_reminders
from personal_enigma.domain import PrivateReminder
from personal_enigma.obligations import CommitmentTracker
from personal_enigma.simulation import (
    DemoEnvironment,
    PrivateEnvironment,
    SimulationClock,
    SystemClock,
    build_environment,
)

# Domain packages that must not call wall-clock for decision logic.
_DOMAIN_AUDIT_ROOTS = (
    "packages/attention/src",
    "packages/obligations/src",
    "packages/embeddings/src",
    "packages/transformation/src",
    "packages/identity/src",
    "packages/dedupe/src",
    "packages/privacy/src",
)

_FORBIDDEN = re.compile(
    r"\b(?:datetime\.(?:now|utcnow)|date\.today|time\.time)\s*\("
)


def test_system_clock_is_timezone_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None


def test_simulation_clock_advance_and_pause() -> None:
    clock = SimulationClock(initial=datetime(2026, 3, 1, 9, 0, tzinfo=UTC))
    assert clock.now() == datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    clock.advance(timedelta(hours=2))
    assert clock.now() == datetime(2026, 3, 1, 11, 0, tzinfo=UTC)
    clock.pause()
    clock.advance(timedelta(days=1))
    assert clock.now() == datetime(2026, 3, 1, 11, 0, tzinfo=UTC)
    clock.resume()
    clock.advance_days(1)
    assert clock.now() == datetime(2026, 3, 2, 11, 0, tzinfo=UTC)


def test_simulation_clock_advance_to_rejects_backwards() -> None:
    clock = SimulationClock(initial=datetime(2026, 3, 10, tzinfo=UTC))
    with pytest.raises(ValueError, match="backwards"):
        clock.advance_to(datetime(2026, 3, 1, tzinfo=UTC))


def test_environments_supply_clock() -> None:
    demo = DemoEnvironment(scenario="alex-v1")
    assert isinstance(demo.clock, SimulationClock)
    private = PrivateEnvironment()
    assert isinstance(private.clock, SystemClock)
    built = build_environment()
    assert isinstance(built, PrivateEnvironment)


def test_advance_clock_marks_commitment_stale() -> None:
    clock = SimulationClock(initial=datetime(2026, 4, 1, 12, 0, tzinfo=UTC))
    tracker = CommitmentTracker()
    reminder = PrivateReminder(
        id="r1",
        provider="apple_reminders",
        provider_id="r1",
        title="Send deck",
        due_at=datetime(2026, 4, 2, 9, 0, tzinfo=UTC),
        is_completed=False,
    )
    tracker.upsert_from_reminder(reminder, now=clock.now())
    assert tracker.refresh_staleness_with_clock(clock) == []

    clock.advance(timedelta(days=2))
    stale = tracker.refresh_staleness_with_clock(clock)
    assert len(stale) == 1
    assert stale[0].state.value == "stale"


def test_advance_clock_surfaces_overdue_attention() -> None:
    clock = SimulationClock(initial=datetime(2026, 5, 1, 8, 0, tzinfo=UTC))
    reminder = PrivateReminder(
        id="r2",
        provider="apple_reminders",
        provider_id="r2",
        title="Pay invoice",
        due_at=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        is_completed=False,
    )
    assert overdue_reminders([reminder], clock=clock) == []
    clock.advance(timedelta(hours=3))
    items = overdue_reminders([reminder], clock=clock)
    assert len(items) == 1
    assert items[0].title.startswith("Overdue:")


def test_domain_packages_have_no_naked_wall_clock() -> None:
    """Fail CI if domain packages grow new ``datetime.now()`` decision leaks."""
    repo = Path(__file__).resolve().parents[3]
    offenders: list[str] = []
    for root in _DOMAIN_AUDIT_ROOTS:
        base = repo / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            # Allow imports and type hints; forbid call expressions via regex on AST-ish text.
            for match in _FORBIDDEN.finditer(source):
                # Skip comments
                line_start = source.rfind("\n", 0, match.start()) + 1
                line = source[line_start : source.find("\n", match.start())]
                if line.lstrip().startswith("#"):
                    continue
                offenders.append(f"{path.relative_to(repo)}: {line.strip()}")
            # Extra AST pass for datetime.now / utcnow attribute calls
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in {"now", "utcnow", "today", "time"}:
                    if isinstance(func.value, ast.Name) and func.value.id in {
                        "datetime",
                        "date",
                        "time",
                    }:
                        offenders.append(
                            f"{path.relative_to(repo)}:{node.lineno} "
                            f"{func.value.id}.{func.attr}()"
                        )
    # Deduplicate
    unique = sorted(set(offenders))
    assert unique == [], "Naked wall-clock in domain packages:\n" + "\n".join(unique)
