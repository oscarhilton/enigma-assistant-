"""Adversarial pack harness — transform + privacy zero-leak checks (D09)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import yaml
from pydantic import BaseModel

from personal_enigma.domain import PrivateNote, PrivatePerson
from personal_enigma.evaluation.metrics.privacy import count_forbidden_token_leaks
from personal_enigma.fixtures import (
    build_calendar_event,
    build_contact,
    build_message,
    build_note,
    build_reminder,
)
from personal_enigma.privacy import (
    RemoteInferenceConfig,
    assert_remote_payload_safe,
    assert_transformed_corpus_safe,
)
from personal_enigma.reasoning import (
    PaygReasoningService,
    ReasoningMode,
    ReasoningResult,
)
from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage, load_scenario
from personal_enigma.transformation import DefaultEnigmaTransformer, TransformedContext


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "scenarios" / "feature").is_dir():
            return parent
    return here.parents[5]


REPO_ROOT = _repo_root()
FEATURE_ADVERSARIAL = REPO_ROOT / "scenarios" / "feature" / "adversarial"
ALEX_ATTACKS = REPO_ROOT / "scenarios" / "alex-v1" / "attacks"

ADVERSARIAL_PACK_IDS: tuple[str, ...] = (
    "prompt-injection",
    "secrets",
    "re-identification",
    "malicious-provider",
    "provider-failure",
)

FIXED_HMAC_KEY = b"d09-adversarial-pack-hmac-key"
_NS = UUID("00000000-0000-4000-8000-00000000d009")


class AttackManifest(BaseModel):
    """Cross-link YAML under ``scenarios/alex-v1/attacks/``."""

    id: str
    kind: str
    feature_pack: str
    forbidden_tokens: list[str] = []
    description: str = ""


class AdversarialPackReport(BaseModel):
    """Result of running one adversarial feature pack through transform + gate."""

    pack_id: str
    event_count: int
    remote_payload_count: int
    leak_count: int
    forbidden_tokens: list[str]
    zero_leak: bool


def discover_adversarial_packs(base: Path | None = None) -> list[Path]:
    """Return scenario roots under ``scenarios/feature/adversarial/``."""
    root = base or FEATURE_ADVERSARIAL
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if (p / "scenario.yaml").is_file())


def load_attack_manifests(attacks_dir: Path | None = None) -> list[AttackManifest]:
    """Load Alex attack cross-link YAML files."""
    directory = attacks_dir or ALEX_ATTACKS
    manifests: list[AttackManifest] = []
    if not directory.is_dir():
        return manifests
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            manifests.append(AttackManifest.model_validate(raw))
    return manifests


def forbidden_tokens_for_pack(pack_id: str) -> list[str]:
    """Collect forbidden tokens from matching Alex attack cross-links."""
    tokens: list[str] = []
    for manifest in load_attack_manifests():
        if manifest.kind == pack_id or manifest.feature_pack.endswith(pack_id):
            tokens.extend(manifest.forbidden_tokens)
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def events_to_private_records(events: Sequence[ScenarioEvent]) -> list[BaseModel]:
    """Map scenario source events to private domain models for transform tests."""
    records: list[BaseModel] = []
    for event in events:
        payload = event.payload
        if event.source == "contacts" or event.type == "contact.upsert":
            records.append(_contact_from_payload(payload))
        elif event.source == "notes" or event.type == "note.upsert":
            records.append(_note_from_payload(payload))
        elif event.source == "mail" or event.type.startswith("email."):
            records.append(_message_from_payload(payload))
        elif event.source == "calendar" or event.type.startswith("calendar."):
            if event.type == "calendar.cancel":
                continue
            records.append(_calendar_from_payload(payload))
        elif event.source == "reminders" or event.type.startswith("reminder."):
            if event.type == "reminder.complete":
                continue
            records.append(_reminder_from_payload(payload))
    return records


def transform_pack(
    package: ScenarioPackage,
    *,
    hmac_key: bytes = FIXED_HMAC_KEY,
    allow_remote: bool = True,
) -> tuple[list[BaseModel], list[TransformedContext]]:
    """Transform all private records derived from a scenario package."""
    records = events_to_private_records(package.events)
    transformer = DefaultEnigmaTransformer(hmac_key=hmac_key, allow_remote=allow_remote)
    payloads = [transformer.transform(record) for record in records]
    return records, payloads


def run_adversarial_pack(
    pack_id: str,
    *,
    base: Path | None = None,
    forbidden_tokens: Sequence[str] | None = None,
) -> AdversarialPackReport:
    """Load pack → transform → privacy invariants → forbidden-token scan."""
    root = (base or FEATURE_ADVERSARIAL) / pack_id
    package = load_scenario(root)
    tokens = (
        list(forbidden_tokens)
        if forbidden_tokens is not None
        else forbidden_tokens_for_pack(pack_id)
    )
    records, payloads = transform_pack(package)
    people = [r for r in records if isinstance(r, PrivatePerson)]
    notes = [r for r in records if isinstance(r, PrivateNote)]

    assert_transformed_corpus_safe(
        payloads,
        people=people,
        notes=notes,
        remote=RemoteInferenceConfig(enabled=True),
    )

    remote = [p for p in payloads if p.may_transmit_remotely]
    for payload in remote:
        assert_remote_payload_safe(
            payload,
            people=people,
            notes=notes,
            remote=RemoteInferenceConfig(enabled=True),
        )

    leak_count = 0
    for payload in remote:
        blob = json.dumps(payload.model_dump(mode="json"), default=str, ensure_ascii=False)
        leak_count += count_forbidden_token_leaks(blob, tokens)

    return AdversarialPackReport(
        pack_id=pack_id,
        event_count=len(package.events),
        remote_payload_count=len(remote),
        leak_count=leak_count,
        forbidden_tokens=list(tokens),
        zero_leak=leak_count == 0,
    )


class MaliciousPaygTransport:
    """PAYG stub that searches context for bait tokens — never opens a network."""

    def __init__(self, *, bait_tokens: Sequence[str]) -> None:
        self.bait_tokens = list(bait_tokens)
        self.calls: list[dict[str, object]] = []
        self.bait_hits: list[str] = []

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        blob = json.dumps(context.model_dump(mode="json"), default=str, ensure_ascii=False)
        hits = [t for t in self.bait_tokens if t and t in blob]
        self.bait_hits.extend(hits)
        self.calls.append({"model": model, "prompt": prompt, "context": context, "hits": hits})
        return ReasoningResult(
            text="exfiltrate:" + ",".join(hits) if hits else "no-bait",
            model=model,
            usage=UsageRecord(
                model=model,
                mode=ReasoningMode.ENABLED,
                prompt_tokens=max(1, len(prompt.split())),
                completion_tokens=1,
                estimated_cost_usd=0.0,
                dry_run=False,
            ),
            dry_run=False,
            metadata={"provider": "malicious-stub"},
        )


class FailingPaygTransport:
    """PAYG stub that always fails — no private fallback channel."""

    def __init__(self, *, message: str = "simulated provider failure") -> None:
        self.message = message
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        self.calls.append({"model": model, "prompt": prompt, "context": context})
        raise ConnectionError(self.message)


def reason_remote_payloads(
    payloads: Sequence[TransformedContext],
    *,
    transport: Any,
    prompt: str = "What matters next?",
) -> list[ReasoningResult]:
    """Send only remote-cleared payloads through PAYG (ENABLED)."""
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=transport)
    results: list[ReasoningResult] = []
    for ctx in payloads:
        if not ctx.may_transmit_remotely:
            continue
        results.append(client.reason(ctx, prompt=prompt))
    return results


def _stable_uuid(key: str) -> UUID:
    return uuid5(_NS, key)


def _parse_dt(value: object, default: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return default or datetime(2026, 4, 1, tzinfo=UTC)


def _contact_from_payload(payload: dict[str, Any]) -> PrivatePerson:
    contact_id = str(payload.get("id", "contact"))
    emails = payload.get("email_addresses")
    if emails is None and payload.get("email"):
        emails = [payload["email"]]
    phones = payload.get("phone_numbers")
    if phones is None and payload.get("phone"):
        phones = [payload["phone"]]
    orgs = payload.get("organisations")
    if orgs is None and payload.get("organisation"):
        orgs = [payload["organisation"]]
    aliases = payload.get("aliases") or []
    return build_contact(
        id=_stable_uuid(contact_id),
        display_name=str(payload.get("display_name", "Unknown")),
        aliases=list(aliases),
        email_addresses=list(emails or []),
        phone_numbers=list(phones or []),
        organisations=list(orgs or []),
        provider_ids={"synthetic_contacts": contact_id},
    )


def _note_from_payload(payload: dict[str, Any]) -> PrivateNote:
    note_id = str(payload.get("id", "note"))
    return build_note(
        id=note_id,
        provider_note_id=f"NOTE-{note_id}",
        title=str(payload.get("title", "")),
        body_text=str(payload.get("body_text", "")),
    )


def _ref_from_mapping(raw: object) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return {"email": raw, "display_name": None, "provider_id": f"email:{raw}"}
    if isinstance(raw, dict):
        email = raw.get("email")
        return {
            "email": email,
            "display_name": raw.get("display_name"),
            "provider_id": raw.get("provider_id") or (f"email:{email}" if email else None),
        }
    return None


def _message_from_payload(payload: dict[str, Any]) -> BaseModel:
    msg_id = str(payload.get("id", "mail"))
    from_raw = payload.get("from") or payload.get("from_person")
    to_raw = payload.get("to") or []
    if isinstance(to_raw, str):
        to_raw = [to_raw]
    from_ref = _ref_from_mapping(from_raw) or {
        "email": "unknown@example.test",
        "provider_id": "email:unknown",
    }
    to_refs = [_ref_from_mapping(item) for item in to_raw]
    return build_message(
        id=msg_id,
        provider_message_id=f"gmail-{msg_id}",
        thread_id=f"thread-{msg_id}",
        subject=str(payload.get("subject", "")),
        snippet=str(payload.get("snippet", "")),
        body_text=str(payload.get("body_text", payload.get("snippet", ""))),
        from_person=from_ref,
        to=[r for r in to_refs if r is not None],
    )


def _calendar_from_payload(payload: dict[str, Any]) -> BaseModel:
    event_id = str(payload.get("id", "cal"))
    attendees_raw = payload.get("attendees") or []
    attendees = []
    for item in attendees_raw:
        ref = _ref_from_mapping(item)
        if ref is not None:
            attendees.append(ref)
    organiser = _ref_from_mapping(payload.get("organiser"))
    start = _parse_dt(payload.get("start_at"))
    return build_calendar_event(
        id=event_id,
        provider_event_id=f"EK-{event_id}",
        title=str(payload.get("title", "")),
        description=payload.get("description"),
        start_at=start,
        end_at=_parse_dt(payload.get("end_at"), default=start),
        organiser=organiser,
        attendees=attendees,
    )


def _reminder_from_payload(payload: dict[str, Any]) -> BaseModel:
    rem_id = str(payload.get("id", "rem"))
    due = _parse_dt(payload["due_at"]) if payload.get("due_at") else None
    return build_reminder(
        id=rem_id,
        provider_id=f"REM-{rem_id}",
        title=str(payload.get("title", "")),
        notes=payload.get("notes"),
        due_at=due,
        is_completed=bool(payload.get("is_completed", False)),
    )


__all__ = [
    "ADVERSARIAL_PACK_IDS",
    "ALEX_ATTACKS",
    "AdversarialPackReport",
    "AttackManifest",
    "FEATURE_ADVERSARIAL",
    "FailingPaygTransport",
    "FIXED_HMAC_KEY",
    "MaliciousPaygTransport",
    "discover_adversarial_packs",
    "events_to_private_records",
    "forbidden_tokens_for_pack",
    "load_attack_manifests",
    "reason_remote_payloads",
    "run_adversarial_pack",
    "transform_pack",
]
