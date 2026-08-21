# ADR-018: Disclosure ledger and inference-attack protection

## Status

Accepted

## Date

2026-08-17

## Context

Capability-scoped ASK ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md)) prevents a single request from returning a full calendar export. It does **not** prevent **cumulative inference**: repeated narrow availability probes can reconstruct a schedule even when each probe is end-to-end encrypted ([ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)). Privacy must be evaluated **cumulatively per counterparty**, not per individual request. This aligns with select → transform → transmit last: outbound answers are disclosures subject to the same discipline as inbound remote LLM context ([privacy-model.md](../architecture/privacy-model.md)).

## Decision

### Core question

Before answering an ASK, Enigma must be able to answer: **"What has this counterparty already learned from me?"**

### Ledger record (per disclosure event)

Record at minimum:

| Field | Purpose |
| --- | --- |
| Requester identity | Cryptographic ref |
| Capability | e.g. `availability.query@v1` |
| Query fingerprint | Normalised payload hash or structured key |
| Answer / disclosure class | What was revealed (not necessarily raw text) |
| Timestamp | When answered |
| Cumulative query count | Per capability + requester window |
| Disclosure class | Coarse taxonomy for policy |
| Expiry / retention | When ledger row may be purged |
| Inferred exposure | Optional estimate of reconstructed information |

Ledger storage is local and private; it does not cross the trust boundary ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)).

### Policy responses

Enforcement may combine:

- Per-capability **rate limits** and **query budgets**
- **Trust tiers** (unknown vs org member vs prior commitment partner)
- **Coarse answers** (bucketed availability vs exact slots)
- **Response randomisation / aggregation** where appropriate (e.g. ±15 min buckets)
- **Refusal** after excessive probing
- **Contact / org policies** (block, require approval)
- **Spam / flooding rejection**

Default posture remains deny unless capability permits ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md)).

### Relation to Assist authority

Auto-answer within budget may run at **A5** for narrowly scoped capabilities; first contact or budget exhaustion escalates to **A4** explicit approval ([ADR-019](./019-delegated-authority-and-execution-ladder.md)).

## Consequences

- Availability for dinner proof must log probes; demo fixtures may include scripted ledger states.
- B2B fulfilment ASK capabilities need stricter budgets than social availability among mutual contacts.
- UI transparency: user can inspect "what we've told this party" from ledger views (future ticket).

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Per-request policy only | Misses reconstruction attacks. |
| Global rate limit by IP | Wrong granularity; ignores capability and trust class. |
| Always require human approval | Unusable for high-trust auto-availability; ladder handles middle ground. |
| Differential privacy on every answer | May be overkill for v1; coarse buckets + budgets suffice initially. |

## References

- [ADR-015](./015-capability-scoped-disclosure-not-data-access.md) · [ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) · [ADR-019](./019-delegated-authority-and-execution-ladder.md)
- [privacy-model.md](../architecture/privacy-model.md)
- [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
