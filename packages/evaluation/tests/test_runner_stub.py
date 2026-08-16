"""Smoke tests for evaluation scaffold."""

from personal_enigma.evaluation import EvaluationRunner
from personal_enigma.evaluation.metrics import attention, cost, memory, privacy, retrieval


def test_runner_stub() -> None:
    report = EvaluationRunner().run("alex-v1")
    assert report.scenario == "alex-v1"
    assert report.status == "not_implemented"


def test_metric_placeholders() -> None:
    assert attention.critical_recall(predicted=9, expected=10) == 0.9
    assert privacy.direct_identifier_leaks(count=0) == 0
    assert memory.checkpoint_hit_rate(hits=1, total=2) == 0.5
    assert retrieval.recall_at_k(hits=3, k=5) == 0.6
    assert cost.total_usd(amount=1.25) == 1.25
