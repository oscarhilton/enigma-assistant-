# ADR-003: SourceType vs Provider separation

## Status

Accepted

## Context

Mixing “what” and “where” (e.g. `AppleCalendarEvent` as a core type) forces provider special-cases through the stack.

## Decision

- `SourceType` describes the kind of thing: email, calendar_event, reminder, note, contact.
- `Provider` describes origin: google, apple, local.
- Canonical models (`PrivateCalendarEvent`, etc.) are provider-tagged only at the edge; reasoning uses domain concepts (`CalendarEvent` / obligation / attention).

## Consequences

- New sources implement `DataSource` and map into existing canonical models.
- Deduplication and obligation merging stay provider-agnostic.
