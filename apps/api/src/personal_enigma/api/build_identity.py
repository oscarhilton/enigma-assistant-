"""Forensic build identity — captured once per API process.

Old trace dumps must not masquerade as current regressions. Build metadata is
attached to llm_trace and conversation payloads for the web forensic formatter.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

TRACE_SCHEMA = 2
COMPILER_VERSION = "adr029-v3"
CAPSULE_VERSION = "adr030-c09c-frozen"
_DEFAULT_FEATURE_FLAGS = ("c14_trace_v0", "c16_overlay")
_PROFILE_NAMES = (
    "AUTHORITATIVE_ACTION",
    "CONVERSATION",
    "GENERAL_KNOWLEDGE",
    "PREPARE_ACTION",
    "PRIVATE_QUERY",
    "SUPPORT",
    "USER_ATTESTATION",
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").is_dir():
            return parent
    return here.parents[4]


def _run_git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=_repo_root(),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256_hex(data: str | bytes) -> str:
    blob = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(blob).hexdigest()


def sha256_prefixed(data: str | bytes) -> str:
    return f"sha256:{_sha256_hex(data)}"


def short_hash(value: str | None, *, length: int = 6) -> str:
    if not value:
        return "??????"
    digest = value.removeprefix("sha256:")
    return digest[:length]


def branch_slug(branch: str) -> str:
    slug = branch.rsplit("/", maxsplit=1)[-1]
    slug = re.sub(r"^ticket[-_]", "", slug, flags=re.IGNORECASE)
    return slug.lower().replace("_", "-")


def derive_build_name(*, branch: str | None = None) -> str:
    explicit = os.environ.get("ENIGMA_BUILD_NAME", "").strip()
    if explicit:
        return explicit
    if branch:
        return branch_slug(branch)
    return "unknown"


def _read_app_version() -> str:
    override = os.environ.get("ENIGMA_APP_VERSION", "").strip()
    if override:
        return override
    pyproject = _repo_root() / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"), re.M)
        if match:
            return match.group(1)
    return "unknown"


def _git_dirty() -> bool:
    status = _run_git("status", "--porcelain")
    return bool(status)


def _git_patch_hash(*, dirty: bool) -> str | None:
    if not dirty:
        return sha256_prefixed("")
    diff = _run_git("diff", "HEAD") or ""
    untracked = _run_git("ls-files", "--others", "--exclude-standard") or ""
    payload = diff
    if untracked.strip():
        listed = [line.strip() for line in untracked.splitlines() if line.strip()]
        for path in sorted(listed):
            file_path = _repo_root() / path
            if not file_path.is_file():
                continue
            try:
                payload += f"\n--- untracked:{path}\n"
                payload += file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                payload += f"\n--- untracked:{path}\n<unreadable>"
    return sha256_prefixed(payload)


@lru_cache(maxsize=1)
def _prompt_bundle_hash() -> str | None:
    from personal_enigma.api.context_compilation import BASE_CONSTITUTION, compile_system_prompt

    bundle = {
        "base_constitution": BASE_CONSTITUTION,
        "profiles": {
            name: compile_system_prompt(name)  # type: ignore[arg-type]
            for name in _PROFILE_NAMES
        },
    }
    return sha256_prefixed(json.dumps(bundle, sort_keys=True, separators=(",", ":")))


@lru_cache(maxsize=1)
def _tool_registry_hash() -> str | None:
    from personal_enigma.api.demo_tools import tool_schemas

    return sha256_prefixed(
        json.dumps(tool_schemas(), sort_keys=True, separators=(",", ":"), default=str)
    )


def _feature_flags() -> list[str]:
    raw = os.environ.get("ENIGMA_FEATURE_FLAGS", "").strip()
    if raw:
        return sorted({part.strip() for part in raw.split(",") if part.strip()})
    return list(_DEFAULT_FEATURE_FLAGS)


def configured_model_label() -> str | None:
    if os.environ.get("LLM_DISABLED", "").lower() in ("1", "true", "yes"):
        return None
    if os.environ.get("ENIGMA_DEMO_LLM_CONVERSATION", "").lower() in ("0", "false", "no"):
        return None
    if os.environ.get("FIREWORKS_API_KEY"):
        model = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b")
        return f"fireworks/{model.rsplit('/', maxsplit=1)[-1]}"
    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        return f"openai/{model.rsplit('/', maxsplit=1)[-1]}"
    return "intent_router/local"


@lru_cache(maxsize=8)
def _scenario_version(scenario_id: str) -> str | None:
    path = _repo_root() / "scenarios" / scenario_id / "scenario.yaml"
    if not path.is_file():
        return None
    match = re.search(r'^version:\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else None


def format_world_checkpoint(*, scenario: str | None, checkpoint_id: str | None) -> str | None:
    if not scenario or not checkpoint_id:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", checkpoint_id)
    if not match:
        return scenario
    return f"{scenario}@{match.group(1)}"


def format_fixture_label(*, scenario: str | None, fixture: str | None = None) -> str | None:
    if fixture:
        return fixture
    if not scenario:
        return None
    version = _scenario_version(scenario)
    return f"{scenario}@{version}" if version else scenario


class BuildIdentity(BaseModel):
    name: str
    app_version: str
    git_sha: str | None = None
    branch: str | None = None
    dirty: bool = False
    patch_hash: str | None = None
    build_fingerprint: str | None = None


class ForensicContracts(BaseModel):
    trace_schema: int = TRACE_SCHEMA
    compiler: str = COMPILER_VERSION
    capsule: str = CAPSULE_VERSION
    prompt_bundle: str | None = None
    tool_registry: str | None = None
    feature_flags: list[str] = Field(default_factory=list)


class ForensicRuntime(BaseModel):
    environment: str | None = None
    session_started: str | None = None
    model: str | None = None
    world_checkpoint: str | None = None
    fixture: str | None = None


class ForensicProvenance(BaseModel):
    build: BuildIdentity
    contracts: ForensicContracts
    runtime: ForensicRuntime


def is_build_identity_complete(
    build: BuildIdentity,
    contracts: ForensicContracts,
) -> bool:
    critical = (
        build.name,
        build.app_version,
        build.git_sha,
        build.build_fingerprint,
        contracts.prompt_bundle,
        contracts.tool_registry,
    )
    return all(value not in (None, "", "unknown") for value in critical)


def build_identity_complete(provenance: ForensicProvenance | None) -> bool:
    if provenance is None:
        return False
    return is_build_identity_complete(provenance.build, provenance.contracts)


def _build_fingerprint(
    *,
    build: BuildIdentity,
    contracts: ForensicContracts,
) -> str:
    payload = {
        "name": build.name,
        "app_version": build.app_version,
        "git_sha": build.git_sha,
        "branch": build.branch,
        "dirty": build.dirty,
        "patch_hash": build.patch_hash,
        "trace_schema": contracts.trace_schema,
        "compiler": contracts.compiler,
        "capsule": contracts.capsule,
        "prompt_bundle": contracts.prompt_bundle,
        "tool_registry": contracts.tool_registry,
        "feature_flags": contracts.feature_flags,
    }
    return sha256_prefixed(json.dumps(payload, sort_keys=True, separators=(",", ":")))


@lru_cache(maxsize=1)
def capture_process_build_identity() -> BuildIdentity:
    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    git_sha = _run_git("rev-parse", "--short", "HEAD")
    dirty = _git_dirty()
    patch_hash = _git_patch_hash(dirty=dirty) if git_sha else None
    name = derive_build_name(branch=branch)
    app_version = _read_app_version()
    build = BuildIdentity(
        name=name,
        app_version=app_version,
        git_sha=git_sha,
        branch=branch,
        dirty=dirty,
        patch_hash=patch_hash,
    )
    contracts = ForensicContracts(
        prompt_bundle=_prompt_bundle_hash(),
        tool_registry=_tool_registry_hash(),
        feature_flags=_feature_flags(),
    )
    build.build_fingerprint = _build_fingerprint(build=build, contracts=contracts)
    return build


@lru_cache(maxsize=1)
def capture_process_contracts() -> ForensicContracts:
    return ForensicContracts(
        prompt_bundle=_prompt_bundle_hash(),
        tool_registry=_tool_registry_hash(),
        feature_flags=_feature_flags(),
    )


def capture_forensic_provenance(
    *,
    environment: str | None = None,
    session_started: str | None = None,
    model: str | None = None,
    scenario: str | None = None,
    checkpoint_id: str | None = None,
    fixture: str | None = None,
) -> ForensicProvenance:
    build = capture_process_build_identity()
    contracts = capture_process_contracts()
    runtime = ForensicRuntime(
        environment=environment,
        session_started=session_started,
        model=model if model is not None else configured_model_label(),
        world_checkpoint=format_world_checkpoint(scenario=scenario, checkpoint_id=checkpoint_id),
        fixture=format_fixture_label(scenario=scenario, fixture=fixture),
    )
    return ForensicProvenance(build=build, contracts=contracts, runtime=runtime)


def attach_forensic_provenance(
    trace: Any,
    *,
    environment: str | None = None,
    session_started: str | None = None,
    model: str | None = None,
    scenario: str | None = None,
    checkpoint_id: str | None = None,
    fixture: str | None = None,
) -> Any:
    provenance = capture_forensic_provenance(
        environment=environment,
        session_started=session_started,
        model=model,
        scenario=scenario,
        checkpoint_id=checkpoint_id,
        fixture=fixture,
    )
    if hasattr(trace, "model_copy"):
        return trace.model_copy(update={"forensic_provenance": provenance})
    if isinstance(trace, dict):
        return {**trace, "forensic_provenance": provenance.model_dump(mode="json")}
    return trace


def session_forensic_provenance(
    *,
    environment: str | None,
    session_started: str | None,
    scenario: str | None,
    checkpoint_id: str | None,
    fixture: str | None = None,
) -> dict[str, Any]:
    return capture_forensic_provenance(
        environment=environment,
        session_started=session_started,
        scenario=scenario,
        checkpoint_id=checkpoint_id,
        fixture=fixture,
    ).model_dump(mode="json")


__all__ = [
    "CAPSULE_VERSION",
    "COMPILER_VERSION",
    "BuildIdentity",
    "ForensicContracts",
    "ForensicProvenance",
    "ForensicRuntime",
    "TRACE_SCHEMA",
    "attach_forensic_provenance",
    "branch_slug",
    "build_identity_complete",
    "capture_forensic_provenance",
    "capture_process_build_identity",
    "configured_model_label",
    "derive_build_name",
    "format_fixture_label",
    "format_world_checkpoint",
    "is_build_identity_complete",
    "session_forensic_provenance",
    "sha256_prefixed",
    "short_hash",
]
