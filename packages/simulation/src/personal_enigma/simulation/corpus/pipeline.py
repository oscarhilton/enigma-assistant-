"""End-to-end Demo-safe corpus build (select → sanitise → cache → timeline)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from personal_enigma.simulation.corpus.cache import DerivedCorpusCache
from personal_enigma.simulation.corpus.expand import expand_conversations
from personal_enigma.simulation.corpus.manifest import CorpusManifest
from personal_enigma.simulation.corpus.models import (
    CorpusConversation,
    CorpusProvenance,
)
from personal_enigma.simulation.corpus.sanitise import (
    SANITISER_VERSION,
    sanitise_conversation_detailed,
)
from personal_enigma.simulation.corpus.selectors import select_conversations
from personal_enigma.simulation.corpus.timeline import place_conversations_on_timeline
from personal_enigma.simulation.scenario import ScenarioEvent


@dataclass(frozen=True, slots=True)
class CorpusBuildResult:
    accepted: list[CorpusConversation]
    rejected: list[dict[str, Any]]
    events: list[ScenarioEvent]
    derived_dir: Path
    manifest: dict[str, Any]


async def collect_conversations(adapter: Any) -> list[CorpusConversation]:
    return [c async for c in adapter.iterate_conversations()]


def build_demo_safe_corpus(
    conversations: Sequence[CorpusConversation],
    *,
    manifest: CorpusManifest,
    seed: str,
    count: int,
    window_start: datetime,
    window_end: datetime,
    derived: DerivedCorpusCache | None = None,
    profile: str = "demo-safe-v1",
    rewrite_seed: str | None = None,
    expand_to: int | None = None,
    require_synthetic: bool = True,
) -> CorpusBuildResult:
    """Select conversations (not messages), sanitise, cache, and place on timeline.

    When ``expand_to`` is set (e.g. 100 for CI), the input pool is deterministically
    expanded first so mini fixtures can meet acceptance without Hugging Face.
    """
    if require_synthetic and manifest.provenance != CorpusProvenance.SYNTHETIC_CONFIRMED:
        raise ValueError(
            f"public Demo build requires provenance "
            f"{CorpusProvenance.SYNTHETIC_CONFIRMED.value}, got "
            f"{manifest.provenance.value}"
        )

    pool: list[CorpusConversation] = list(conversations)
    if expand_to is not None and len(pool) < expand_to:
        pool = expand_conversations(pool, target_count=expand_to, seed=f"{seed}:expand")

    selected = select_conversations(pool, seed=seed, count=count)
    rewrite = rewrite_seed or seed

    accepted: list[CorpusConversation] = []
    rejected: list[dict[str, Any]] = []
    for conv in selected:
        result = sanitise_conversation_detailed(conv, rewrite_seed=rewrite)
        if result.conversation is None:
            rejected.append(
                {
                    "id": conv.id,
                    "reasons": result.diagnostics.reasons,
                }
            )
            continue
        accepted.append(result.conversation)

    events = place_conversations_on_timeline(
        accepted,
        window_start=window_start,
        window_end=window_end,
        seed=seed,
    )

    revision = manifest.source.revision or "unspecified"
    cache = derived or DerivedCorpusCache()
    target = cache.ensure_profile_dir(
        manifest.id,
        revision=revision,
        sanitiser_version=SANITISER_VERSION,
        seed=seed,
        profile=profile,
    )
    build_manifest: dict[str, Any] = {
        "source": manifest.id,
        "source_revision": revision,
        "sanitiser_version": SANITISER_VERSION,
        "seed": seed,
        "profile": profile,
        "provenance": (
            CorpusProvenance.SYNTHETIC_CONFIRMED.value
            if require_synthetic
            else manifest.provenance.value
        ),
        "requested_count": count,
        "accepted_conversations": len(accepted),
        "rejected_conversations": len(rejected),
        "event_count": len(events),
    }
    cache.write_build(
        target,
        manifest=build_manifest,
        accepted=accepted,
        rejected=rejected,
    )
    return CorpusBuildResult(
        accepted=accepted,
        rejected=rejected,
        events=events,
        derived_dir=target,
        manifest=build_manifest,
    )
