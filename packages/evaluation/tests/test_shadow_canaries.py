"""SEC-07 stub — shadow benchmark canary dependency checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.evaluation.semantic_leakage import SemanticLeakageScorer
from personal_enigma.fixtures.alex_security_canaries import (
    GREP_TARGETS,
    PACK_DESCRIPTION,
    PACK_ID,
    GrepTargetId,
    grep_directory_for_sentinels,
    reconstructability_probe_sentinels,
    security_canary_manifest,
)
from personal_enigma.fixtures.alex_security_overlay import ALEX_SCENARIO_ROOT
from personal_enigma.fixtures.alex_sensitive_canaries import (
    ALEX_SENSITIVE_CANARIES,
    assert_canary_pack_complete,
)


def test_shadow_benchmark_canary_pack_registered() -> None:
    """SEC-07 stub — canary pack available for reconstructability scoring."""
    assert_canary_pack_complete()
    manifest = security_canary_manifest()
    assert len(manifest) == len(ALEX_SENSITIVE_CANARIES)
    high_tier = [row for row in manifest if row.sensitivity_tier == "HIGH"]
    assert len(high_tier) >= 5


def test_reconstructability_probes_cover_sensitive_categories() -> None:
    probes = reconstructability_probe_sentinels()
    categories = {row.category for row in security_canary_manifest()}
    assert "medical" in categories
    assert "credentials" in categories
    assert len(probes) >= 14


def test_canary_pack_metadata() -> None:
    assert PACK_ID == "alex-sensitive-canaries-v1"
    assert "FICTIONAL" in PACK_DESCRIPTION


def test_exact_leakage_no_sentinels_in_behavioural_corpus() -> None:
    """Exact leakage — grep Alex behavioural timeline; sentinel count must be 0."""
    if not ALEX_SCENARIO_ROOT.is_dir():
        pytest.skip("scenarios/alex-v1 not present")
    hits = grep_directory_for_sentinels(ALEX_SCENARIO_ROOT)
    assert hits == [], f"Exact leakage into behavioural corpus: {hits[:3]}"


def test_exact_leakage_empty_shadow_export_passes(tmp_path: Path) -> None:
    """Exact leakage — stripped shadow export with no canary injection → 0 hits."""
    export = tmp_path / "shadow-export"
    export.mkdir()
    (export / "shadow.json").write_text('{"items": []}', encoding="utf-8")
    hits = grep_directory_for_sentinels(export)
    assert hits == []


def test_grep_targets_include_shadow_and_stolen_stages() -> None:
    ids = {t.target_id for t in GREP_TARGETS}
    assert GrepTargetId.PERSISTENT_SHADOW in ids
    assert GrepTargetId.STOLEN_DIRECTORY in ids


@pytest.mark.skip(reason="SEC-07 shadow runner not implemented — SemanticLeakageScorer stub")
def test_semantic_leakage_scorer_detects_salary_paraphrase() -> None:
    """Semantic leakage — £123,456 → 'salary around 123k' must score > 0."""
    examples = SemanticLeakageScorer.calibration_examples()
    salary = next(ex for ex in examples if ex.source_fragment.startswith("£"))
    scorer = SemanticLeakageScorer()
    canary = ALEX_SENSITIVE_CANARIES[1]  # payroll
    score = scorer.score(salary.shadow_fragment, canary)
    assert score > 0.0


def test_semantic_leakage_scorer_stub_documents_calibration_cases() -> None:
    examples = SemanticLeakageScorer.calibration_examples()
    assert any("123" in ex.source_fragment for ex in examples)
    assert any("salary" in ex.shadow_fragment for ex in examples)
