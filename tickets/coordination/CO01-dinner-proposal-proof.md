# CO01 — Dinner proposal proof case

**Status:** todo  
**Branch:** `ticket/CO01-dinner-proposal-proof`  
**Domain:** coordination  
**Package boundary:** TBD when claimed — expect `packages/coordination/**` (new), `packages/fixtures/**` (demo identities), `apps/api/**` (demo coordination routes), `apps/web/src/enigma/**` (Assist preview for PROPOSE/ACCEPT). Exact globs to be pinned at claim time per [tickets/README.md](../README.md).

## Goal

First **end-to-end proof** that two Enigmas can coordinate a social dinner proposal using the architecture in ADRs 013–019 without exporting private world models.

**Capability:** `schedule.event.propose@v1`  
**Scenario:** Oscar proposes dinner with Tobi; Tobi accepts or counters.

## Hard depends

- [CO00](./CO00-adr-programme.md) — ADR programme (`done`)

## Soft depends (~)

- [C02](../conversational-ui/C02-enigma-client.md) — EnigmaClient types
- [C07](../conversational-ui/C07-assist-proposals.md) — Assist proposal / approve UI (A3/A4)

## Non-goals

- Production relay or real crypto infrastructure (may use fixture keys)
- Additional capabilities beyond `schedule.event.propose` and optional `availability.query`
- Private Mode or cross-environment storage sharing
- LLM-generated wire payloads

## Acceptance criteria

- [ ] Two Demo fixture identities exchange PROPOSE and ACCEPT envelopes with all canonical fields ([ADR-014](../../docs/adr/014-minimal-semantic-envelope-protocol.md))
- [ ] Wire capture / test asserts **no** calendar rows, mail, Notes, or `PrivatePerson` fields in payloads
- [ ] Sender world state does **not** treat dinner as shared commitment until recipient ACCEPT ([ADR-016](../../docs/adr/016-bilateral-consent-and-shared-commitments.md))
- [ ] Assist structured preview shown before send (A3) and before accept (A4) ([ADR-019](../../docs/adr/019-delegated-authority-and-execution-ladder.md))
- [ ] If availability ASK used: disclosure ledger row written ([ADR-018](../../docs/adr/018-disclosure-ledger-and-inference-attack-protection.md))
- [ ] Demo storage roots only ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))

## Test plan

- Unit: envelope schema validation, consent state machine
- Integration: two-identity Demo flow with fixture relay (in-process)
- Regression: snapshot of wire payloads for privacy assertions

## Privacy constraints

- Demo identities and keys under Demo root only
- No hosted model receives coordination payloads or private calendar exports
- Display names local; cryptographic refs on wire ([ADR-017](../../docs/adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md))

## References

- [enigma-coordination-protocol.md](../../docs/architecture/enigma-coordination-protocol.md) — dinner proof section
