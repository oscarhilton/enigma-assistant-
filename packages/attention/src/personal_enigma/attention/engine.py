"""Local heuristic attention ranking — no remote LLM required."""

from __future__ import annotations

from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.protocol import AttentionItem

# Higher weight → surfaces first. Explicit reminders beat weak email inferences.
KIND_PRIORITY: dict[AttentionKind, float] = {
    AttentionKind.EXPLICIT_REMINDER: 100.0,
    AttentionKind.CALENDAR_OBLIGATION: 75.0,
    AttentionKind.INFERRED_OBLIGATION: 50.0,
    AttentionKind.INFERRED_COMMITMENT: 25.0,
}

# Soft email / message inferences; never outrank EXPLICIT_REMINDER via raw score alone.
WEAK_INFERRED_KINDS: frozenset[AttentionKind] = frozenset(
    {AttentionKind.INFERRED_COMMITMENT},
)

_WEAK_SCORE_CAP = 20.0


def effective_score(item: AttentionItem) -> float:
    """Combine kind priority with item score; clamp weak inferences."""
    base = KIND_PRIORITY[item.kind]
    bonus = item.score
    if item.kind in WEAK_INFERRED_KINDS:
        bonus = min(bonus, _WEAK_SCORE_CAP)
    return base + bonus


class HeuristicAttentionEngine:
    """Rank attention items with local heuristics only.

    ``remote_llm_enabled`` is accepted for API compatibility with later M05
    wiring; v0 never calls a hosted model.
    """

    def __init__(self, *, remote_llm_enabled: bool = False) -> None:
        self.remote_llm_enabled = remote_llm_enabled

    def rank(self, items: list[AttentionItem]) -> list[AttentionItem]:
        """Return items ordered by what matters most (highest score first)."""
        ranked: list[AttentionItem] = []
        for item in items:
            ranked.append(item.model_copy(update={"score": effective_score(item)}))
        ranked.sort(key=lambda i: (-i.score, i.title.casefold(), i.kind.value))
        return ranked
