# ADR-003: SourceType vs Provider separation

## Status

Accepted

## Context

Mixing “what” and “where” (e.g. `AppleCalendarEvent` as a core type) forces provider special-cases through the stack.

## Decision

- `SourceType` describes the kind of thing: email, calendar_event, reminder, note, contact, chat_message.
- `Provider` describes origin: google, apple, local, whatsapp.
- Canonical models (`PrivateCalendarEvent`, `PrivateChatMessage`, etc.) are provider-tagged only at the edge; reasoning uses domain concepts (`CalendarEvent` / obligation / attention).

Chat messages (synthetic WhatsApp first) are a **source type**, not a mail subtype. `PrivateMessage` remains Gmail-shaped; `PrivateChatMessage` is the canonical chat record. Raw chat is PRIVATE_RAW / VERY_HIGH and is never the world model.

## Consequences

- New sources implement `DataSource` and map into existing canonical models.
- Deduplication and obligation merging stay provider-agnostic.
