# ADR-041: My Enigma calendar READ authority ceiling

## Status

Accepted (P03)

## Context

P03 connects the first real private source — calendar — to My Enigma. The pilot must answer schedule questions without gaining write authority or leaking raw attendee data to hosted models.

## Decision

1. **My Enigma calendar conversation uses a separate tool surface** from Alex Lab demo tools. Allowed: `agenda.get`, `availability.check`, `attention.get_current`, `world.explain`. Denied: `assist.*`, `source.*`, attestation writes, Gmail.

2. **Events are stored under the private world root** at `calendar/events.json`. Ingestion adapters (M08/M12) sync into this store; Alex Lab never reads it.

3. **Reduced calendar facts** (title, time window, id) may reach reasoning. Descriptions and attendee emails stay local unless a future ticket explicitly earns narrower egress.

4. **Calendar holds are not bookings.** Availability/agenda copy must not confirm reservations.

5. **World switch clears** private conversation and last calendar provenance (ADR-040).

## Consequences

- `ENIGMA_CALENDAR_FIXTURE` env selects a deterministic fixture adapter for CI without bridge credentials.
- Real adapter hookup reuses existing M08/M12 ingestion into the private store; P03 does not add calendar writes.

## Related

- [ADR-040](./040-product-worlds-same-enigma.md) · [ADR-005](./005-demo-private-storage-roots.md)
- Ticket: [P03](../../tickets/pilot/P03-calendar-read-support.md) — P03a [#109](https://github.com/oscarhilton/enigma-assistant-/pull/109); live ingress [P03b](../../tickets/pilot/P03b-live-calendar-ingress.md)
- `ENIGMA_CALENDAR_FIXTURE` is a CI override. Production reads `StoreCalendarAdapter` from the private-root store when the env is unset.
