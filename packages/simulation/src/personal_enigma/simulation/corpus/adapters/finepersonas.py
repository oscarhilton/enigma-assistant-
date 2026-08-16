"""FinePersonas / local JSONL conversation adapter (fixture-first stub)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from personal_enigma.simulation.corpus.manifest import CorpusManifest
from personal_enigma.simulation.corpus.models import (
    CorpusConversation,
    CorpusMessage,
    CorpusMetadata,
)
from personal_enigma.simulation.corpus.sanitise import sanitise_raw_record


class FinePersonasAdapter:
    """Load FinePersonas-shaped conversations from a local root (no HF download)."""

    def __init__(self, manifest: CorpusManifest, *, root: Path | None = None) -> None:
        self.manifest = manifest
        self.root = root or Path(".")

    def _conversations_path(self) -> Path:
        return self.root / "conversations.jsonl"

    async def inspect(self) -> CorpusMetadata:
        path = self._conversations_path()
        count = 0
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                count = sum(1 for line in handle if line.strip())
        return CorpusMetadata(
            corpus_id=self.manifest.id,
            provenance=self.manifest.provenance,
            revision=self.manifest.source.revision,
            conversation_count=count,
            description="FinePersonas-shaped local fixture / cache",
        )

    async def iterate_conversations(self) -> AsyncIterator[CorpusConversation]:
        path = self._conversations_path()
        if not path.exists():
            return
            yield  # pragma: no cover — makes this an async generator
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = sanitise_raw_record(json.loads(line))
                yield self._to_conversation(raw)

    def _to_conversation(self, raw: dict[str, Any]) -> CorpusConversation:
        conv_id = str(raw.get("id") or raw.get("conversation_id") or "unknown")
        emails = raw.get("emails") or raw.get("messages") or []
        messages: list[CorpusMessage] = []
        for index, item in enumerate(emails):
            if not isinstance(item, dict):
                continue
            cleaned = sanitise_raw_record(item)
            messages.append(
                CorpusMessage(
                    corpus_id=self.manifest.id,
                    conversation_id=conv_id,
                    message_index=index,
                    sender_name=str(
                        cleaned.get("sender_name")
                        or cleaned.get("from_name")
                        or "Unknown"
                    ),
                    sender_email=str(
                        cleaned.get("sender_email")
                        or cleaned.get("from")
                        or "unknown@example"
                    ),
                    recipient_names=list(cleaned.get("recipient_names") or []),
                    recipient_emails=list(
                        cleaned.get("recipient_emails")
                        or cleaned.get("to")
                        or ["alex@morgan.example"]
                    ),
                    subject=str(cleaned.get("subject") or "(no subject)"),
                    body_text=str(cleaned.get("body_text") or cleaned.get("body") or ""),
                )
            )
        return CorpusConversation(id=conv_id, messages=messages)
