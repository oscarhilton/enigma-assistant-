"""Map private domain records to sanitised ``TransformedContext``."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivatePersonRef,
    PrivateReminder,
    SourceType,
)
from personal_enigma.identity import EntityResolver
from personal_enigma.privacy.levels import PrivacyLevel, default_level_for_source
from personal_enigma.transformation.passages import extract_minimal_passage
from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.stub_resolver import StubHmacResolver

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"
)


class DefaultEnigmaTransformer:
    """Concrete Enigma transformer: select → transform; transmit stays opt-in."""

    def __init__(
        self,
        resolver: EntityResolver | None = None,
        *,
        hmac_key: bytes | str | None = None,
        allow_remote: bool = False,
    ) -> None:
        if resolver is not None:
            self._resolver: EntityResolver = resolver
        elif hmac_key is not None:
            self._resolver = StubHmacResolver(hmac_key)
        else:
            raise ValueError(
                "DefaultEnigmaTransformer requires an explicit hmac_key or resolver; "
                "refusing a shared default key that would correlate pseudonyms across users"
            )
        self._allow_remote = allow_remote

    def transform(self, private_record: dict[str, Any] | BaseModel) -> TransformedContext:
        record = self._coerce(private_record)
        if isinstance(record, PrivateCalendarEvent):
            return self._transform_calendar(record)
        if isinstance(record, PrivateReminder):
            return self._transform_reminder(record)
        if isinstance(record, PrivateNote):
            return self._transform_note(record)
        if isinstance(record, PrivatePerson):
            return self._transform_person(record)
        if isinstance(record, PrivateMessage):
            return self._transform_message(record)
        raise TypeError(f"Unsupported private record type: {type(record)!r}")

    def _coerce(self, private_record: dict[str, Any] | BaseModel) -> BaseModel:
        if isinstance(private_record, BaseModel):
            return private_record
        parsers: tuple[type[BaseModel], ...] = (
            PrivateCalendarEvent,
            PrivateReminder,
            PrivateNote,
            PrivateMessage,
            PrivatePerson,
        )
        for model in parsers:
            try:
                return model.model_validate(private_record)
            except ValidationError:
                continue
        raise ValueError("private_record does not match a known domain model")

    def _may_transmit(self, source: SourceType) -> bool:
        if not self._allow_remote:
            return False
        level = default_level_for_source(source)
        return level not in {PrivacyLevel.HIGH, PrivacyLevel.VERY_HIGH}

    def _resolve_refs(self, refs: list[PrivatePersonRef]) -> list[str]:
        entities: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            pseudo = self._resolver.resolve_ref(ref)
            if pseudo is None:
                continue
            value = str(pseudo)
            if value not in seen:
                seen.add(value)
                entities.append(value)
        return entities

    def _sanitise_text(self, text: str | None, entities: list[str]) -> str | None:
        if text is None:
            return None

        def replace_email(match: re.Match[str]) -> str:
            email = match.group(0)
            pseudo = self._resolver.resolve_ref(PrivatePersonRef(email=email))
            if pseudo is None:
                return "[REDACTED_EMAIL]"
            value = str(pseudo)
            if value not in entities:
                entities.append(value)
            return value

        def replace_phone(match: re.Match[str]) -> str:
            phone = match.group(0)
            pseudo = self._resolver.resolve_ref(PrivatePersonRef(provider_id=f"phone:{phone}"))
            if pseudo is None:
                return "[REDACTED_PHONE]"
            value = str(pseudo)
            if value not in entities:
                entities.append(value)
            return value

        scrubbed = _EMAIL_RE.sub(replace_email, text)
        scrubbed = _PHONE_RE.sub(replace_phone, scrubbed)
        return scrubbed

    def _transform_calendar(self, event: PrivateCalendarEvent) -> TransformedContext:
        entities = self._resolve_refs(
            ([event.organiser] if event.organiser else []) + list(event.attendees)
        )
        title = self._sanitise_text(event.title, entities) or ""
        description = self._sanitise_text(event.description, entities)
        location = self._sanitise_text(event.location, entities)
        parts = [f"Calendar: {title}"]
        parts.append(f"{_fmt_dt(event.start_at)} → {_fmt_dt(event.end_at)}")
        if location:
            parts.append(f"at {location}")
        if description:
            parts.append(description)
        if entities:
            parts.append(f"people: {', '.join(entities)}")
        return TransformedContext(
            summary=" | ".join(parts),
            entities=entities,
            metadata={
                "source_type": SourceType.CALENDAR_EVENT.value,
                "record_id": event.id,
                "provider": event.provider,
                "all_day": event.all_day,
            },
            may_transmit_remotely=self._may_transmit(SourceType.CALENDAR_EVENT),
        )

    def _transform_reminder(self, reminder: PrivateReminder) -> TransformedContext:
        entities: list[str] = []
        title = self._sanitise_text(reminder.title, entities) or ""
        notes = self._sanitise_text(reminder.notes, entities)
        parts = [f"Reminder: {title}"]
        if reminder.due_at is not None:
            parts.append(f"due {_fmt_dt(reminder.due_at)}")
        if notes:
            parts.append(notes)
        return TransformedContext(
            summary=" | ".join(parts),
            entities=entities,
            metadata={
                "source_type": SourceType.REMINDER.value,
                "record_id": reminder.id,
                "provider": reminder.provider,
                "is_completed": reminder.is_completed,
            },
            may_transmit_remotely=self._may_transmit(SourceType.REMINDER),
        )

    def _transform_note(self, note: PrivateNote) -> TransformedContext:
        entities: list[str] = []
        title = self._sanitise_text(note.title, entities) or ""
        passage = extract_minimal_passage(note.body_text)
        passage = self._sanitise_text(passage, entities) or ""
        wholesale = note.body_text.strip()
        # Never mark Notes remote-safe by default; HIGH privacy forbids remote even if
        # allow_remote is set. Passage is selected content only — not a remote green light.
        return TransformedContext(
            summary=f"Note: {title} | {passage}" if passage else f"Note: {title}",
            entities=entities,
            metadata={
                "source_type": SourceType.NOTE.value,
                "record_id": note.id,
                "provider": note.provider,
                "passage_chars": len(passage),
                "body_chars": len(wholesale),
                "wholesale_body_included": False,
            },
            may_transmit_remotely=False,
        )

    def _transform_person(self, person: PrivatePerson) -> TransformedContext:
        pseudo = str(self._resolver.resolve_person(person))
        return TransformedContext(
            summary=f"Contact: {pseudo}",
            entities=[pseudo],
            metadata={
                "source_type": SourceType.CONTACT.value,
                "record_id": str(person.id),
            },
            may_transmit_remotely=False,
        )

    def _transform_message(self, message: PrivateMessage) -> TransformedContext:
        refs = (
            ([message.from_person] if message.from_person else [])
            + list(message.to)
            + list(message.cc)
        )
        entities = self._resolve_refs(refs)
        subject = self._sanitise_text(message.subject, entities)
        snippet = self._sanitise_text(message.snippet, entities)
        # Prefer snippet over body — never ship full body as the default summary.
        body_passage = None
        if message.body_text:
            body_passage = self._sanitise_text(
                extract_minimal_passage(message.body_text),
                entities,
            )
        content = snippet or body_passage
        parts = ["Email"]
        if subject:
            parts.append(subject)
        if content:
            parts.append(content)
        if entities:
            parts.append(f"people: {', '.join(entities)}")
        return TransformedContext(
            summary=" | ".join(parts),
            entities=entities,
            metadata={
                "source_type": SourceType.EMAIL.value,
                "record_id": message.id,
                "provider": message.provider,
                "wholesale_body_included": False,
            },
            may_transmit_remotely=self._may_transmit(SourceType.EMAIL),
        )


def _fmt_dt(value: datetime) -> str:
    return value.isoformat()
