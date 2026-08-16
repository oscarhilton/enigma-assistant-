"""Arm B LLM Judge evaluation harness (scaffold).

See ``docs/architecture/reasoning-llm-benchmark.md`` and ADR-011.
"""

from personal_enigma.evaluation.llm_judge.authority import (
    AuthorityResult,
    JudgeAuthorityError,
    apply_code_authority,
)
from personal_enigma.evaluation.llm_judge.harness import (
    LIVE_API_KEY_ENV,
    LIVE_ENV_FLAG,
    JudgeHarness,
    JudgeHarnessError,
    JudgeHarnessMode,
    default_fixture_path,
    live_enabled_from_env,
    load_judge_fixture,
)
from personal_enigma.evaluation.llm_judge.payload import (
    EvidenceItem,
    JudgeCandidate,
    JudgeCheckpointRequest,
)
from personal_enigma.evaluation.llm_judge.schema import (
    JudgementAttention,
    JudgementImportance,
    JudgementKind,
    JudgementStatus,
    JudgementTiming,
    JudgeResponse,
    StructuredJudgement,
)

__all__ = [
    "LIVE_API_KEY_ENV",
    "LIVE_ENV_FLAG",
    "AuthorityResult",
    "EvidenceItem",
    "JudgeAuthorityError",
    "JudgeCandidate",
    "JudgeCheckpointRequest",
    "JudgeHarness",
    "JudgeHarnessError",
    "JudgeHarnessMode",
    "JudgeResponse",
    "JudgementAttention",
    "JudgementImportance",
    "JudgementKind",
    "JudgementStatus",
    "JudgementTiming",
    "StructuredJudgement",
    "apply_code_authority",
    "default_fixture_path",
    "live_enabled_from_env",
    "load_judge_fixture",
]
