"""PAYG reasoning — remote calls only over TransformedContext."""

from personal_enigma.reasoning.client import PaygReasoningService, build_reasoning_client
from personal_enigma.reasoning.errors import PrivacyGateError, ReasoningDisabledError
from personal_enigma.reasoning.fireworks_transport import (
    DEFAULT_FIREWORKS_MODEL,
    FireworksChatTransport,
    default_fireworks_model,
    fireworks_seed,
)
from personal_enigma.reasoning.logging import (
    InMemoryUsageLogger,
    NullUsageLogger,
    UsageLogger,
    UsageRecord,
)
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.openai_transport import OpenAIChatTransport
from personal_enigma.reasoning.protocol import (
    PaygReasoningClient,
    PaygTransport,
    ReasoningResult,
)
from personal_enigma.reasoning.replay_transport import (
    RecordingPaygTransport,
    ReplayMismatchError,
    ReplayMismatchPolicy,
    ReplayPaygTransport,
)
from personal_enigma.reasoning.structured_output import (
    LlmJudgeOutput,
    LlmJudgeParseError,
    parse_llm_judge_output,
)
from personal_enigma.reasoning.transport import MockPaygTransport, NullPaygTransport

__all__ = [
    "DEFAULT_FIREWORKS_MODEL",
    "FireworksChatTransport",
    "InMemoryUsageLogger",
    "LlmJudgeOutput",
    "LlmJudgeParseError",
    "MockPaygTransport",
    "NullPaygTransport",
    "OpenAIChatTransport",
    "NullUsageLogger",
    "PaygReasoningClient",
    "PaygReasoningService",
    "PaygTransport",
    "PrivacyGateError",
    "ReasoningDisabledError",
    "ReasoningMode",
    "ReasoningResult",
    "RecordingPaygTransport",
    "ReplayMismatchError",
    "ReplayMismatchPolicy",
    "ReplayPaygTransport",
    "UsageLogger",
    "UsageRecord",
    "build_reasoning_client",
    "default_fireworks_model",
    "fireworks_seed",
    "parse_llm_judge_output",
]
