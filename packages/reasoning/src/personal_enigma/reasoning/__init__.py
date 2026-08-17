"""PAYG reasoning — remote calls only over TransformedContext."""

from personal_enigma.reasoning.client import PaygReasoningService, build_reasoning_client
from personal_enigma.reasoning.errors import PrivacyGateError, ReasoningDisabledError
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
    InvalidEvidenceIdsError,
    JudgeV1Attention,
    JudgeV1Output,
    JudgeV1ParseError,
    LlmJudgeParseError,
    NextActionV1,
    ReasonCode,
    parse_judge_v1_output,
    parse_llm_judge_output,
    validate_evidence_ids,
)
from personal_enigma.reasoning.transport import MockPaygTransport, NullPaygTransport

__all__ = [
    "InMemoryUsageLogger",
    "InvalidEvidenceIdsError",
    "JudgeV1Attention",
    "JudgeV1Output",
    "JudgeV1ParseError",
    "LlmJudgeParseError",
    "MockPaygTransport",
    "NextActionV1",
    "NullPaygTransport",
    "OpenAIChatTransport",
    "NullUsageLogger",
    "PaygReasoningClient",
    "PaygReasoningService",
    "PaygTransport",
    "PrivacyGateError",
    "ReasonCode",
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
    "parse_judge_v1_output",
    "parse_llm_judge_output",
    "validate_evidence_ids",
]
