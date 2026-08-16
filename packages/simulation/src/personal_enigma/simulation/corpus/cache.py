"""Local dataset + derived corpus cache roots (ADR-007)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from personal_enigma.simulation.corpus.models import CorpusConversation
from personal_enigma.simulation.corpus.sanitise import SANITISER_VERSION


def default_cache_root() -> Path:
    override = os.environ.get("ENIGMA_CORPUS_CACHE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "enigma" / "datasets"


def default_derived_root() -> Path:
    override = os.environ.get("ENIGMA_CORPUS_DERIVED")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "enigma" / "datasets-derived"


class CorpusCache:
    """Resolve on-disk paths for pinned corpus revisions."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_cache_root()

    def revision_dir(self, corpus_id: str, revision: str) -> Path:
        return self.root / corpus_id / revision

    def ensure_revision_dir(self, corpus_id: str, revision: str) -> Path:
        path = self.revision_dir(corpus_id, revision)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, corpus_id: str, revision: str) -> bool:
        path = self.revision_dir(corpus_id, revision)
        return path.exists() and any(path.iterdir())


class DerivedCorpusCache:
    """Demo-safe derived indexes keyed by corpus + revision + sanitiser + seed."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_derived_root()

    def profile_dir(
        self,
        corpus_id: str,
        *,
        revision: str,
        sanitiser_version: str = SANITISER_VERSION,
        seed: str,
        profile: str = "demo-safe-v1",
    ) -> Path:
        return (
            self.root
            / corpus_id
            / revision
            / f"sanitiser-{sanitiser_version}"
            / f"seed-{seed}"
            / profile
        )

    def ensure_profile_dir(
        self,
        corpus_id: str,
        *,
        revision: str,
        sanitiser_version: str = SANITISER_VERSION,
        seed: str,
        profile: str = "demo-safe-v1",
    ) -> Path:
        path = self.profile_dir(
            corpus_id,
            revision=revision,
            sanitiser_version=sanitiser_version,
            seed=seed,
            profile=profile,
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_build(
        self,
        target: Path,
        *,
        manifest: dict[str, Any],
        accepted: list[CorpusConversation],
        rejected: list[dict[str, Any]],
    ) -> Path:
        target.mkdir(parents=True, exist_ok=True)
        (target / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with (target / "conversations.jsonl").open("w", encoding="utf-8") as handle:
            for conv in accepted:
                handle.write(conv.model_dump_json() + "\n")
        with (target / "rejected.jsonl").open("w", encoding="utf-8") as handle:
            for row in rejected:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        return target

    def read_conversations(self, target: Path) -> list[CorpusConversation]:
        path = target / "conversations.jsonl"
        if not path.exists():
            return []
        out: list[CorpusConversation] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    out.append(CorpusConversation.model_validate_json(line))
        return out

    def read_manifest(self, target: Path) -> dict[str, Any]:
        path = target / "manifest.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
