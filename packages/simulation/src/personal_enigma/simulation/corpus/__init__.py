"""Background email corpus plumbing for Demo Mode (D08b).

Governing rule: Story creates meaning. Corpus creates noise.
See ``docs/architecture/demo-corpus.md`` and ADR-007.
"""

from __future__ import annotations

from personal_enigma.simulation.corpus.background import (
    CANONICAL_BACKGROUND_MESSAGE_TARGET,
    CI_SCALE_LADDER_POINTS,
    DEMO_BACKGROUND_MESSAGE_TARGET,
    FULL_SCALE_LADDER_POINTS,
    STRESS_BACKGROUND_MESSAGE_TARGET,
    STRESS_NOISE_MESSAGE_TARGET,
    STRESS_STRETCH_BACKGROUND_MESSAGE_TARGET,
    BackgroundBuildResult,
    BackgroundConfig,
    BackgroundSignalTruth,
    DocumentedProfileTargets,
    build_background_stream,
    canonical_contact_emails,
    load_background_config,
    load_scenario_background,
)
from personal_enigma.simulation.corpus.cache import (
    CorpusCache,
    DerivedCorpusCache,
    default_cache_root,
    default_derived_root,
)
from personal_enigma.simulation.corpus.expand import expand_conversations
from personal_enigma.simulation.corpus.manifest import CorpusManifest, load_manifest
from personal_enigma.simulation.corpus.models import (
    CorpusConversation,
    CorpusMessage,
    CorpusMetadata,
    CorpusProvenance,
)
from personal_enigma.simulation.corpus.noise import (
    CANONICAL_NOISE_MESSAGE_TARGET,
    DEMO_NOISE_MESSAGE_TARGET,
    MAX_BACKGROUND_FALSE_ALERTS_PER_1K,
    NOISE_CATEGORIES,
    QUIET_DAY_MESSAGE_COUNT,
    QUIET_DAY_NOISE_MESSAGE_COUNT,
    NoiseBuildResult,
    NoiseConfig,
    NoiseSignalTruth,
    build_noise_stream,
    load_noise_config,
    load_scenario_noise,
    looks_like_machine_noise,
)
from personal_enigma.simulation.corpus.pipeline import (
    CorpusBuildResult,
    build_demo_safe_corpus,
    collect_conversations,
)
from personal_enigma.simulation.corpus.protocol import CorpusAdapter
from personal_enigma.simulation.corpus.registry import CorpusRegistry, default_registry
from personal_enigma.simulation.corpus.safety import (
    PublicDemoCorpusError,
    assert_public_demo_allowed,
)
from personal_enigma.simulation.corpus.sanitise import (
    GENERATION_METADATA_KEYS,
    SANITISER_VERSION,
    SanitiseResult,
    sanitise_conversation,
    sanitise_conversation_detailed,
    sanitise_raw_record,
)
from personal_enigma.simulation.corpus.selectors import select_conversations
from personal_enigma.simulation.corpus.streams import (
    CanonicalScenarioStream,
    CorpusBackgroundStream,
    GeneratedNoiseStream,
    MailStream,
    merge_stream_events,
)
from personal_enigma.simulation.corpus.timeline import (
    place_conversation_on_timeline,
    place_conversations_on_timeline,
)

# Prefer D08d noise module constants for shared noise budgets.

__all__ = [
    "CANONICAL_BACKGROUND_MESSAGE_TARGET",
    "CANONICAL_NOISE_MESSAGE_TARGET",
    "CI_SCALE_LADDER_POINTS",
    "DEMO_BACKGROUND_MESSAGE_TARGET",
    "DEMO_NOISE_MESSAGE_TARGET",
    "FULL_SCALE_LADDER_POINTS",
    "GENERATION_METADATA_KEYS",
    "MAX_BACKGROUND_FALSE_ALERTS_PER_1K",
    "NOISE_CATEGORIES",
    "QUIET_DAY_MESSAGE_COUNT",
    "QUIET_DAY_NOISE_MESSAGE_COUNT",
    "SANITISER_VERSION",
    "STRESS_BACKGROUND_MESSAGE_TARGET",
    "STRESS_NOISE_MESSAGE_TARGET",
    "STRESS_STRETCH_BACKGROUND_MESSAGE_TARGET",
    "BackgroundBuildResult",
    "BackgroundConfig",
    "BackgroundSignalTruth",
    "CanonicalScenarioStream",
    "CorpusAdapter",
    "CorpusBackgroundStream",
    "CorpusBuildResult",
    "CorpusCache",
    "CorpusConversation",
    "CorpusManifest",
    "CorpusMessage",
    "CorpusMetadata",
    "CorpusProvenance",
    "CorpusRegistry",
    "DerivedCorpusCache",
    "DocumentedProfileTargets",
    "GeneratedNoiseStream",
    "MailStream",
    "NoiseBuildResult",
    "NoiseConfig",
    "NoiseSignalTruth",
    "PublicDemoCorpusError",
    "SanitiseResult",
    "assert_public_demo_allowed",
    "build_background_stream",
    "build_demo_safe_corpus",
    "build_noise_stream",
    "canonical_contact_emails",
    "collect_conversations",
    "default_cache_root",
    "default_derived_root",
    "default_registry",
    "expand_conversations",
    "load_background_config",
    "load_manifest",
    "load_noise_config",
    "load_scenario_background",
    "load_scenario_noise",
    "looks_like_machine_noise",
    "merge_stream_events",
    "place_conversation_on_timeline",
    "place_conversations_on_timeline",
    "sanitise_conversation",
    "sanitise_conversation_detailed",
    "sanitise_raw_record",
    "select_conversations",
]
