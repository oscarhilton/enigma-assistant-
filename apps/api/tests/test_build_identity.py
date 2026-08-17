"""Forensic build identity — process capture and fingerprint stability."""

from __future__ import annotations

from personal_enigma.api.build_identity import (
    BuildIdentity,
    ForensicContracts,
    branch_slug,
    capture_process_build_identity,
    derive_build_name,
    is_build_identity_complete,
    sha256_prefixed,
    short_hash,
)


def test_branch_slug_strips_ticket_prefix() -> None:
    assert branch_slug("ticket/C16-attested-completion") == "c16-attested-completion"


def test_derive_build_name_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("ENIGMA_BUILD_NAME", "my-custom-build")
    assert derive_build_name(branch="ticket/foo") == "my-custom-build"


def test_derive_build_name_from_branch_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("ENIGMA_BUILD_NAME", raising=False)
    assert derive_build_name(branch="ticket/C16-attested-completion") == "c16-attested-completion"


def test_build_fingerprint_is_stable_for_fixed_inputs() -> None:
    build = BuildIdentity(
        name="c16-attested-overlay",
        app_version="0.3.0-dev",
        git_sha="7c8f4a1",
        branch="ticket/C16-attested-completion",
        dirty=True,
        patch_hash="sha256:93ad2e",
    )
    contracts = ForensicContracts(
        prompt_bundle="sha256:81e4c9",
        tool_registry="sha256:42b7a0",
        feature_flags=["c14_trace_v0", "c16_overlay"],
    )
    from personal_enigma.api.build_identity import _build_fingerprint

    first = _build_fingerprint(build=build, contracts=contracts)
    second = _build_fingerprint(build=build, contracts=contracts)
    assert first == second
    assert first.startswith("sha256:")


def test_process_build_identity_has_critical_fields() -> None:
    identity = capture_process_build_identity()
    assert identity.name
    assert identity.app_version
    assert identity.build_fingerprint
    assert identity.build_fingerprint.startswith("sha256:")
    assert is_build_identity_complete(identity, ForensicContracts(
        prompt_bundle=sha256_prefixed("prompt"),
        tool_registry=sha256_prefixed("tools"),
    ))


def test_short_hash_prefix_stripping() -> None:
    assert short_hash("sha256:abcdef123456") == "abcdef"


def test_incomplete_build_identity_detected() -> None:
    build = BuildIdentity(name="demo", app_version="0.1.0")
    contracts = ForensicContracts()
    assert not is_build_identity_complete(build, contracts)
