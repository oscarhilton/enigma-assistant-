"""Corpus format adapters (stubs)."""

from __future__ import annotations

from personal_enigma.simulation.corpus.adapters.finepersonas import FinePersonasAdapter
from personal_enigma.simulation.corpus.adapters.maildir import MaildirAdapter
from personal_enigma.simulation.corpus.adapters.mbox import MboxAdapter

__all__ = ["FinePersonasAdapter", "MaildirAdapter", "MboxAdapter"]
