"""D09 — adversarial scenario packs remain zero-leak under transform + privacy gate."""

from __future__ import annotations

import pytest

from personal_enigma.evaluation.adversarial import (
    ADVERSARIAL_PACK_IDS,
    FEATURE_ADVERSARIAL,
    FailingPaygTransport,
    MaliciousPaygTransport,
    discover_adversarial_packs,
    forbidden_tokens_for_pack,
    load_attack_manifests,
    reason_remote_payloads,
    run_adversarial_pack,
    transform_pack,
)
from personal_enigma.evaluation.metrics import privacy as privacy_metrics
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.transformation import TransformedContext


@pytest.mark.parametrize("pack_id", ADVERSARIAL_PACK_IDS)
def test_adversarial_pack_loads(pack_id: str) -> None:
    pkg = load_scenario(FEATURE_ADVERSARIAL / pack_id)
    assert pkg.manifest.id == pack_id
    assert pkg.manifest.status == "feature"
    assert 5 <= len(pkg.events) <= 10


def test_alex_attack_cross_links_cover_all_packs() -> None:
    manifests = load_attack_manifests()
    kinds = {m.kind for m in manifests}
    assert kinds == set(ADVERSARIAL_PACK_IDS)
    assert len(discover_adversarial_packs()) == len(ADVERSARIAL_PACK_IDS)


@pytest.mark.parametrize("pack_id", ADVERSARIAL_PACK_IDS)
def test_adversarial_pack_zero_leak(pack_id: str) -> None:
    report = run_adversarial_pack(pack_id)
    assert report.zero_leak, (
        f"{pack_id}: {report.leak_count} forbidden token leak(s) in remote payloads"
    )
    assert privacy_metrics.direct_identifier_leaks(count=report.leak_count) == 0
    assert privacy_metrics.zero_leak(leak_count=report.leak_count)


def test_malicious_provider_never_sees_bait() -> None:
    pack_id = "malicious-provider"
    package = load_scenario(FEATURE_ADVERSARIAL / pack_id)
    _records, payloads = transform_pack(package)
    bait = forbidden_tokens_for_pack(pack_id)
    assert bait, "expected bait tokens from attack manifest"
    transport = MaliciousPaygTransport(bait_tokens=bait)
    results = reason_remote_payloads(payloads, transport=transport)
    assert results, "expected at least one remote-cleared payload"
    assert transport.bait_hits == []
    assert all(r.metadata.get("provider") == "malicious-stub" for r in results)


def test_provider_failure_does_not_open_private_fallback() -> None:
    pack_id = "provider-failure"
    package = load_scenario(FEATURE_ADVERSARIAL / pack_id)
    _records, payloads = transform_pack(package)
    forbidden = forbidden_tokens_for_pack(pack_id)
    transport = FailingPaygTransport()
    with pytest.raises(ConnectionError, match="simulated provider failure"):
        reason_remote_payloads(payloads, transport=transport)
    assert transport.calls, "failing transport should still receive gated TransformedContext"
    for call in transport.calls:
        ctx = call["context"]
        assert isinstance(ctx, TransformedContext)
        blob = ctx.model_dump_json()
        for token in forbidden:
            assert token not in blob
