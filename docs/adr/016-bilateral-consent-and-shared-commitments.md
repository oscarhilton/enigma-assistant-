# ADR-016: Bilateral consent and shared commitments

## Status

Accepted

## Date

2026-08-17

## Context

A remote `PROPOSE` must not become a confirmed commitment in the recipient's world merely because it arrived on the wire. That would bypass human agency, Assist approval ([ADR-019](./019-delegated-authority-and-execution-ladder.md)), and local policy. Open-loop facts in memory are orthogonal to attention surface ([open-loop-commitments.md](../architecture/open-loop-commitments.md)); **shared commitments** are a distinct coordination concept for **agreed public facts between participants**, not private obligation inference.

Protocol envelopes define transport ([ADR-014](./014-minimal-semantic-envelope-protocol.md)); this ADR defines the **consent and commitment lifecycle**.

## Decision

### Flow

```text
Person A states intent (natural language, local)
    ↓
Enigma A reasons privately → draft proposal
    ↓
Person A approves sending
    ↓
Enigma A emits signed PROPOSE envelope
    ↓
Enigma B receives as external evidence (untrusted)
    ↓
Enigma B evaluates locally → presents to Person B
    ↓
Person B accepts / declines / counters
    ↓
Only ACCEPT (or equivalent bilateral COMMIT) establishes SharedCommitment
```

A proposal **never** becomes confirmed commitment solely because another Enigma sent it.

### Domain concepts (coordination layer)

| Concept | Meaning |
| --- | --- |
| `Proposal` | Local draft or received external offer; not yet shared commitment |
| `Consent` | Explicit human (or delegated-authority) approval to send or accept |
| `Counterproposal` | DECLINE + alternate terms as new PROPOSE chain |
| `SharedCommitment` | Agreed public facts both sides recognise |
| `CommitmentVersion` | Monotonic version on material term changes |
| `Participant` | Cryptographic identity refs + local display mapping |
| `SharedCommitmentState` | Lifecycle: proposed → active → completed / cancelled |

### SharedCommitment contents (public facts only)

- Shared id (correlation across Enigmas)
- Participants
- Subject / capability (e.g. `schedule.event.propose`)
- Agreed terms (typed payload — time window, location label, task title)
- Status and version
- Timestamps

Each Enigma maintains its **own private interpretation** (calendar hold, reminder, obligation link, attention implications). SharedCommitment does not replace local `Obligation` records.

### Modification rule

Material changes are **new proposals**. No remote direct mutation of another Enigma's private state or of an existing SharedCommitment without bilateral accept of the new version ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)).

## Consequences

- Dinner proof: Oscar's Enigma proposes; Tobi's Enigma shows structured preview; calendar blocks update only after Tobi accepts ([CO01](../../tickets/coordination/CO01-dinner-proposal-proof.md)).
- Independently signed PROPOSE / ACCEPT records are the future basis for portable shared-commitment proof without trusting the relay database ([ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)).
- `UPDATE` / `CANCEL` on wire are notifications tied to commitment ids; local world updates follow verification ([ADR-019](./019-delegated-authority-and-execution-ladder.md)).
- Demo scenarios may stub SharedCommitment in fixtures without implying Private DB writes.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Auto-accept from trusted contacts | Trust ≠ consent; fails org and B2B cases. |
| Single-writer shared document | Remote mutation of local state; no bilateral audit. |
| Treat PROPOSE as committed in sender's calendar only | Asymmetric truth; breaks coordination semantics. |
| Fold into generic Obligation model | Conflates inferred open loops with explicitly agreed cross-party facts. |

## References

- [ADR-013](./013-inter-enigma-coordination-trust-boundary.md) · [ADR-014](./014-minimal-semantic-envelope-protocol.md) · [ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) · [ADR-019](./019-delegated-authority-and-execution-ladder.md)
- [open-loop-commitments.md](../architecture/open-loop-commitments.md)
- [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
