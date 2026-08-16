"""Corpus registry — known manifests + adapter factories (stubs)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from personal_enigma.simulation.corpus.adapters.finepersonas import FinePersonasAdapter
from personal_enigma.simulation.corpus.adapters.maildir import MaildirAdapter
from personal_enigma.simulation.corpus.adapters.mbox import MboxAdapter
from personal_enigma.simulation.corpus.manifest import (
    CorpusLicenceSpec,
    CorpusManifest,
    CorpusProfilesAllowed,
    CorpusSourceSpec,
    load_manifest,
)
from personal_enigma.simulation.corpus.models import CorpusProvenance
from personal_enigma.simulation.corpus.protocol import CorpusAdapter

AdapterFactory = Callable[[CorpusManifest, Path | None], CorpusAdapter]

_ADAPTERS: dict[str, AdapterFactory] = {
    "finepersonas": lambda m, p: FinePersonasAdapter(m, root=p),
    "mbox": lambda m, p: MboxAdapter(m, root=p),
    "maildir": lambda m, p: MaildirAdapter(m, root=p),
}

_PACKAGE_ROOT = Path(__file__).resolve().parents[4]
_MINI_MANIFEST = (
    _PACKAGE_ROOT / "tests" / "fixtures" / "corpus" / "finepersonas-mini" / "manifest.yaml"
)


class CorpusRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, CorpusManifest] = {}
        self._roots: dict[str, Path] = {}

    def register(self, manifest: CorpusManifest, *, root: Path | None = None) -> None:
        self._manifests[manifest.id] = manifest
        if root is not None:
            self._roots[manifest.id] = root

    def register_manifest_path(self, path: Path) -> CorpusManifest:
        manifest = load_manifest(path)
        self.register(manifest, root=path.parent)
        return manifest

    def get(self, corpus_id: str) -> CorpusManifest:
        try:
            return self._manifests[corpus_id]
        except KeyError as exc:
            raise KeyError(f"unknown corpus id: {corpus_id!r}") from exc

    def list_ids(self) -> list[str]:
        return sorted(self._manifests)

    def adapter_for(self, corpus_id: str) -> CorpusAdapter:
        manifest = self.get(corpus_id)
        factory = _ADAPTERS.get(manifest.format_adapter)
        if factory is None:
            raise KeyError(f"no adapter for format {manifest.format_adapter!r}")
        return factory(manifest, self._roots.get(corpus_id))


def default_registry() -> CorpusRegistry:
    """Registry with the checked-in finepersonas-mini fixture when present."""
    registry = CorpusRegistry()
    if _MINI_MANIFEST.exists():
        registry.register_manifest_path(_MINI_MANIFEST)
    else:
        registry.register(
            CorpusManifest(
                id="finepersonas-mini",
                provenance=CorpusProvenance.SYNTHETIC_CONFIRMED,
                adapter="finepersonas",
                synthetic=True,
                source=CorpusSourceSpec(type="local", revision="mini-v1"),
                licence=CorpusLicenceSpec(
                    declared="original-synthetic-fixture",
                    redistribution_reviewed=True,
                ),
                profiles_allowed=CorpusProfilesAllowed(
                    public_demo=True,
                    developer=True,
                    stress=True,
                ),
            )
        )
    return registry
