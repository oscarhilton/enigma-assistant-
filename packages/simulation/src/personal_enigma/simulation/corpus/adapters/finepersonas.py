"""FinePersonas / local JSONL conversation adapter (fixture-first).

Hugging Face downloads are opt-in via ``fetch_huggingface`` / CLI
``--force-network`` and must never run in PR CI.
"""

from __future__ import annotations

import json
import shutil
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

DEFAULT_HF_DATASET = "argilla/FinePersonas-Synthetic-Email-Conversations"


class FinePersonasAdapter:
    """Load FinePersonas-shaped conversations from a local root."""

    def __init__(self, manifest: CorpusManifest, *, root: Path | None = None) -> None:
        self.manifest = manifest
        self.root = root or Path(".")

    def _conversations_path(self) -> Path:
        candidate = self.root / "conversations.jsonl"
        if candidate.exists():
            return candidate
        # Allow a nested HF-style dump.
        nested = self.root / "data" / "conversations.jsonl"
        return nested if nested.exists() else candidate

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
            if False:  # pragma: no cover — keep AsyncIterator typing
                yield CorpusConversation(id="", messages=[])
            return
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
            to_field = cleaned.get("recipient_emails") or cleaned.get("to") or []
            if isinstance(to_field, str):
                to_field = [to_field]
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
                    recipient_emails=list(to_field or ["alex@morgan.example"]),
                    subject=str(cleaned.get("subject") or "(no subject)"),
                    body_text=str(cleaned.get("body_text") or cleaned.get("body") or ""),
                )
            )
        return CorpusConversation(id=conv_id, messages=messages)


def materialise_local_fixture(
    *,
    source_root: Path,
    target_root: Path,
) -> Path:
    """Copy a local fixture / cache tree into ``target_root`` (no network)."""
    target_root.mkdir(parents=True, exist_ok=True)
    src_jsonl = source_root / "conversations.jsonl"
    if not src_jsonl.exists():
        raise FileNotFoundError(f"missing conversations.jsonl under {source_root}")
    shutil.copy2(src_jsonl, target_root / "conversations.jsonl")
    for name in ("manifest.yaml", "manifest.yml", "README.md"):
        src = source_root / name
        if src.exists():
            shutil.copy2(src, target_root / name)
    return target_root


def fetch_huggingface(
    *,
    dataset: str,
    revision: str,
    target_root: Path,
    max_conversations: int | None = None,
) -> Path:
    """Download FinePersonas from Hugging Face into ``target_root``.

    Requires optional ``datasets`` package. Never call from PR CI.
    """
    try:
        from datasets import load_dataset  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Hugging Face fetch requires the optional 'datasets' package. "
            "Install it locally, or use finepersonas-mini fixtures for CI."
        ) from exc

    target_root.mkdir(parents=True, exist_ok=True)
    ds = load_dataset(dataset, split="train", revision=revision)
    out_path = target_root / "conversations.jsonl"
    written = 0
    with out_path.open("w", encoding="utf-8") as handle:
        for row in ds:
            handle.write(json.dumps(dict(row), default=str) + "\n")
            written += 1
            if max_conversations is not None and written >= max_conversations:
                break
    (target_root / "FETCH_META.json").write_text(
        json.dumps(
            {
                "dataset": dataset,
                "revision": revision,
                "conversations_written": written,
                "truncated": max_conversations is not None,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return target_root
