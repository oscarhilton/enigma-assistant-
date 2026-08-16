"""Deterministic PAYG recording + replay (D11).

Stores sanitised ``TransformedContext`` request/response pairs only. Replay
never opens a network connection.

Mismatch policy
---------------
* ``fail`` (default) — raise :class:`ReplayMismatchError` when nothing matches.
* ``passthrough`` — call an optional inner transport **unless**
  ``force_offline=True`` (forced offline always fails closed).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import PaygTransport, ReasoningResult
from personal_enigma.transformation import TransformedContext

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?!\w)"
)
_FORBIDDEN_MARKERS = (
    "PrivatePerson",
    "PrivateNote",
    "email_addresses",
    "phone_numbers",
)


class ReplayMismatchPolicy(StrEnum):
    """Behaviour when a request hash / step has no recording."""

    FAIL = "fail"
    PASSTHROUGH = "passthrough"


class ReplayMismatchError(LookupError):
    """No recording matched the request under the fail / force-offline policy."""


class RecordingPrivacyError(ValueError):
    """Recording payload contains forbidden private material."""


class ProviderRecording(BaseModel):
    """One sanitised request/response pair (TransformedContext wire shape)."""

    request_hash: str
    scenario_step: str | None = None
    model: str
    prompt: str
    context: dict[str, Any]
    response_text: str
    response_metadata: dict[str, str] = Field(default_factory=dict)

    def to_result(self) -> ReasoningResult:
        summary = str(self.context.get("summary", ""))
        prompt_tokens = max(1, len(self.prompt.split()) + len(summary.split()))
        completion_tokens = max(1, len(self.response_text.split()) or 1)
        return ReasoningResult(
            text=self.response_text,
            model=self.model,
            usage=UsageRecord(
                model=self.model,
                mode=ReasoningMode.ENABLED,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=0.0,
                dry_run=False,
                metadata={"provider": "replay", "request_hash": self.request_hash},
            ),
            dry_run=False,
            metadata={
                **self.response_metadata,
                "provider": "replay",
                "request_hash": self.request_hash,
            },
        )


class RecordingStore(BaseModel):
    """Collection of provider recordings (YAML/JSON on disk)."""

    version: str = "1"
    scenario: str = ""
    recordings: list[ProviderRecording] = Field(default_factory=list)

    def by_hash(self) -> dict[str, ProviderRecording]:
        return {r.request_hash: r for r in self.recordings}


def request_hash(
    *,
    model: str,
    prompt: str,
    context: TransformedContext | Mapping[str, Any],
) -> str:
    """Stable SHA-256 over model + prompt + context JSON."""
    payload = {"model": model, "prompt": prompt, "context": _context_dict(context)}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def assert_recording_safe(recording: ProviderRecording | Mapping[str, Any]) -> None:
    """Refuse PrivatePerson fields, wholesale-note markers, or raw contact PII."""
    data = recording if isinstance(recording, Mapping) else recording.model_dump(mode="json")
    blob = json.dumps(data, default=str, ensure_ascii=False)
    for marker in _FORBIDDEN_MARKERS:
        if marker in blob:
            raise RecordingPrivacyError(f"recording must not contain {marker!r}")
    if _EMAIL_RE.search(blob):
        raise RecordingPrivacyError("recording must not contain raw email addresses")
    if _PHONE_RE.search(blob):
        raise RecordingPrivacyError("recording must not contain raw phone numbers")
    ctx = data.get("context") if isinstance(data, Mapping) else None
    if not isinstance(ctx, Mapping) or ctx.get("may_transmit_remotely") is not True:
        raise RecordingPrivacyError(
            "recording context must be remote-safe TransformedContext "
            "(may_transmit_remotely=True)"
        )


def load_recording_store(path: Path | str) -> RecordingStore:
    """Load JSON (preferred) or YAML recordings; validates privacy on each entry."""
    root = Path(path)
    text = root.read_text(encoding="utf-8")
    if root.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise ImportError("PyYAML required to load .yaml recording stores") from exc
        raw: Any = yaml.safe_load(text) or {}
    else:
        raw = json.loads(text)
    store = RecordingStore.model_validate(raw)
    for rec in store.recordings:
        assert_recording_safe(rec)
    return store


def save_recording_store(store: RecordingStore, path: Path | str) -> None:
    """Persist recordings as JSON (Demo Mode artefacts only)."""
    for rec in store.recordings:
        assert_recording_safe(rec)
    root = Path(path)
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text(
        json.dumps(store.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


class RecordingPaygTransport:
    """Demo-only wrapper that records sanitised PAYG pairs from an inner transport."""

    def __init__(
        self,
        inner: PaygTransport,
        *,
        store: RecordingStore | None = None,
        scenario: str = "",
        step_prefix: str = "step",
    ) -> None:
        self._inner = inner
        self.store = store or RecordingStore(scenario=scenario)
        if scenario:
            self.store.scenario = scenario
        self._step_prefix = step_prefix
        self._step_index = 0
        self.calls: list[str] = []

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        result = self._inner.complete(model=model, prompt=prompt, context=context)
        digest = request_hash(model=model, prompt=prompt, context=context)
        self._step_index += 1
        recording = ProviderRecording(
            request_hash=digest,
            scenario_step=f"{self._step_prefix}-{self._step_index:04d}",
            model=model,
            prompt=prompt,
            context=context.model_dump(mode="json"),
            response_text=result.text,
            response_metadata={k: str(v) for k, v in result.metadata.items()},
        )
        assert_recording_safe(recording)
        self.store.recordings.append(recording)
        self.calls.append(digest)
        return result

    def save(self, path: Path | str) -> None:
        save_recording_store(self.store, path)


class ReplayPaygTransport:
    """Serve recordings by request hash. Never opens a network socket."""

    def __init__(
        self,
        store: RecordingStore | Path | str,
        *,
        mismatch: ReplayMismatchPolicy | Literal["fail", "passthrough"] = (
            ReplayMismatchPolicy.FAIL
        ),
        inner: PaygTransport | None = None,
        force_offline: bool = True,
    ) -> None:
        if isinstance(store, (str, Path)):
            self.store = load_recording_store(store)
        else:
            self.store = store
            for rec in self.store.recordings:
                assert_recording_safe(rec)
        self.mismatch = (
            mismatch
            if isinstance(mismatch, ReplayMismatchPolicy)
            else ReplayMismatchPolicy(mismatch)
        )
        self._inner = inner
        self.force_offline = force_offline
        self.calls: list[str] = []

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        digest = request_hash(model=model, prompt=prompt, context=context)
        self.calls.append(digest)
        hit = self.store.by_hash().get(digest)
        if hit is not None:
            return hit.to_result()

        if self.force_offline or self.mismatch is ReplayMismatchPolicy.FAIL or self._inner is None:
            raise ReplayMismatchError(
                f"no recording for request_hash={digest[:12]}… "
                f"(policy={self.mismatch.value}, force_offline={self.force_offline})"
            )
        return self._inner.complete(model=model, prompt=prompt, context=context)


def _context_dict(context: TransformedContext | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(context, TransformedContext):
        return context.model_dump(mode="json")
    return dict(context)


__all__ = [
    "ProviderRecording",
    "RecordingPaygTransport",
    "RecordingPrivacyError",
    "RecordingStore",
    "ReplayMismatchError",
    "ReplayMismatchPolicy",
    "ReplayPaygTransport",
    "assert_recording_safe",
    "load_recording_store",
    "request_hash",
    "save_recording_store",
]
