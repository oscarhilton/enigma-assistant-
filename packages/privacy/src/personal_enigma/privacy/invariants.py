"""Privacy invariant gate for remote-facing payloads.

Call :func:`assert_remote_payload_safe` (or the finer-grained helpers) before
any hosted-model transmission. Failures raise :class:`PrivacyInvariantError`
so CI and runtime refuse unsafe payloads.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from personal_enigma.domain import PrivateNote, PrivatePerson, SourceType
from personal_enigma.privacy.allowlist import (
    PERSON_PSEUDONYM_PREFIX,
    REMOTE_METADATA_KEYS,
    REMOTE_PAYLOAD_TOP_LEVEL_KEYS,
)
from personal_enigma.privacy.levels import PrivacyLevel, default_level_for_source
from personal_enigma.privacy.notes_policy import (
    NotesRemotePolicyException,
    wholesale_note_body_remote_safe,
)
from personal_enigma.privacy.remote import RemoteInferenceConfig, may_send_remotely

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"
)
_PERSON_TOKEN_RE = re.compile(rf"^{re.escape(PERSON_PSEUDONYM_PREFIX)}[0-9A-F]{{6}}$")


class PrivacyInvariantError(ValueError):
    """Raised when a remote payload violates privacy invariants."""


def payload_as_dict(payload: Any) -> dict[str, Any]:
    """Normalise a transformed context or mapping into a plain dict."""
    if isinstance(payload, Mapping):
        return dict(payload)
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError(f"Unsupported remote payload type: {type(payload)!r}")


def secrets_from_person(person: PrivatePerson) -> list[str]:
    """Collect raw ``PrivatePerson`` field values that must never appear remotely."""
    secrets: list[str] = []
    if person.display_name and person.display_name.strip():
        secrets.append(person.display_name.strip())
    secrets.extend(a.strip() for a in person.aliases if a.strip())
    secrets.extend(e.strip() for e in person.email_addresses if e.strip())
    secrets.extend(p.strip() for p in person.phone_numbers if p.strip())
    secrets.extend(o.strip() for o in person.organisations if o.strip())
    secrets.extend(pid.strip() for pid in person.provider_ids.values() if pid.strip())
    return secrets


def _serialised_blob(data: Mapping[str, Any]) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


def assert_remote_payload_allowlisted(payload: Any) -> None:
    """Fail if the payload uses keys or entity shapes outside the allowlist."""
    data = payload_as_dict(payload)
    extra_keys = set(data) - REMOTE_PAYLOAD_TOP_LEVEL_KEYS
    if extra_keys:
        raise PrivacyInvariantError(
            f"Remote payload contains non-allowlisted keys: {sorted(extra_keys)}"
        )

    entities = data.get("entities", [])
    if not isinstance(entities, list):
        raise PrivacyInvariantError("Remote payload 'entities' must be a list")
    for entity in entities:
        if not isinstance(entity, str) or not _PERSON_TOKEN_RE.fullmatch(entity):
            raise PrivacyInvariantError(
                f"Remote entity must be opaque {PERSON_PSEUDONYM_PREFIX}* token, got {entity!r}"
            )

    metadata = data.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise PrivacyInvariantError("Remote payload 'metadata' must be a mapping")
    bad_meta = set(metadata) - REMOTE_METADATA_KEYS
    if bad_meta:
        raise PrivacyInvariantError(
            f"Remote metadata contains non-allowlisted keys: {sorted(bad_meta)}"
        )

    if "may_transmit_remotely" in data and not isinstance(data["may_transmit_remotely"], bool):
        raise PrivacyInvariantError("'may_transmit_remotely' must be a bool")


def assert_no_private_person_fields(
    payload: Any,
    people: Sequence[PrivatePerson],
) -> None:
    """Fail if any raw ``PrivatePerson`` field value appears in the payload."""
    data = payload_as_dict(payload)
    blob = _serialised_blob(data)
    for person in people:
        for secret in secrets_from_person(person):
            if secret in blob:
                raise PrivacyInvariantError(
                    f"Raw PrivatePerson field value leaked into remote payload: {secret!r}"
                )

    if _EMAIL_RE.search(blob):
        raise PrivacyInvariantError("Raw email address found in remote payload")
    if _PHONE_RE.search(blob):
        raise PrivacyInvariantError("Raw phone number found in remote payload")


def assert_notes_not_wholesale_remote_safe(
    payload: Any,
    note: PrivateNote,
    *,
    policy_exception: NotesRemotePolicyException | None = None,
) -> None:
    """Fail if a note is marked remote-safe without a passage-only policy exception.

    Wholesale bodies are **never** remote-safe — even with
    :class:`NotesRemotePolicyException` (passage-only by construction).
    """
    data = payload_as_dict(payload)
    if not data.get("may_transmit_remotely"):
        return

    meta = data.get("metadata") or {}
    source = meta.get("source_type") if isinstance(meta, Mapping) else None
    record_id = meta.get("record_id") if isinstance(meta, Mapping) else None
    is_this_note = source == SourceType.NOTE.value or record_id == note.id
    summary = data.get("summary")
    summary_text = summary if isinstance(summary, str) else ""

    if not is_this_note and note.body_text.strip() and note.body_text not in _serialised_blob(
        data
    ):
        return

    if default_level_for_source(SourceType.NOTE) is not PrivacyLevel.HIGH:
        raise PrivacyInvariantError("Notes must default to HIGH privacy")

    matching_exc = (
        policy_exception
        if policy_exception is not None and policy_exception.note_id == note.id
        else None
    )
    if matching_exc is None:
        raise PrivacyInvariantError(
            "Note cannot be marked remote-safe without an explicit "
            "NotesRemotePolicyException"
        )

    wholesale_flag = isinstance(meta, Mapping) and meta.get("wholesale_body_included") is True
    if wholesale_flag or not wholesale_note_body_remote_safe(
        body_text=note.body_text,
        candidate_text=summary_text,
        exception=matching_exc,
    ):
        if wholesale_flag or note.body_text.strip() in _serialised_blob(data):
            raise PrivacyInvariantError(
                "Wholesale note body cannot be marked remote-safe "
                "(NotesRemotePolicyException is passage-only)"
            )


def assert_high_privacy_not_remote(
    payload: Any,
    *,
    source_type: SourceType | str | None = None,
    policy_exception: NotesRemotePolicyException | None = None,
) -> None:
    """Fail when HIGH / VERY_HIGH sources claim remote transmission without exception."""
    data = payload_as_dict(payload)
    if not data.get("may_transmit_remotely"):
        return

    meta = data.get("metadata") or {}
    raw_source = source_type or (meta.get("source_type") if isinstance(meta, Mapping) else None)
    if raw_source is None:
        return
    source = SourceType(raw_source) if not isinstance(raw_source, SourceType) else raw_source
    level = default_level_for_source(source)
    if level not in {PrivacyLevel.HIGH, PrivacyLevel.VERY_HIGH}:
        return

    if source == SourceType.NOTE:
        note_id = meta.get("record_id") if isinstance(meta, Mapping) else None
        if (
            policy_exception is not None
            and isinstance(note_id, str)
            and policy_exception.note_id == note_id
        ):
            return
    raise PrivacyInvariantError(
        f"Source {source.value} defaults to {level.value} and cannot set "
        "may_transmit_remotely without an explicit NotesRemotePolicyException"
    )


def assert_remote_payload_safe(
    payload: Any,
    *,
    people: Sequence[PrivatePerson] = (),
    notes: Sequence[PrivateNote] = (),
    policy_exception: NotesRemotePolicyException | None = None,
    remote: RemoteInferenceConfig | None = None,
) -> None:
    """Full gate: allowlist + PrivatePerson leakage + Notes policy + remote switch.

    When ``remote.enabled`` is False, payloads with ``may_transmit_remotely=True``
    still must be structurally safe (allowlist / no PII), but
    :func:`~personal_enigma.privacy.remote.may_send_remotely` remains False so
    Apple-local pipelines can run without hosted transmission.
    """
    data = payload_as_dict(payload)
    assert_remote_payload_allowlisted(data)

    if data.get("may_transmit_remotely"):
        assert_no_private_person_fields(data, people)
        assert_high_privacy_not_remote(data, policy_exception=policy_exception)
        for note in notes:
            assert_notes_not_wholesale_remote_safe(
                data, note, policy_exception=policy_exception
            )

    config = remote if remote is not None else RemoteInferenceConfig()
    if may_send_remotely(config, payload_allows_remote=bool(data.get("may_transmit_remotely"))):
        assert_no_private_person_fields(data, people)


def assert_transformed_corpus_safe(
    payloads: Iterable[Any],
    *,
    people: Sequence[PrivatePerson] = (),
    notes: Sequence[PrivateNote] = (),
    policy_exception: NotesRemotePolicyException | None = None,
    remote: RemoteInferenceConfig | None = None,
) -> None:
    """Run :func:`assert_remote_payload_safe` over a transformed fixture corpus."""
    for payload in payloads:
        assert_remote_payload_safe(
            payload,
            people=people,
            notes=notes,
            policy_exception=policy_exception,
            remote=remote,
        )
