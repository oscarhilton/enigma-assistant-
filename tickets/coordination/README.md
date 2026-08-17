# Enigma coordination programme (CO00–CO01+)

**Status:** ADR programme landed — implementation not started  
**North star:** Reason privately. Communicate minimally. Commit explicitly.

## Architectural rules (from ADR-013)

1. Private world models **never** cross the trust boundary.
2. Remote Enigmas are **untrusted peers**; incoming messages are evidence.
3. Natural language stays **inside**; structured signed envelopes cross **outside**.
4. Capability grants are **questions**, not data access ([ADR-015](../../docs/adr/015-capability-scoped-disclosure-not-data-access.md)).
5. Shared commitments require **bilateral consent** ([ADR-016](../../docs/adr/016-bilateral-consent-and-shared-commitments.md)).
6. Cryptography protects envelopes; the protocol protects meaning, authority, and consent. Encryption is not privacy ([ADR-017](../../docs/adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)).

## ADR sequence

| ADR | Title | Status |
| --- | --- | --- |
| [013](../../docs/adr/013-inter-enigma-coordination-trust-boundary.md) | Inter-Enigma coordination trust boundary | Accepted |
| [014](../../docs/adr/014-minimal-semantic-envelope-protocol.md) | Minimal semantic envelope protocol | Accepted |
| [015](../../docs/adr/015-capability-scoped-disclosure-not-data-access.md) | Capability-scoped disclosure | Accepted |
| [016](../../docs/adr/016-bilateral-consent-and-shared-commitments.md) | Bilateral consent and shared commitments | Accepted |
| [017](../../docs/adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) | Cryptographic identity and encrypted relay | Accepted |
| [018](../../docs/adr/018-disclosure-ledger-and-inference-attack-protection.md) | Disclosure ledger | Accepted |
| [019](../../docs/adr/019-delegated-authority-and-execution-ladder.md) | Delegated authority ladder (A0–A5) | Accepted |

## Tickets

| Ticket | Title | Status |
| --- | --- | --- |
| [CO00](./CO00-adr-programme.md) | ADR programme + architecture doc | done |
| [CO01](./CO01-dinner-proposal-proof.md) | Dinner proposal proof case | todo |

## Docs

- [docs/architecture/enigma-coordination-protocol.md](../../docs/architecture/enigma-coordination-protocol.md)
- Assist UI overlap: [C07](../conversational-ui/C07-assist-proposals.md) (A3/A4 surfaces)

## Claim order

1. **CO00** — complete (documentation only)
2. **CO01** — first implementation proof; hard-depends on CO00 + conversational shell (C02 ~ C07 soft)

Do not claim protocol/crypto/relay implementation without an explicit ticket.
