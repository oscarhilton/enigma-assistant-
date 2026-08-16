"""Background email corpus plumbing for Demo Mode (D08b scaffold).

Governing rule: Story creates meaning. Corpus creates noise.
See ``docs/architecture/demo-corpus.md`` and ADR-007.
"""

from __future__ import annotations

from personal_enigma.simulation.corpus.cache import CorpusCache, default_cache_root
from personal_enigma.simulation.corpus.manifest import CorpusManifest, load_manifest
from personal_enigma.simulation.corpus.models import (
    CorpusConversation,
    CorpusMessage,
    CorpusMetadata,
    CorpusProvenance,
)
from personal_enigma.simulation.corpus.protocol import CorpusAdapter
from personal_enigma.simulation.corpus.registry import CorpusRegistry, default_registry
from personal_enigma.simulation.corpus.safety import (
    PublicDemoCorpusError,
    assert_public_demo_allowed,
)
from personal_enigma.simulation.corpus.sanitise import (
    GENERATION_METADATA_KEYS,
    sanitise_conversation,
)
from personal_enigma.simulation.corpus.selectors import select_conversations
from personal_enigma.simulation.corpus.streams import (
    CanonicalScenarioStream,
    CorpusBackgroundStream,
    GeneratedNoiseStream,
    MailStream,
    merge_stream_events,
)
from personal_enigma.simulation.corpus.timeline import place_conversation_on_timeline

__all__ = [
    "GENERATION_METADATA_KEYS",
    "CanonicalScenarioStream",
    "CorpusAdapter",
    "CorpusBackgroundStream",
    "CorpusCache",
    "CorpusConversation",
    "CorpusManifest",
    "CorpusMessage",
    "CorpusMetadata",
    "CorpusProvenance",
    "CorpusRegistry",
    "GeneratedNoiseStream",
    "MailStream",
    "PublicDemoCorpusError",
    "assert_public_demo_allowed",
    "default_cache_root",
    "default_registry",
    "load_manifest",
    "merge_stream_events",
    "place_conversation_on_timeline",
    "sanitise_conversation",
    "select_conversations",
]
