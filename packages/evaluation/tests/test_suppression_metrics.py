"""Tests for background / noise false-alert headline metric (D08d)."""

from __future__ import annotations

from personal_enigma.evaluation.ground_truth import (
    GroundTruthCorpus,
    ScenarioSignalClass,
    SignalTruth,
)
from personal_enigma.evaluation.metrics.suppression import (
    MAX_BACKGROUND_FALSE_ALERTS_PER_1000,
    background_false_alerts_per_1000,
    quiet_day_attention_empty,
)
from personal_enigma.evaluation.observations import SurfacedAlert


def test_false_alert_rate_zero_when_silent() -> None:
    truth = GroundTruthCorpus(
        signals=[
            SignalTruth(
                evidence_id="noise-1",
                signal_class=ScenarioSignalClass.NOISE,
                expected_attention=False,
            ),
            SignalTruth(
                evidence_id="bg-1",
                signal_class=ScenarioSignalClass.BACKGROUND,
                expected_attention=False,
            ),
        ]
    )
    rate = background_false_alerts_per_1000(truth, [], message_count=183)
    assert rate.false_alerts == 0
    assert rate.per_1000 == 0.0
    assert rate.passed
    assert rate.max_per_1000 == MAX_BACKGROUND_FALSE_ALERTS_PER_1000


def test_false_alert_rate_counts_noise_evidence() -> None:
    truth = GroundTruthCorpus(
        signals=[
            SignalTruth(
                evidence_id="noise-1",
                signal_class=ScenarioSignalClass.NOISE,
                expected_attention=False,
            )
        ]
    )
    alerts = [SurfacedAlert(id="a1", evidence_ids=["noise-1"])]
    rate = background_false_alerts_per_1000(truth, alerts, message_count=1000)
    assert rate.false_alerts == 1
    assert rate.per_1000 == 1.0
    assert rate.passed  # exactly at ceiling


def test_quiet_day_attention_empty_helper() -> None:
    assert quiet_day_attention_empty(attention_items=[], obligation_count=0)
    assert not quiet_day_attention_empty(attention_items=["x"], obligation_count=0)
