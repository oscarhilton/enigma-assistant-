"""Corpus manifest loading (pinned revisions, provenance, profile gates)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from personal_enigma.simulation.corpus.models import CorpusProvenance


class CorpusSourceSpec(BaseModel):
    type: str = "local"
    dataset: str | None = None
    revision: str | None = None
    path: str | None = None


class CorpusLicenceSpec(BaseModel):
    declared: str | None = None
    redistribution_reviewed: bool = False


class CorpusProfilesAllowed(BaseModel):
    public_demo: bool = False
    developer: bool = True
    stress: bool = True


class CorpusManifest(BaseModel):
    id: str
    source: CorpusSourceSpec = Field(default_factory=CorpusSourceSpec)
    licence: CorpusLicenceSpec = Field(default_factory=CorpusLicenceSpec)
    format_adapter: str = Field(default="finepersonas", alias="adapter")
    synthetic: bool = True
    provenance: CorpusProvenance = CorpusProvenance.UNKNOWN
    profiles_allowed: CorpusProfilesAllowed = Field(default_factory=CorpusProfilesAllowed)
    cache_checksum: str | None = None

    model_config = {"populate_by_name": True}


def load_manifest(path: Path | str) -> CorpusManifest:
    raw: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    # Allow nested content.synthetic / format.adapter shapes from the plan.
    if "format" in raw and isinstance(raw["format"], dict):
        raw.setdefault("adapter", raw["format"].get("adapter"))
    if "content" in raw and isinstance(raw["content"], dict):
        raw.setdefault("synthetic", raw["content"].get("synthetic", True))
    if "cache" in raw and isinstance(raw["cache"], dict):
        raw.setdefault("cache_checksum", raw["cache"].get("checksum"))
    return CorpusManifest.model_validate(raw)
