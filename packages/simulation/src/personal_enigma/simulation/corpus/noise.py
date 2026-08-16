"""Deterministic machine-noise templates → GeneratedNoiseStream (D08d).

Noise is **machine sludge** (newsletters, receipts, bots, marketing) — not the
D08c human-background corpus. Evaluator ``signal_class: noise`` stays off
Enigma-facing payloads.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from personal_enigma.domain import PrivateMessage
from personal_enigma.simulation.corpus.streams import GeneratedNoiseStream
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage
from personal_enigma.simulation.scenario_rng import scenario_rng

DemoProfileName = Literal["feature", "demo", "canonical", "stress", "quiet_day", "quiet"]

# Documented budgets (CI uses feature/demo/quiet_day small counts).
DEMO_NOISE_MESSAGE_TARGET = 250
CANONICAL_NOISE_MESSAGE_TARGET = 1_500
QUIET_DAY_NOISE_MESSAGE_COUNT = 183
QUIET_DAY_MESSAGE_COUNT = QUIET_DAY_NOISE_MESSAGE_COUNT  # alias

# Headline gate — false alerts attributed to background/noise per 1k inbound.
# Keep in sync with evaluation.metrics.suppression.MAX_BACKGROUND_FALSE_ALERTS_PER_1000.
MAX_BACKGROUND_FALSE_ALERTS_PER_1K = 1.0

NoiseCategory = Literal[
    "newsletter",
    "receipt",
    "automated_notification",
    "marketing",
    "account_notice",
    "delivery_update",
    "calendar_confirmation",
    "spam_like",
]

NOISE_CATEGORIES: tuple[NoiseCategory, ...] = (
    "newsletter",
    "receipt",
    "automated_notification",
    "marketing",
    "account_notice",
    "delivery_update",
    "calendar_confirmation",
    "spam_like",
)

# Fictional brands only — never trademarked provider names (ticket non-goal).
_BRANDS: dict[NoiseCategory, tuple[str, ...]] = {
    "newsletter": ("DesignLedger", "StackBrief", "ProductPulse"),
    "receipt": ("CartNest", "ShopHarbor", "InvoiceBee"),
    "automated_notification": ("BuildCloud", "DeployHive", "SyncForge"),
    "marketing": ("CloudBoost", "GrowthKit", "PromoNest"),
    "account_notice": ("AccountGuard", "SafeKey", "LoginShield"),
    "delivery_update": ("ParcelPost", "RouteFox", "BoxTrail"),
    "calendar_confirmation": ("MeetSlot", "CalConfirm", "SlotKeeper"),
    "spam_like": ("PrizeVault", "LuckyClick", "OfferRiver"),
}

_BRAND_TOKENS_LOWER: tuple[str, ...] = tuple(
    brand.lower() for brands in _BRANDS.values() for brand in brands
)
_MACHINE_LOCAL_PARTS: frozenset[str] = frozenset(
    {
        "noreply",
        "no-reply",
        "news",
        "newsletter",
        "receipts",
        "hello",
        "accounts",
        "shipments",
        "calendar",
        "wins",
        "marketing",
        "promo",
        "notifications",
    }
)
_SUBJECT_NOISE_TOKENS: tuple[str, ...] = (
    "receipt",
    "out for delivery",
    "% off",
    "security notice",
    "build #",
    "claim your",
    "unsubscribe",
    "weekly #",
    "confirmed:",
)

_CATEGORY_WEIGHTS: dict[str, float] = {
    "newsletter": 0.18,
    "receipt": 0.12,
    "automated_notification": 0.18,
    "marketing": 0.14,
    "account_notice": 0.10,
    "delivery_update": 0.12,
    "calendar_confirmation": 0.08,
    "spam_like": 0.08,
}


class NoiseDateRange(BaseModel):
    start: datetime
    end: datetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            text = f"{text}T00:00:00+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @model_validator(mode="after")
    def _ordered(self) -> NoiseDateRange:
        if self.start > self.end:
            raise ValueError("date_range.start must be <= date_range.end")
        return self


class NoiseClassification(BaseModel):
    """Evaluator-only labels for machine noise."""

    signal_class: Literal["noise"] = "noise"
    expected_attention: bool = False


class NoiseSpec(BaseModel):
    """One noise generation declaration."""

    id: str = "machine-sludge"
    seed: str
    message_count: int = Field(ge=0)
    date_range: NoiseDateRange
    classification: NoiseClassification = Field(default_factory=NoiseClassification)
    # Optional category mix override (must sum ≈ 1.0 when set).
    category_weights: dict[str, float] | None = None

    @model_validator(mode="after")
    def _validate_category_weights(self) -> NoiseSpec:
        weights = self.category_weights
        if weights is None:
            return self
        if not weights:
            raise ValueError(f"noise {self.id!r}: category_weights must be non-empty")
        unknown = sorted(set(weights) - set(NOISE_CATEGORIES))
        if unknown:
            raise ValueError(
                f"noise {self.id!r}: unknown category_weights keys {unknown}"
            )
        if any(float(v) < 0 for v in weights.values()):
            raise ValueError(f"noise {self.id!r}: category_weights must be >= 0")
        total = sum(float(v) for v in weights.values())
        if abs(total - 1.0) > 0.05:
            raise ValueError(
                f"noise {self.id!r}: category_weights must sum ≈ 1.0 (got {total})"
            )
        return self


class NoiseConfig(BaseModel):
    """Contents of ``noise.yaml`` (simulation metadata, not Enigma input)."""

    profile: DemoProfileName = "demo"
    noise: list[NoiseSpec] = Field(default_factory=list)
    streams: list[NoiseSpec] = Field(default_factory=list)
    profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: str | None = None

    def specs_for_profile(
        self, profile: DemoProfileName | str | None = None
    ) -> list[NoiseSpec]:
        name = profile or self.profile
        if name in self.profiles:
            block = self.profiles[name] or {}
            raw = block.get("streams", block.get("noise", block.get("email", [])))
            if raw is None:
                return []
            if not isinstance(raw, list):
                raise ValueError(f"profiles.{name}.streams/noise must be a list")
            return [NoiseSpec.model_validate(item) for item in raw]
        if name == self.profile or not self.profiles:
            return list(self.streams or self.noise)
        raise KeyError(f"unknown noise profile {name!r}")


@dataclass(frozen=True, slots=True)
class NoiseSignalTruth:
    """Evaluator-only classification for one noise mail event."""

    evidence_id: str
    signal_class: str = "noise"
    expected_attention: bool = False
    category: NoiseCategory | None = None
    stream_id: str | None = None


@dataclass
class NoiseBuildResult:
    stream: GeneratedNoiseStream
    signals: list[NoiseSignalTruth] = field(default_factory=list)
    events: list[ScenarioEvent] = field(default_factory=list)
    profile: str = "demo"


def load_noise_config(path: Path | str) -> NoiseConfig:
    root = Path(path)
    raw = yaml.safe_load(root.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{root}: noise.yaml must be a mapping")
    return NoiseConfig.model_validate(raw)


def load_scenario_noise(package: ScenarioPackage) -> NoiseConfig | None:
    path = package.root / "noise.yaml"
    if not path.is_file():
        return None
    return load_noise_config(path)


def _self_email(package: ScenarioPackage) -> str:
    contacts = package.entities.get("contacts") or {}
    roster = contacts.get("contacts") if isinstance(contacts, dict) else None
    if isinstance(roster, dict):
        self_entry = roster.get("alex") or roster.get("self")
        if isinstance(self_entry, dict) and self_entry.get("email"):
            return str(self_entry["email"])
    for event in package.events:
        if event.type == "contact.upsert" and event.payload.get("email"):
            return str(event.payload["email"])
    return "alex.morgan@northwind.example"


def _pick_category(rng: Random, weights: Mapping[str, float]) -> NoiseCategory:
    items = [(str(k), float(v)) for k, v in weights.items() if float(v) > 0]
    if not items:
        return "newsletter"
    total = sum(w for _, w in items)
    roll = rng.random() * total
    cursor = 0.0
    for name, weight in items:
        cursor += weight
        if roll <= cursor:
            if name in NOISE_CATEGORIES:
                return name  # type: ignore[return-value]
            break
    return "newsletter"


def _brand_domain(brand: str) -> str:
    return f"{brand.lower()}.example"


def _render_template(
    category: NoiseCategory,
    *,
    index: int,
    rng: Random,
    to_email: str,
) -> dict[str, Any]:
    brand = rng.choice(_BRANDS[category])
    domain = _brand_domain(brand)
    n = index + 1
    if category == "newsletter":
        subject = f"{brand} Weekly #{400 + (n % 80)}"
        sender = f"news@{domain}"
        body = (
            f"This week from {brand}: five links worth a skim, none urgent. "
            f"Issue {n}."
        )
    elif category == "receipt":
        subject = f"Your {brand} receipt #{10_000 + n}"
        sender = f"receipts@{domain}"
        body = f"Thanks for your order. Total £{(n % 90) + 9}.99. No action needed."
    elif category == "automated_notification":
        subject = f"{brand}: build #{8000 + n} finished"
        sender = f"noreply@{domain}"
        body = f"Pipeline succeeded on main (run {n}). View logs in {brand}."
    elif category == "marketing":
        subject = f"{brand}: {20 + (n % 30)}% off this week only"
        sender = f"hello@{domain}"
        body = f"Limited offer from {brand}. Unsubscribe anytime. Promo code NOISE{n}."
    elif category == "account_notice":
        subject = f"{brand} security notice — new sign-in"
        sender = f"accounts@{domain}"
        body = (
            f"We noticed a sign-in to your {brand} account. If this was you, "
            "no action is required."
        )
    elif category == "delivery_update":
        subject = f"{brand}: package out for delivery"
        sender = f"shipments@{domain}"
        body = f"Parcel {brand[:2].upper()}{n:05d} is out for delivery today."
    elif category == "calendar_confirmation":
        subject = f"Confirmed: {brand} hold on your calendar"
        sender = f"calendar@{domain}"
        body = f"This is an automated confirmation from {brand}. No RSVP needed."
    else:  # spam_like
        subject = f"Congrats — claim your {brand} reward"
        sender = f"wins@{domain}"
        body = (
            f"You have been selected by {brand}. This message is junk; "
            "do not click anything."
        )

    evidence_id = f"noise-{category}-{index:04d}"
    return {
        "id": evidence_id,
        "thread_id": f"noise-thread-{category}-{index // 3:04d}",
        "subject": subject,
        "snippet": body[:120],
        "body_text": body,
        "from": sender,
        "from_name": brand,
        "to": [to_email],
        "labels": [],
    }


def _place_at(
    rng: Random,
    *,
    window_start: datetime,
    window_end: datetime,
    index: int,
    message_count: int,
) -> datetime:
    start = window_start if window_start.tzinfo else window_start.replace(tzinfo=UTC)
    end = window_end if window_end.tzinfo else window_end.replace(tzinfo=UTC)
    span = max(1.0, (end - start).total_seconds())
    # Spread deterministically across the window with light jitter.
    frac = (index + 0.5) / max(1, message_count)
    base = start + timedelta(seconds=frac * span)
    jitter_cap = max(1, min(1800, int(span / max(1, message_count))))
    jitter = timedelta(seconds=rng.randrange(0, jitter_cap))
    at = base + jitter
    if at < start:
        return start
    if at > end:
        return end
    return at


def generate_noise_events(
    *,
    seed: str,
    message_count: int,
    window_start: datetime,
    window_end: datetime,
    to_email: str,
    stream_id: str = "machine-sludge",
    category_weights: Mapping[str, float] | None = None,
) -> tuple[list[ScenarioEvent], list[NoiseSignalTruth]]:
    """Build deterministic noise mail events + evaluator signal rows."""
    if message_count <= 0:
        return [], []
    rng = scenario_rng(seed)
    weights: dict[str, float] = (
        dict(category_weights) if category_weights is not None else dict(_CATEGORY_WEIGHTS)
    )
    # Guarantee every category appears at least once when the budget allows.
    if message_count >= len(NOISE_CATEGORIES):
        categories: list[NoiseCategory] = list(NOISE_CATEGORIES)
        while len(categories) < message_count:
            categories.append(_pick_category(rng, weights))
        rng.shuffle(categories)
    else:
        categories = [_pick_category(rng, weights) for _ in range(message_count)]
    events: list[ScenarioEvent] = []
    signals: list[NoiseSignalTruth] = []
    for index, category in enumerate(categories):
        payload = _render_template(category, index=index, rng=rng, to_email=to_email)
        payload["id"] = f"noise-{category}-{index:04d}"
        payload["thread_id"] = f"noise-thread-{category}-{index // 3:04d}"
        at = _place_at(
            rng,
            window_start=window_start,
            window_end=window_end,
            index=index,
            message_count=message_count,
        )
        payload["received_at"] = at.isoformat().replace("+00:00", "Z")
        evidence_id = str(payload["id"])
        events.append(
            ScenarioEvent(
                id=f"noise:{evidence_id}",
                at=at,
                source="mail",
                type="email.receive",
                payload=payload,
            )
        )
        signals.append(
            NoiseSignalTruth(
                evidence_id=evidence_id,
                signal_class="noise",
                expected_attention=False,
                category=category,
                stream_id=stream_id,
            )
        )
    events.sort(key=lambda e: (e.at, e.id))
    return events, signals


def build_noise_stream(
    package: ScenarioPackage,
    *,
    profile: DemoProfileName | str | None = None,
    config: NoiseConfig | None = None,
) -> NoiseBuildResult:
    """Generate a ``GeneratedNoiseStream`` for a scenario profile."""
    cfg = config if config is not None else load_scenario_noise(package)
    if cfg is None:
        return NoiseBuildResult(
            stream=GeneratedNoiseStream(events=[]),
            profile=str(profile or "demo"),
        )

    resolved = str(profile or cfg.profile)
    specs = cfg.specs_for_profile(resolved)

    to_email = _self_email(package)
    all_events: list[ScenarioEvent] = []
    signals: list[NoiseSignalTruth] = []
    for spec in specs:
        if spec.message_count <= 0:
            continue
        events, rows = generate_noise_events(
            seed=spec.seed,
            message_count=spec.message_count,
            window_start=spec.date_range.start,
            window_end=spec.date_range.end,
            to_email=to_email,
            stream_id=spec.id,
            category_weights=spec.category_weights,
        )
        all_events.extend(events)
        signals.extend(rows)

    all_events.sort(key=lambda e: (e.at, e.id))
    return NoiseBuildResult(
        stream=GeneratedNoiseStream(events=all_events),
        signals=signals,
        events=all_events,
        profile=resolved,
    )


def looks_like_machine_noise(
    message: PrivateMessage | Mapping[str, Any],
) -> bool:
    """Heuristic: machine-sludge patterns used by local templates.

    Enigma never sees ``signal_class``; this is the product-side filter that
    keeps quiet-day silence honest. Conservative — only clear automation /
    marketing / junk shapes.
    """
    if isinstance(message, PrivateMessage):
        sender = (message.from_person.email if message.from_person else None) or ""
        subject = message.subject or ""
        body = message.body_text or message.snippet or ""
        from_name = (message.from_person.display_name if message.from_person else None) or ""
    else:
        sender = str(message.get("from") or "")
        subject = str(message.get("subject") or "")
        body = str(message.get("body_text") or message.get("snippet") or "")
        from_name = str(message.get("from_name") or "")

    sender_l = sender.lower()
    subject_l = subject.lower()
    blob = f"{subject_l}\n{body.lower()}\n{from_name.lower()}"

    local = sender_l.split("@", 1)[0] if "@" in sender_l else sender_l
    if local in _MACHINE_LOCAL_PARTS:
        return True

    if any(token in blob for token in _BRAND_TOKENS_LOWER):
        return True
    if any(token in subject_l for token in _SUBJECT_NOISE_TOKENS):
        return True
    return False


def category_distribution(signals: Sequence[NoiseSignalTruth]) -> dict[str, int]:
    counts: dict[str, int] = {c: 0 for c in NOISE_CATEGORIES}
    for signal in signals:
        if signal.category:
            counts[signal.category] = counts.get(signal.category, 0) + 1
    return counts


__all__ = [
    "CANONICAL_NOISE_MESSAGE_TARGET",
    "DEMO_NOISE_MESSAGE_TARGET",
    "MAX_BACKGROUND_FALSE_ALERTS_PER_1K",
    "NOISE_CATEGORIES",
    "QUIET_DAY_MESSAGE_COUNT",
    "QUIET_DAY_NOISE_MESSAGE_COUNT",
    "DemoProfileName",
    "NoiseBuildResult",
    "NoiseCategory",
    "NoiseClassification",
    "NoiseConfig",
    "NoiseDateRange",
    "NoiseSignalTruth",
    "NoiseSpec",
    "build_noise_stream",
    "category_distribution",
    "generate_noise_events",
    "load_noise_config",
    "load_scenario_noise",
    "looks_like_machine_noise",
]
