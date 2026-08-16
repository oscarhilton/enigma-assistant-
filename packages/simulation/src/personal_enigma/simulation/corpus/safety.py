"""Public-demo provenance gates (ADR-007)."""

from __future__ import annotations

from personal_enigma.simulation.corpus.manifest import CorpusManifest
from personal_enigma.simulation.corpus.models import CorpusProvenance


class PublicDemoCorpusError(ValueError):
    """Raised when a non-synthetic corpus is loaded into a public Demo profile."""


def assert_public_demo_allowed(manifest: CorpusManifest) -> None:
    """Public Demo accepts only SYNTHETIC_CONFIRMED corpora with public_demo allowed."""
    if manifest.provenance != CorpusProvenance.SYNTHETIC_CONFIRMED:
        raise PublicDemoCorpusError(
            f"public Demo rejects corpus {manifest.id!r} with provenance "
            f"{manifest.provenance.value!r}; expected "
            f"{CorpusProvenance.SYNTHETIC_CONFIRMED.value!r}"
        )
    if not manifest.profiles_allowed.public_demo:
        raise PublicDemoCorpusError(
            f"corpus {manifest.id!r} is not allowed in public_demo profiles"
        )
