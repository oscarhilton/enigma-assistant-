"""CorpusAdapter protocol — dataset-specific behaviour stops here."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMetadata


class CorpusAdapter(Protocol):
    """Load conversations from an external or fixture corpus."""

    async def inspect(self) -> CorpusMetadata:
        """Return corpus metadata without loading all conversations."""
        ...

    def iterate_conversations(self) -> AsyncIterator[CorpusConversation]:
        """Yield conversations (thread integrity preserved)."""
        ...
