# ADR-013: Inter-Enigma coordination trust boundary

## Status

Accepted

## Date

2026-08-17

## Context

Enigma today reasons over a single user's private world model inside one trust boundary. Product scenarios — social plans, shared tasks, supplier fulfilment, appointment rescheduling — require **two or more Enigmas** (across users or organisations) to coordinate without treating a remote installation as trusted infrastructure or as an extension of local memory.

The governing product rule remains: Apple services enrich Enigma's private model of the user's world; they do not enlarge the remote model's view of it. **Select first → transform second → transmit last** ([privacy-model.md](../architecture/privacy-model.md)). Coordination must not punch holes in storage separation ([ADR-005](./005-demo-private-storage-roots.md), [ADR-008](./008-shadow-storage-roots.md)), Notes handling ([ADR-004](./004-notes-best-effort-no-sqlite.md)), or identity tokenisation (`packages/identity`).

Remote LLM providers are already untrusted for raw private context. A peer Enigma is a different class of untrusted party: it may be well-intentioned but must never receive wholesale world-model access.

## Decision

1. **Enigmas may coordinate across users and organisations.** Coordination is a first-class architectural concern, not an ad-hoc messaging feature.
2. **Private world models never cross the trust boundary.** Calendar rows, inbox threads, Notes bodies, embeddings indexes, obligation graphs, and reasoning traces stay local.
3. **Remote Enigmas are untrusted peers.** Incoming protocol messages are **evidence**, not truth. Each Enigma evaluates claims against local policy and private state.
4. **Cross-boundary communication is typed, minimal, explicit protocol data only.** No free-form LLM ↔ LLM conversation across the boundary.
5. **Core rule:** Natural language and rich context stay **inside** the trust boundary. Structured protocol messages cross it.
6. **Principle:** LLMs reason privately; protocols communicate deterministically.
7. **Crypto vs protocol:** Cryptography authenticates and conceals envelopes ([ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)); the protocol defines meaning, capability, consent, and cumulative privacy ([ADR-014](./014-minimal-semantic-envelope-protocol.md)–[ADR-016](./016-bilateral-consent-and-shared-commitments.md), [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md), [ADR-019](./019-delegated-authority-and-execution-ladder.md)).

### Rejects (non-negotiable)

- Sharing inbox, calendar, memory, or world-model context with a remote Enigma.
- Sending raw model context windows or chain-of-thought across the boundary.
- Remote mutation of another Enigma's private state.
- Treating a relay, directory, or hosted coordination service as trusted for private data.

## Consequences

- Every cross-boundary feature must be expressible as capability-scoped protocol envelopes ([ADR-014](./014-minimal-semantic-envelope-protocol.md), [ADR-015](./015-capability-scoped-disclosure-not-data-access.md)).
- Assist and conversational UI remain inside the boundary; they prepare proposals for human approval before anything crosses it ([ADR-019](./019-delegated-authority-and-execution-ladder.md), [conversational-ui.md](../architecture/conversational-ui.md)).
- Demo Mode coordination proofs must use Demo storage roots and fictional identities only — never Private keys or PERSON_* namespaces ([ADR-005](./005-demo-private-storage-roots.md)).
- Implementation is deferred; this ADR defines the boundary programme tickets must respect.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Federated shared database or replicated world model | Violates private-by-default; remote peer becomes implicit reader of all synced facts. |
| LLM-to-LLM negotiation channel | Unbounded disclosure risk; non-deterministic commitments; no auditable consent. |
| OAuth-style "grant Tobi read access to Oscar's calendar" | Capability becomes data access; fails cumulative inference attacks ([ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)). |
| Trust remote Enigma because same organisation | Organisation boundary ≠ user consent; insider relay still must not see private stores. |

## References

- Programme overview: [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
- Envelope crypto vs protocol meaning: [ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)
- Tickets: [tickets/coordination/](../../tickets/coordination/)
- Shareable recipes may later include `propose.shared_event`; capability/consent protocol still governs ([ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md) — parked)
