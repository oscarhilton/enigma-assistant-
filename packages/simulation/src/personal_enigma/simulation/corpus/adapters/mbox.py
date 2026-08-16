"""mbox corpus adapter stub — developer/stress profiles only for real corpora."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from personal_enigma.simulation.corpus.manifest import CorpusManifest
from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMetadata


class MboxAdapter:
    """Stub: full mbox parsing lands when developer SpamAssassin/TREC profiles need it."""

    def __init__(self, manifest: CorpusManifest, *, root: Path | None = None) -> None:
        self.manifest = manifest
        self.root = root or Path(".")

    async def inspect(self) -> CorpusMetadata:
        return CorpusMetadata(
            corpus_id=self.manifest.id,
            provenance=self.manifest.provenance,
            revision=self.manifest.source.revision,
            conversation_count=0,
            description="mbox adapter stub (not implemented)",
        )

    async def iterate_conversations(self) -> AsyncIterator[CorpusConversation]:
        if False:  # pragma: no cover
            yield CorpusConversation(id="", messages=[])
        return
