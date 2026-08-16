"""Seeded conversation selection — deterministic, thread-preserving."""

from __future__ import annotations

from collections.abc import Sequence
from random import Random

from personal_enigma.simulation.corpus.models import CorpusConversation


def select_conversations(
    conversations: Sequence[CorpusConversation],
    *,
    seed: str,
    count: int,
) -> list[CorpusConversation]:
    """Select up to ``count`` conversations deterministically from ``seed``.

    Never samples individual messages — thread integrity is preserved.
    """
    if count <= 0:
        return []
    pool = list(conversations)
    rng = Random(seed)
    rng.shuffle(pool)
    return pool[: min(count, len(pool))]
