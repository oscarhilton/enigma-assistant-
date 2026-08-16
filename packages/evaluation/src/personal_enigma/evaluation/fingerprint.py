"""Corpus fingerprint helpers for eval reports (D08e)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from personal_enigma.simulation.corpus.sanitise import SANITISER_VERSION


@dataclass(frozen=True, slots=True)
class CorpusFingerprint:
    """Stable fingerprint recorded on every scale / A/B eval report."""

    corpus_id: str
    seed: str
    profile: str
    revision: str
    sanitiser_version: str
    digest: str
    n_messages: int = 0
    corpus_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        ids = list(self.corpus_ids) if self.corpus_ids else [self.corpus_id]
        return {
            "corpus_id": self.corpus_id,
            "corpus_ids": ids,
            "seed": self.seed,
            "profile": self.profile,
            "revision": self.revision,
            "corpus_revision": self.revision,
            "sanitiser_version": self.sanitiser_version,
            "n_messages": self.n_messages,
            "digest": self.digest,
        }


def corpus_fingerprint(
    *,
    corpus_id: str | None = None,
    corpus_ids: Sequence[str] | None = None,
    seed: str,
    profile: str,
    revision: str = "unknown",
    corpus_revision: str | None = None,
    sanitiser_version: str | None = None,
    n_messages: int = 0,
    extra: dict[str, Any] | None = None,
) -> CorpusFingerprint:
    """Build a stable fingerprint (id, revision, sanitiser, seed, profile, digest)."""
    ids = list(corpus_ids) if corpus_ids else ([corpus_id] if corpus_id else ["unknown"])
    primary = ids[0]
    rev = corpus_revision if corpus_revision is not None else revision
    sanitiser = sanitiser_version or SANITISER_VERSION
    material = "|".join(
        [
            ",".join(sorted(ids)),
            rev,
            sanitiser,
            seed,
            profile,
            str(n_messages),
        ]
    )
    if extra:
        material += "|" + ",".join(f"{k}={extra[k]}" for k in sorted(extra))
    digest = sha256(material.encode()).hexdigest()[:16]
    return CorpusFingerprint(
        corpus_id=primary,
        seed=seed,
        profile=profile,
        revision=rev,
        sanitiser_version=sanitiser,
        digest=digest,
        n_messages=n_messages,
        corpus_ids=tuple(sorted(ids)),
    )


__all__ = ["CorpusFingerprint", "corpus_fingerprint"]
