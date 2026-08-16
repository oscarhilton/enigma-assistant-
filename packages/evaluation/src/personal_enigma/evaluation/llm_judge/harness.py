"""Arm B LLM Judge harness — DRY_RUN / fixture-replay / optional live.

CI defaults to fixture replay. Live ENABLED requires
``ENIGMA_LLM_JUDGE_LIVE=1`` and an API key (developer only).
"""

from __future__ import annotations

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.llm_judge.authority import (
    AuthorityResult,
    apply_code_authority,
)
from personal_enigma.evaluation.llm_judge.payload import JudgeCheckpointRequest
from personal_enigma.evaluation.llm_judge.schema import JudgeResponse
from personal_enigma.reasoning import (
    OpenAIChatTransport,
    PaygReasoningService,
    ReasoningMode,
)
from personal_enigma.reasoning.errors import ReasoningDisabledError
from personal_enigma.transformation import TransformedContext

LIVE_ENV_FLAG = "ENIGMA_LLM_JUDGE_LIVE"
LIVE_API_KEY_ENV = "OPENAI_API_KEY"


class JudgeHarnessMode(StrEnum):
    """Harness modes (mirrors PAYG intent; replay is CI-default)."""

    DISABLED = "disabled"
    DRY_RUN = "dry_run"
    REPLAY = "replay"
    ENABLED = "enabled"


class JudgeHarnessError(RuntimeError):
    """Harness misconfiguration or unavailable live path."""


def default_fixture_path(name: str = "parents-brunch-wed-noon") -> Path:
    """Checked-in Judge fixture under ``packages/evaluation/fixtures/llm_judge/``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "packages" / "evaluation" / "fixtures" / "llm_judge" / f"{name}.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no llm_judge fixture found for {name!r}")


def load_judge_fixture(path: Path | str) -> tuple[JudgeCheckpointRequest, JudgeResponse]:
    """Load frozen request + Judge response from a JSON fixture."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    request = JudgeCheckpointRequest.model_validate(data["request"])
    response = JudgeResponse.model_validate(data["response"])
    return request, response


def live_enabled_from_env(
    *,
    environ: dict[str, str] | None = None,
) -> bool:
    """True only when developer explicitly opts into live Judge calls with a key."""
    env = environ if environ is not None else os.environ
    flag = env.get(LIVE_ENV_FLAG, "").strip().lower()
    if flag not in {"1", "true", "yes", "on"}:
        return False
    return bool(env.get(LIVE_API_KEY_ENV, "").strip())


class JudgeHarness:
    """Thin Arm B harness: replay / dry-run by default; live is opt-in."""

    def __init__(
        self,
        *,
        mode: JudgeHarnessMode = JudgeHarnessMode.REPLAY,
        fixture_path: Path | str | None = None,
        must_suppress_ids: frozenset[str] | set[str] | None = None,
        max_judgements: int | None = None,
        reasoning: PaygReasoningService | None = None,
    ) -> None:
        self._mode = mode
        self._fixture_path = Path(fixture_path) if fixture_path else None
        self._must_suppress_ids = must_suppress_ids
        self._max_judgements = max_judgements
        self._reasoning = reasoning

    @property
    def mode(self) -> JudgeHarnessMode:
        return self._mode

    def run(
        self,
        request: JudgeCheckpointRequest | None = None,
    ) -> AuthorityResult:
        """Execute one checkpoint Judge pass under the configured mode."""
        if self._mode is JudgeHarnessMode.DISABLED:
            raise ReasoningDisabledError("LLM Judge harness is disabled")

        if self._mode is JudgeHarnessMode.REPLAY:
            path = self._fixture_path or default_fixture_path()
            frozen_request, response = load_judge_fixture(path)
            effective = request or frozen_request
            return apply_code_authority(
                effective,
                response,
                must_suppress_ids=self._must_suppress_ids,
                max_judgements=self._max_judgements,
            )

        if request is None:
            raise JudgeHarnessError("request required unless mode is replay with fixture")

        if self._mode is JudgeHarnessMode.DRY_RUN:
            # Privacy gate on context when present; no network; empty proposal.
            empty = JudgeResponse(judgements=[], model="dry-run", schema_version="1")
            return apply_code_authority(
                request,
                empty,
                must_suppress_ids=self._must_suppress_ids,
                max_judgements=self._max_judgements,
            )

        # ENABLED — developer live path only.
        if not live_enabled_from_env():
            raise JudgeHarnessError(
                f"live Judge requires {LIVE_ENV_FLAG}=1 and {LIVE_API_KEY_ENV}; "
                "CI must use replay or dry_run"
            )
        response = self._live_judge(request)
        return apply_code_authority(
            request,
            response,
            must_suppress_ids=self._must_suppress_ids,
            max_judgements=self._max_judgements,
        )

    def _live_judge(self, request: JudgeCheckpointRequest) -> JudgeResponse:
        context = request.context or _context_from_request(request)
        client = self._reasoning or PaygReasoningService(
            mode=ReasoningMode.ENABLED,
            transport=OpenAIChatTransport(),
            default_model="gpt-4o-mini",
        )
        prompt = (
            "Return JSON only matching JudgeResponse schema_version=1 with "
            "judgements[]. fields: candidate_id, kind, status, importance, "
            "attention, timing, confidence, reason_codes, evidence_ids. No CoT."
        )
        result = client.reason(context, prompt=prompt)
        return _parse_judge_text(result.text, model=result.model)


def _context_from_request(request: JudgeCheckpointRequest) -> TransformedContext:
    lines = [
        f"checkpoint={request.checkpoint_id}",
        f"clock={request.clock}",
        f"scenario={request.scenario}",
    ]
    entities: list[str] = []
    for cand in request.candidates:
        lines.append(
            f"candidate {cand.candidate_id}: {cand.title} "
            f"evidence={','.join(cand.evidence_ids)}"
        )
    for item in request.evidence:
        lines.append(f"evidence {item.evidence_id}: {item.summary}")
        entities.extend(item.entities)
    return TransformedContext(
        summary="\n".join(lines),
        entities=sorted(set(entities)),
        metadata={
            "source_type": "llm_judge_checkpoint",
            "record_id": request.checkpoint_id,
            "provider": "synthetic",
        },
        may_transmit_remotely=True,
    )


def _parse_judge_text(text: str, *, model: str) -> JudgeResponse:
    raw: Any = json.loads(text)
    if isinstance(raw, list):
        raw = {"judgements": raw, "model": model, "schema_version": "1"}
    elif isinstance(raw, dict) and "judgements" not in raw:
        raw = {"judgements": [raw], "model": model, "schema_version": "1"}
    if isinstance(raw, dict):
        raw.setdefault("model", model)
        raw.setdefault("schema_version", "1")
    return JudgeResponse.model_validate(raw)


__all__ = [
    "LIVE_API_KEY_ENV",
    "LIVE_ENV_FLAG",
    "JudgeHarness",
    "JudgeHarnessError",
    "JudgeHarnessMode",
    "default_fixture_path",
    "live_enabled_from_env",
    "load_judge_fixture",
]
