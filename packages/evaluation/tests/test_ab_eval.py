"""A/B storyline-recall helpers (D08c)."""

from __future__ import annotations

from personal_enigma.evaluation.ab_eval import (
    compare_storyline_ab,
    storyline_recall_under_noise,
)


def test_storyline_recall_ab_passes_within_one_pp() -> None:
    spine = {"attention": {"critical_recall": 0.97}}
    with_bg = {"attention": {"critical_recall": 0.965}}
    result = storyline_recall_under_noise(spine, with_bg)
    assert result.passed
    assert abs(result.drop - 0.005) < 1e-9
    assert compare_storyline_ab(spine, with_bg).passed


def test_storyline_recall_ab_fails_when_drop_exceeds_budget() -> None:
    spine = {"attention": {"critical_recall": 1.0}}
    with_bg = {"attention": {"critical_recall": 0.97}}
    result = storyline_recall_under_noise(spine, with_bg)
    assert not result.passed
    assert abs(result.drop - 0.03) < 1e-9
    regression = compare_storyline_ab(spine, with_bg)
    assert not regression.passed
    assert any("critical_recall" in v for v in regression.violations)


def test_storyline_recall_ab_fails_on_displacement_even_if_recall_flat() -> None:
    spine = {"attention": {"critical_recall": 1.0}}
    with_bg = {"attention": {"critical_recall": 1.0}}
    result = storyline_recall_under_noise(
        spine, with_bg, critical_displacement=2
    )
    assert not result.passed
    regression = compare_storyline_ab(
        spine, with_bg, critical_displacement=2
    )
    assert not regression.passed
    assert any("critical_displacement" in v for v in regression.violations)
