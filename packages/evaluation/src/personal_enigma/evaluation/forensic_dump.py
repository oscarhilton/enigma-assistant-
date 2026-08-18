"""Parse forensic dumps and score named humour / action-integrity invariants.

A dump that says BUILD UNKNOWN is an adversarial Life Script — not evidence
that current main still has these bugs. Live replay is skipped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

FORENSIC_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "forensic"
DUMP_NAME = "alex_brunch_token_goose_forensic.dump.txt"
TURNS_NAME = "alex_brunch_token_goose_forensic.turns.yaml"
BOOTSTRAP_NAME = "alex_brunch_token_goose_forensic.bootstrap.yaml"

CORPUS_ID = "alex_brunch_token_goose_forensic"
RESERVATION_TOOLS = frozenset({"reservation.book", "reservation.confirm"})
EFFECT_STATES = (
    "prepared",
    "proposed",
    "scheduled",
    "attempted",
    "verified-complete",
)
_TURN_SPLIT = re.compile(r"======== Turn (\d+) of (\d+) ========")
_HEADERS = (
    "PATH",
    "CORRELATION",
    "USER MESSAGE",
    "CONVERSATION STATE",
    "INTENT",
    "TOOLS AVAILABLE",
    "REMOTE CONTEXT SENT",
    "MODEL TOOL REQUEST",
    "REFERENT RESOLUTION",
    "EXECUTED TOOL REQUEST",
    "TOOL RESULT",
    "MODEL RESPONSE",
    "Privacy disclosure",
    "Provider",
    "Purpose",
    "Payload hash",
    "Included",
    "Excluded",
)
_WORK_CLAIM = re.compile(
    r"i['’]m starting|i['’]ll proceed|i['’]m working on",
    re.IGNORECASE,
)
_BEIGE = re.compile(
    r"sounds like you['’]?re in a playful mood|whoa[—\-].*chaos in the room|"
    r"is the [“\"]?goose[”\"]? a metaphor",
    re.IGNORECASE,
)
_SPAIN_HOLIDAY = re.compile(r"went on holiday to spain|holiday in spain", re.IGNORECASE)


def _fold(text: str) -> str:
    return text.casefold().replace("\u2019", "'").replace("\u2018", "'")


def _parse_jsonish(blob: str) -> Any:
    text = blob.strip()
    if not text or text.lower() == "none":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _sections(body: str) -> dict[str, str]:
    found: dict[str, str] = {}
    matches: list[tuple[int, str, int]] = []
    for header in _HEADERS:
        for match in re.finditer(rf"^{re.escape(header)}\n", body, re.MULTILINE):
            matches.append((match.start(), header, match.end()))
    matches.sort()
    for index, (_start, header, content_start) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(body)
        found[header] = body[content_start:end].strip()
    return found


def _tool_names(payload: Any) -> list[str]:
    if not isinstance(payload, list):
        return []
    names: list[str] = []
    for row in payload:
        if isinstance(row, dict) and isinstance(row.get("name"), str):
            names.append(row["name"])
    return names


def _response_texts(payload: Any) -> list[str]:
    if not isinstance(payload, list):
        return []
    texts: list[str] = []
    for row in payload:
        if isinstance(row, dict) and isinstance(row.get("text"), str):
            texts.append(row["text"])
    return texts


@dataclass(frozen=True, slots=True)
class ForensicTurn:
    number: int
    user: str
    tools_available: list[str]
    executed_tools: list[str]
    tool_results: list[dict[str, Any]]
    response_texts: list[str]
    remote_context: dict[str, Any] | None
    authority: str | None
    profile: str | None
    subject_id: str | None
    unavailable: list[str] = field(default_factory=list)

    @property
    def response_blob(self) -> str:
        return "\n".join(self.response_texts)

    def explain_payload(self) -> dict[str, Any] | None:
        for row in self.tool_results:
            if row.get("name") == "world.explain" and isinstance(row.get("data"), dict):
                data = row["data"]
                return data if isinstance(data, dict) else None
        return None


@dataclass(frozen=True, slots=True)
class ForensicDump:
    header: str
    turns: tuple[ForensicTurn, ...]
    build_unknown: bool

    def turn(self, number: int) -> ForensicTurn:
        for row in self.turns:
            if row.number == number:
                return row
        raise KeyError(f"turn {number}")


def parse_forensic_dump(text: str) -> ForensicDump:
    parts = _TURN_SPLIT.split(text)
    header = parts[0]
    turns: list[ForensicTurn] = []
    index = 1
    while index + 2 < len(parts):
        number = int(parts[index])
        body = parts[index + 2]
        sections = _sections(body)
        remote = _parse_jsonish(sections.get("REMOTE CONTEXT SENT", ""))
        remote_dict = remote if isinstance(remote, dict) else None
        working = remote_dict.get("working_set") if remote_dict else None
        working_dict = working if isinstance(working, dict) else {}
        contract = working_dict.get("capability_contract")
        contract_dict = contract if isinstance(contract, dict) else {}
        unavailable = contract_dict.get("unavailable")
        avail_raw = sections.get("TOOLS AVAILABLE", "").strip()
        available = (
            []
            if avail_raw.lower() in {"", "none"}
            else [item.strip() for item in avail_raw.split(",") if item.strip()]
        )
        executed_payload = _parse_jsonish(sections.get("EXECUTED TOOL REQUEST", ""))
        result_payload = _parse_jsonish(sections.get("TOOL RESULT", ""))
        results: list[dict[str, Any]] = []
        if isinstance(result_payload, list):
            results = [row for row in result_payload if isinstance(row, dict)]
        conversation = remote_dict.get("conversation") if remote_dict else None
        conversation_dict = conversation if isinstance(conversation, dict) else {}
        turns.append(
            ForensicTurn(
                number=number,
                user=sections.get("USER MESSAGE", "").strip(),
                tools_available=available,
                executed_tools=_tool_names(executed_payload),
                tool_results=results,
                response_texts=_response_texts(
                    _parse_jsonish(sections.get("MODEL RESPONSE", ""))
                ),
                remote_context=remote_dict,
                authority=(
                    str(working_dict.get("authority"))
                    if working_dict.get("authority")
                    else str(conversation_dict.get("authority"))
                    if conversation_dict.get("authority")
                    else None
                ),
                profile=(
                    str(working_dict.get("profile"))
                    if working_dict.get("profile")
                    else None
                ),
                subject_id=(
                    str(working_dict.get("current_subject_id"))
                    if working_dict.get("current_subject_id")
                    else None
                ),
                unavailable=list(unavailable) if isinstance(unavailable, list) else [],
            )
        )
        index += 3
    return ForensicDump(
        header=header,
        turns=tuple(turns),
        build_unknown="BUILD UNKNOWN" in header,
    )


def load_corpus_dump() -> ForensicDump:
    return parse_forensic_dump((FORENSIC_DIR / DUMP_NAME).read_text(encoding="utf-8"))


def load_corpus_index() -> dict[str, Any]:
    raw = yaml.safe_load((FORENSIC_DIR / TURNS_NAME).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("turns yaml must be a mapping")
    return raw


def load_relational_bootstrap() -> dict[str, Any]:
    raw = yaml.safe_load((FORENSIC_DIR / BOOTSTRAP_NAME).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("bootstrap yaml must be a mapping")
    return raw


def proposal_is_not_reservation(turn: ForensicTurn) -> bool:
    executed = set(turn.executed_tools)
    return "assist.propose" in executed and executed.isdisjoint(RESERVATION_TOOLS)


def distinguishes_calendar_from_reservation(text: str) -> bool:
    blob = _fold(text)
    denies = any(
        needle in blob
        for needle in (
            "haven't booked a restaurant",
            "have not booked a restaurant",
            "not a restaurant booking",
            "calendar event is not",
        )
    )
    return denies


def brunch_fact_contaminates_token_subject(title: str, facts: list[str]) -> bool:
    tokenish = "token" in title.casefold()
    brunch = any("elena" in fact.casefold() and "saturday" in fact.casefold() for fact in facts)
    return tokenish and brunch


def claims_work_underway(text: str) -> bool:
    return bool(_WORK_CLAIM.search(_fold(text)))


def agency_forbids_work_claim(turn: ForensicTurn) -> bool:
    payload = json.dumps(turn.remote_context or {})
    has_active_work = "agent_work" in payload and "no active" not in payload.casefold()
    return turn.tools_available == [] and turn.authority == "NONE" and not has_active_work


def product_payload_mentions_goose(turn: ForensicTurn) -> bool:
    context = dict(turn.remote_context or {})
    context.pop("user_message", None)
    context.pop("recent_dialogue", None)
    return "goose" in json.dumps(context).casefold()


def is_beige_boilerplate(text: str) -> bool:
    return bool(_BEIGE.search(_fold(text)))


def mammal_test_holds(*, squeeze_goose_funny: bool, animal_cruelty_funny: bool) -> bool:
    return not (squeeze_goose_funny and animal_cruelty_funny)


def ignore_palette_is_success(bootstrap: dict[str, Any]) -> bool:
    constitution = bootstrap.get("humour_constitution")
    palette = (bootstrap.get("relational_bootstrap") or {}).get("cultural_palette")
    constitution_ok = isinstance(constitution, dict) and constitution.get(
        "ignore_palette_is_success"
    ) is True
    palette_ok = isinstance(palette, dict) and palette.get("ignore_is_success") is True
    return constitution_ok and palette_ok


def crowbars_unrelated_memory(response: str, memory: str) -> bool:
    return _fold(memory) in _fold(response)


def parrots_established_phrase(response: str, phrase: str) -> bool:
    return _fold(phrase) in _fold(response)


def is_novel_goose_variation(response: str) -> bool:
    blob = _fold(response)
    mentions_goose = "goose" in blob
    verbatim = "squeeze the goose" in blob
    inventive = any(
        needle in blob
        for needle in ("kubernetes", "in production", "paddock", "corner")
    )
    return mentions_goose and inventive and not verbatim


def live_variation_auto_promotes(variation: dict[str, Any]) -> bool:
    return bool(variation.get("auto_promote_to_canon"))


def motif_is_punchline_string(motif: dict[str, Any]) -> bool:
    return "phrase_to_insert" in motif or "joke" in motif


GOOSE_CARGO_KEYS = frozenset(
    {
        "mission_id",
        "held_items",
        "capacity_class",
        "source_visits",
        "dropped_items",
        "delivered_items",
    }
)


def holding_does_not_memorise(*, held: bool, remembered_by_holding: bool) -> bool:
    """THE Goose may hold information temporarily. It may never remember it merely by holding it."""
    return not (held and remembered_by_holding)


def cargo_is_inspectable(cargo: dict[str, Any]) -> bool:
    return GOOSE_CARGO_KEYS <= set(cargo) and cargo.get("is_memory_store") is not True


def dropped_items_not_retained(cargo: dict[str, Any]) -> bool:
    retained_ids = {str(item) for item in cargo.get("retained_ids") or []}
    dropped = cargo.get("dropped_items") or []
    return all(
        str(item.get("id")) not in retained_ids
        for item in dropped
        if isinstance(item, dict)
    )


def retention_requires_vault_errand(decision: dict[str, Any]) -> bool:
    if decision.get("auto_entered_vault") is True:
        return False
    if decision.get("worth_remembering") is True:
        return decision.get("vault_errand") is True
    return True


def machine_produces_does_not_retain(event: dict[str, Any]) -> bool:
    return bool(event.get("produced")) and event.get("retained") is not True


def having_is_not_understanding_is_not_remembering(
    *,
    held: bool,
    understood: bool,
    remembered: bool,
) -> bool:
    """Having now ≠ understanding ≠ remembering later. Holding must not itself be memory."""
    return not (held and remembered)


def three_jobs_are_distinct(layers: dict[str, str]) -> bool:
    return {
        layers.get("having"),
        layers.get("understanding"),
        layers.get("remembering"),
    } == {"goose_cargo", "assistant", "vault"}


ALWAYS_VISIBLE = frozenset({"user", "assistant", "goose", "cases"})
INSPECTABLE_WHEN_RELEVANT = frozenset({"vault", "machine", "sources"})
FORENSIC_ADVANCED = frozenset(
    {
        "cortex",
        "evidence_bundle",
        "lineage",
        "egress",
        "authority",
        "epistemic_status",
    }
)
INTERNAL_METAPHORS = frozenset(
    {"shadows", "satchel", "cargo", "workbench", "engine_room"}
)


def visibility_layers_hold(spec: dict[str, Any]) -> bool:
    always = {str(item) for item in spec.get("always_visible") or []}
    inspectable = {str(item) for item in spec.get("inspectable_when_relevant") or []}
    forensic = {str(item) for item in spec.get("forensic") or []}
    internal = {str(item) for item in spec.get("internal_metaphors_not_cast") or []}
    return (
        always == ALWAYS_VISIBLE
        and inspectable == INSPECTABLE_WHEN_RELEVANT
        and forensic == FORENSIC_ADVANCED
        and internal == INTERNAL_METAPHORS
        and always.isdisjoint(internal)
        and spec.get("next_frontier") == "relationship_not_more_memory_architecture"
        and spec.get("core_state_drives_goose_state") is True
    )
