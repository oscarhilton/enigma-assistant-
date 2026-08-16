"""maildir corpus adapter stub."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from personal_enigma.simulation.corpus.manifest import CorpusManifest
from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMetadata


class MaildirAdapter:
    """Stub: maildir iteration for optional developer corpora."""

    def __init__(self, manifest: CorpusManifest, *, root: Path | None = None) -> None:
        self.manifest = manifest
        self.root = root or Path(".")

    async def inspect(self) -> CorpusMetadata:
        return CorpusMetadata(
            corpus_id=self.manifest.id,
            provenance=self.manifest.provenance,
            revision=self.manifest.source.revision,
            conversation_count=0,
            description="maildir adapter stub (not implemented)",
        )

    async def iterate_conversations(self) -> AsyncIterator[CorpusConversation]:
        if False:  # pragma: no cover
            yield CorpusConversation(id="", messages=[])
        return
