"""Local dataset cache roots (ADR-007)."""

from __future__ import annotations

from pathlib import Path


def default_cache_root() -> Path:
    return Path.home() / ".cache" / "enigma" / "datasets"


def default_derived_root() -> Path:
    return Path.home() / ".cache" / "enigma" / "datasets-derived"


class CorpusCache:
    """Resolve on-disk paths for pinned corpus revisions. Does not download."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_cache_root()

    def revision_dir(self, corpus_id: str, revision: str) -> Path:
        return self.root / corpus_id / revision

    def ensure_revision_dir(self, corpus_id: str, revision: str) -> Path:
        path = self.revision_dir(corpus_id, revision)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, corpus_id: str, revision: str) -> bool:
        return self.revision_dir(corpus_id, revision).exists()
