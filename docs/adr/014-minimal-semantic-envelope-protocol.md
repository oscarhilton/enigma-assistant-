# ADR-014: Minimal semantic envelope protocol

## Status

Accepted

## Date

2026-08-17

## Context

Inter-Enigma coordination needs a **small, stable transport vocabulary** so domain workflows do not invent bespoke wire formats per product feature. The trust boundary ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)) requires that only structured protocol data crosses it; domain semantics must be versioned separately from transport verbs.

## Decision

### Generic coordination verbs

Keep the protocol verb set small and generic:

| Verb | Role |
| --- | --- |
| `ASK` | Request information within a granted capability |
| `PROPOSE` | Offer terms for bilateral agreement |
| `ACCEPT` | Accept a proposal (establishes or advances shared commitment) |
| `DECLINE` | Reject a proposal without counter terms |
| `COUNTER` | Reject with alternate terms (new proposal thread) |
| `COMMIT` | Affirm an agreed shared commitment state |
| `UPDATE` | Notify of a change to agreed public facts (via new proposal if material) |
| `COMPLETE` | Mark shared work or event as done |
| `CANCEL` | Withdraw or void a prior proposal or commitment |
| `ATTEST` | Signed statement of a public fact (e.g. fulfilment status) |

Domain behaviour lives in **versioned capability schemas**, not in new transport verbs per workflow.

### Canonical envelope

Every cross-boundary message uses a canonical envelope:

```text
protocol_version
sender            # cryptographic identity ref — not display name
recipient
message_id
correlation_id    # ties ASK/response, PROPOSE/ACCEPT chains
conversation_id
issued_at
expires_at
nonce
capability        # e.g. schedule.event.propose@v1
typed_payload     # schema-validated for capability
signature
```

Signing, encryption, and relay routing are specified in [ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md).

### Example capabilities (illustrative, not exhaustive)

| Capability | Typical verb |
| --- | --- |
| `schedule.event.propose` | PROPOSE / ACCEPT / COUNTER |
| `availability.query` | ASK |
| `shared_task.propose` | PROPOSE / ACCEPT / COMPLETE |
| `dependency.complete` | ATTEST / UPDATE |
| `supplier.fulfilment.query` | ASK |

The dinner proof case ([CO01](../../tickets/coordination/CO01-dinner-proposal-proof.md)) uses `schedule.event.propose` only; do not build a large capability catalogue up front.

### Design rules

- Do **not** create bespoke transport semantics per product workflow (e.g. no separate `DINNER_INVITE` wire type).
- Payload schemas are versioned (`capability@vN`); breaking changes increment version.
- Envelope fields are required for replay protection and audit ([ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md), [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)).

## Consequences

- A future `packages/coordination` (or equivalent) owns envelope validation and capability registry — not yet claimed; see [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md).
- Product features map to capability + verb combinations; conversational Assist prepares human-readable previews of typed payloads before send ([ADR-019](./019-delegated-authority-and-execution-ladder.md)).
- Relay services route opaque signed envelopes; they do not parse domain payloads beyond capability metadata where needed for policy.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Per-feature REST APIs between Enigmas | Encourages wide data endpoints; harder to enforce minimal disclosure. |
| Rich semantic ontology on the wire | Couples transport to domain evolution; violates "small generic vocabulary." |
| JSON blobs with ad-hoc `type` strings | No versioned capability contract; ambiguous validation and consent scope. |
| NATS / custom RPC per workflow | Same bespoke-transport problem at a different layer. |

## References

- [ADR-013](./013-inter-enigma-coordination-trust-boundary.md) · [ADR-016](./016-bilateral-consent-and-shared-commitments.md)
- [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
