# ADR-015: Capability-scoped disclosure, not data access

## Status

Accepted

## Date

2026-08-17

## Context

Cross-Enigma coordination fails if implemented as **shared data access** ("Tobi can read Oscar's calendar"). That model leaks by default, cannot answer narrowly scoped questions without over-disclosure, and ignores cumulative inference ([ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)). The trust boundary ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)) requires that remote peers receive permission to **ask specific questions**, evaluated locally against private state.

This extends the existing privacy pipeline — select, transform, transmit last — to **outbound answers** as well as inbound remote LLM context ([privacy-model.md](../architecture/privacy-model.md)).

## Decision

1. **Counterparties receive capability grants, not store access.** A grant authorises a bounded question shape within a scope and time window.
2. **Evaluate privately. Return the minimum useful answer.** The remote party never sees raw records; it sees a typed response valid for the capability schema.
3. **Default: deny** unless a capability explicitly permits the request.

### Anti-patterns vs correct model

| Bad | Good |
| --- | --- |
| "Tobi can access Oscar's calendar." | "Tobi may ask whether supplied windows are available (yes/no / coarse buckets)." |
| "Supplier can inspect our inventory." | "Supplier may ask whether quantity X can be fulfilled by date Y." |
| Return event titles and attendee lists for availability | Return `available: true` or coarse slot labels per policy |

### Capability policy dimensions

Each granted capability records at minimum:

| Dimension | Purpose |
| --- | --- |
| Caller identity / trust class | Who may invoke |
| Allowed question shape | Schema for ASK / PROPOSE payloads |
| Scope | Subjects, date ranges, project ids — minimal |
| Expiry | Time-bound grants |
| Rate limit / query budget | Anti-probing ([ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)) |
| Disclosure level | Coarse vs fine-grained answer classes |
| Approval policy | Human-in-the-loop before first use or each answer ([ADR-019](./019-delegated-authority-and-execution-ladder.md)) |

### Answer path

```text
signed ASK envelope
    ↓
verify identity + capability + ledger budget
    ↓
private evaluation (calendar, obligations, inventory — local only)
    ↓
minimum typed response
    ↓
sign + return
```

`PrivatePerson`, wholesale Notes, and raw provider objects never appear in responses ([ADR-004](./004-notes-best-effort-no-sqlite.md)).

## Consequences

- Calendar availability for the dinner proof returns structured availability facts, not ICS exports or event lists.
- Demo coordination uses fictional personas and Demo storage only ([ADR-005](./005-demo-private-storage-roots.md)).
- Disclosure ledger entries are mandatory for ASK handling ([ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)).
- UI must show what question will be asked and what disclosure class may result before send (Assist A3).

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Shared calendar feed / CalDAV between Enigmas | Data access model; reconstructs full schedule from deltas. |
| Encrypted blob of calendar export | Cryptographic privacy without semantic privacy ([ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)); still wholesale data transfer. |
| Remote SQL/query over anonymised replica | Replica drift and inference risk; violates "evaluate privately." |
| Trust-based "friends see everything" | No per-capability audit; fails B2B and org boundaries. |

## References

- [ADR-013](./013-inter-enigma-coordination-trust-boundary.md) · [ADR-014](./014-minimal-semantic-envelope-protocol.md) · [ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) · [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)
- [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
- [ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) — local recipes reuse capability grants, not store access; grants are per **version** and do not silently carry over (v1 `calendar.read` + `browser.open` ↛ v2 `email.send`). Recipe runtime is not authorised here.
