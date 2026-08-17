"""Life Script YAML schema.

Public C09 capability names are structured *boundaries* (product surface).
Router intents, orchestrator branches, handler names, and regex IDs are smell.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# Keys that would couple the script to Enigma internals. Refactors would
# break the life even if Alex's morning still worked.
SMELL_EXPECT_KEYS: frozenset[str] = frozenset(
    {
        "router_intent",
        "orchestrator_branch",
        "orchestrator_path",
        "handler",
        "handler_name",
        "regex",
        "phrase_map",
        "phrase_id",
        "intent_name",
        "intent_router",
        "branch",
    }
)


class LifeScriptError(ValueError):
    """Invalid Life Script — usually a smell key or schema mismatch."""


class PrivacyDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_source_allowed_remote: bool = False
    exact_payload_audited: bool = True
    outbound_classification: Literal["remote_safe"] = "remote_safe"


class AuthorityDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    undeclared_tools_allowed: bool = False
    direct_source_access_by_model: bool = False


class ScriptDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    privacy: PrivacyDefaults = Field(default_factory=PrivacyDefaults)
    authority: AuthorityDefaults = Field(default_factory=AuthorityDefaults)


class ConversationalRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    temporary: bool = True


class TurnExpect(BaseModel):
    """Public effects + structured capability boundaries — not internals."""

    model_config = ConfigDict(extra="forbid")

    tool: str | None = None
    tools: list[str] | None = None
    arguments: dict[str, Any] | None = None
    meaning: str | None = None
    equivalent_to_previous: bool | None = None
    response_meaning: list[str] | None = None
    source_scope: str | None = None
    conversational_response: bool | None = None
    fallback_not_allowed: bool | None = None
    needs_you: list[str] | None = None
    current_subject_id: str | None = None
    current_subject_excludes: str | list[str] | None = None
    preserve_subject: str | bool | None = None
    secondary_items: str | list[str] | None = None
    secondary_items_may_include: str | list[str] | None = None
    assist_target: str | None = None
    attributed_to_original_assist: str | None = None
    world_mutation: bool | None = None
    evidence_source: str | None = None
    current_next_action_excludes: str | list[str] | None = None
    alternative_returned: bool | None = None
    conversational_rejection: ConversationalRejection | None = None
    no_tool: bool | None = None
    verified_external_effect: bool | None = None
    grounded_world_response: bool | None = None
    tool_required: bool | None = None
    covers: list[str] | None = None

    @field_validator("tool", mode="before")
    @classmethod
    def _coerce_none_tool(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() in {"", "none", "null"}:
            return None
        return value


class TurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meaning: list[str] = Field(default_factory=list)
    may_offer: str | list[str] | None = None
    must_not: list[str] = Field(default_factory=list)


class WorldEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    checkpoint: str
    note: str | None = None


class InjectSpec(BaseModel):
    """Harness hook — deliberate wrong subject. Not live-model luck."""

    model_config = ConfigDict(extra="forbid")

    wrong_subject_id: str
    note: str | None = None


def _clock_to_str(value: object) -> object:
    """YAML timestamps load as datetime; keep the script surface a string."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class ScriptStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str | None = None
    event: str | None = None
    expect: TurnExpect | None = None
    response: TurnResponse | None = None
    privacy: PrivacyDefaults | None = None
    authority: AuthorityDefaults | None = None
    v1: Literal["live", "deferred"] | None = Field(
        default=None,
        description=(
            "On-surface vs missing product capability — not Fireworks vs deterministic."
        ),
    )
    deferred_reason: str | None = None
    clock: str | None = None
    world_event: WorldEvent | None = None
    inject: InjectSpec | None = None
    comment: str | None = None

    @field_validator("clock", mode="before")
    @classmethod
    def _coerce_step_clock(cls, value: object) -> object:
        return _clock_to_str(value)


class LifeScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str
    clock: str
    checkpoint: str = "cp-2026-01-19T10:00"
    persona: str = "Alex Morgan"
    world: str = "alex_v1"
    purpose: str
    pass_rule: str
    frozen_rules: list[str] = Field(default_factory=list)
    defaults: ScriptDefaults = Field(default_factory=ScriptDefaults)
    turns: list[ScriptStep]

    @field_validator("clock", mode="before")
    @classmethod
    def _coerce_script_clock(cls, value: object) -> object:
        return _clock_to_str(value)


def _find_smell_keys(payload: Any, *, trail: str) -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        scoped = trail.endswith(".expect") or trail.endswith(".expect]")
        for key, value in payload.items():
            here = f"{trail}.{key}"
            if scoped and key in SMELL_EXPECT_KEYS:
                hits.append(f"{here} ({key})")
            hits.extend(_find_smell_keys(value, trail=here))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            hits.extend(_find_smell_keys(item, trail=f"{trail}[{index}]"))
    return hits


def load_life_script(path: Path) -> LifeScript:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise LifeScriptError(f"Life Script must be a mapping: {path}")
    smells = _find_smell_keys(raw, trail="script")
    if smells:
        listed = ", ".join(smells)
        raise LifeScriptError(
            "Life Scripts must not encode router/orchestrator internals. "
            "Assert public effects and capability boundaries only. "
            f"Smell: {listed}"
        )
    try:
        return LifeScript.model_validate(raw)
    except ValidationError as exc:
        text = str(exc)
        if any(key in text for key in SMELL_EXPECT_KEYS):
            raise LifeScriptError(
                "Life Scripts must not encode router/orchestrator internals. "
                "Assert public effects and capability boundaries only. "
                f"{exc}"
            ) from exc
        raise LifeScriptError(f"Invalid Life Script {path}: {exc}") from exc
