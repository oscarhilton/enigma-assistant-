# Enigma coordination protocol

**Status:** Architecture programme (ADRs 013–019) — no protocol implementation yet  
**Date:** 2026-08-17  
**Related:** [north-star.md](./north-star.md) (squeeze 7 — answers, not state) · [privacy-model.md](./privacy-model.md) · [conversational-ui.md](./conversational-ui.md) · [open-loop-commitments.md](./open-loop-commitments.md) · [shareable-recipes.md](./shareable-recipes.md) (parked; a recipe may later include `propose.shared_event` — protocol still governs)  
**ADRs:** [013](../adr/013-inter-enigma-coordination-trust-boundary.md) · [014](../adr/014-minimal-semantic-envelope-protocol.md) · [015](../adr/015-capability-scoped-disclosure-not-data-access.md) · [016](../adr/016-bilateral-consent-and-shared-commitments.md) · [017](../adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) · [018](../adr/018-disclosure-ledger-and-inference-attack-protection.md) · [019](../adr/019-delegated-authority-and-execution-ladder.md)  
**Tickets:** [tickets/coordination/](../../tickets/coordination/)

## Programme thesis

Enigma coordinates with other Enigmas **without exporting private world models**. Consumer social planning and B2B supplier fulfilment are **deployments of the same three-layer architecture**, not separate products.

```text
┌─────────────────────────────────────────────────────────────┐
│  PRIVATE AGENT LAYER                                        │
│  Natural language · local reasoning · Assist · approval     │
│  World model · obligations · attention · disclosure policy  │
└───────────────────────────┬─────────────────────────────────┘
                            │ typed signed envelopes only
┌───────────────────────────▼─────────────────────────────────┐
│  TRUST PROTOCOL LAYER                                       │
│  Identity · capabilities · bilateral consent · ledger       │
│  Minimal verbs · versioned payloads · encrypted relay       │
└───────────────────────────┬─────────────────────────────────┘
                            │ verified execution requests
┌───────────────────────────▼─────────────────────────────────┐
│  EXECUTION LAYER                                            │
│  PROPOSED → APPROVED → EXECUTING → VERIFIED               │
│  Calendar holds · shared tasks · attestations               │
└─────────────────────────────────────────────────────────────┘
```

### Technical creed

1. **Reason privately. Communicate minimally. Commit explicitly.**
2. **Natural language inside the trust boundary. Structured protocols across it.**
3. **LLMs reason privately; protocols communicate deterministically.**
4. **Select first → transform second → transmit last** — applies to outbound disclosures as well as inbound remote LLM context ([privacy-model.md](./privacy-model.md)).
5. **Apple services enrich Enigma's private model; they do not enlarge the remote model's view of it** ([AGENTS.md](../../AGENTS.md)).
6. **Cryptography protects envelopes; the protocol protects meaning, authority, and consent** ([ADR-017](../adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)).

Incoming protocol messages are **evidence**, not truth. Shared facts exist only after **bilateral consent** ([ADR-016](../adr/016-bilateral-consent-and-shared-commitments.md)).

## Cryptographic layer and privacy stack

Enigma adopts the public-key identity, recipient encryption and message-signing properties associated with PGP/OpenPGP, but does **not** adopt PGP's user-facing key-management model or treat OpenPGP as the coordination protocol ([ADR-017](../adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md)).

```text
PGP-ish crypto  →  protects the envelope
Enigma protocol →  defines meaning + authority + consent
```

Envelope path (PGP-shaped, implementation not frozen):

```text
sender private key → sign protocol envelope → encrypt to recipient public key
    → opaque relay → decrypt → recipient verifies signature
```

Encryption alone is not privacy. Repeated encrypted availability probes still reconstruct a calendar.

| Layer | Question | ADR |
| --- | --- | --- |
| **Cryptographic privacy** | Who can read this? | [017](../adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) |
| **Semantic privacy** | What are they allowed to ask? | [015](../adr/015-capability-scoped-disclosure-not-data-access.md) |
| **Inference privacy** | What can they learn cumulatively? | [018](../adr/018-disclosure-ledger-and-inference-attack-protection.md) |
| **Consent** | What are they allowed to cause? | [016](../adr/016-bilateral-consent-and-shared-commitments.md), [019](../adr/019-delegated-authority-and-execution-ladder.md) |

Product UX is invisible crypto (verified contact, active devices) — not fingerprints, armored key blocks, or key-server ceremonies. Long-lived identity keys authorise device keys; devices sign envelopes. Signed PROPOSE / ACCEPT records are a future portable-proof property; they do not require a blockchain.

**Core insight:** PGP can prove who said something and keep others from reading it. Enigma still has to decide what they're allowed to say, learn and cause.

## End-to-end flow

```text
Person A — natural-language intent ("Propose dinner with Tobi Thursday")
    ↓
Enigma A — private reasoning (calendar, preferences, relationships)
    ↓
Assist — structured proposal preview (capability + typed payload)
    ↓
Person A — approval (A3 send)
    ↓
Enigma A — capability-scoped signed envelope (PROPOSE)
    ↓
Encrypted relay — routes ciphertext; no private world data
    ↓
Enigma B — verify signature, identity, expiry, ledger budget
    ↓
Enigma B — local policy + private evaluation
    ↓
Person B — accept / decline / counter (A4 for accept)
    ↓
SharedCommitment — agreed public facts only
    ↓
Each Enigma — updates **own** private world (hold, reminder, obligation link)
```

No step exports inbox, calendar rows, Notes, embeddings, or model context windows to the peer.

## ADR sequence (read in order)

| ADR | Title |
| --- | --- |
| [013](../adr/013-inter-enigma-coordination-trust-boundary.md) | Inter-Enigma coordination trust boundary |
| [014](../adr/014-minimal-semantic-envelope-protocol.md) | Minimal semantic envelope protocol |
| [015](../adr/015-capability-scoped-disclosure-not-data-access.md) | Capability-scoped disclosure, not data access |
| [016](../adr/016-bilateral-consent-and-shared-commitments.md) | Bilateral consent and shared commitments |
| [017](../adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) | Cryptographic identity, signed envelopes, encrypted relay |
| [018](../adr/018-disclosure-ledger-and-inference-attack-protection.md) | Disclosure ledger and inference-attack protection |
| [019](../adr/019-delegated-authority-and-execution-ladder.md) | Delegated authority and execution ladder |

## First proof case: dinner proposal

**Scenario:** Oscar asks Enigma to propose dinner with Tobi on a specific evening.

**Capability:** `schedule.event.propose@v1`  
**Verbs:** `PROPOSE` → `ACCEPT` | `DECLINE` | `COUNTER`

**Oscar side (sender)**

1. Natural-language intent stays local.
2. Enigma drafts typed payload: proposed window, coarse location label, optional note (no calendar export).
3. Assist shows preview; Oscar approves at A3.
4. Signed envelope sent; Oscar's calendar **may** show tentative hold locally only after APPROVED — not committed shared fact until Tobi accepts.

**Tobi side (recipient)**

1. Enigma verifies envelope; treats payload as external evidence.
2. Assist shows structured preview (not Oscar's calendar).
3. Optional: Enigma runs private availability check; does **not** send Tobi's calendar back.
4. Tobi accepts (A4) → `ACCEPT` envelope → `SharedCommitment` active on both sides.
5. Each Enigma writes local calendar event from agreed public terms.

### Acceptance criteria ([CO01](../../tickets/coordination/CO01-dinner-proposal-proof.md))

- [ ] Demo or integration test with two fixture Enigma identities (Demo storage only)
- [ ] PROPOSE / ACCEPT exchange using canonical envelope fields ([ADR-014](../adr/014-minimal-semantic-envelope-protocol.md))
- [ ] No private store fields in wire payloads or relay logs
- [ ] Sender cannot mark commitment confirmed without recipient ACCEPT
- [ ] Assist preview before send (A3) and before accept (A4)
- [ ] Disclosure ledger entry if availability ASK used during negotiation

## Follow-on scenarios (architecture only — not v1 implementation)

| Scenario | Capability sketch | Notes |
| --- | --- | --- |
| Availability query | `availability.query` | ASK + coarse answer; ledger critical |
| Shared task | `shared_task.propose` | PROPOSE / COMPLETE |
| Dependency handoff | `dependency.complete` | ATTEST from upstream |
| Appointment reschedule | `schedule.event.propose` | COUNTER chain |
| B2B fulfilment | `supplier.fulfilment.query` | Strict budgets; org trust tier |
| Approval workflow | `approval.request` | A4 gate on commit |
| Attestation | `*.attest` | Signed public fact |

Do not implement a large capability catalogue until dinner proof passes.

## Assist authority (A0–A5)

Canonical ladder: [ADR-019](../adr/019-delegated-authority-and-execution-ladder.md). Conversational Assist ([C07](../../tickets/conversational-ui/C07-assist-proposals.md)) is the primary UI for A3/A4 coordination actions.

## Privacy and storage alignment

| Invariant | Source |
| --- | --- |
| Demo coordination uses Demo roots only | [ADR-005](../adr/005-demo-private-storage-roots.md) |
| Shadow / Private never share DB or keys | [ADR-005](../adr/005-demo-private-storage-roots.md), [ADR-008](../adr/008-shadow-storage-roots.md) |
| Notes / Contacts tokenisation for remote | [ADR-004](../adr/004-notes-best-effort-no-sqlite.md), [privacy-model.md](./privacy-model.md) |
| Open loops ≠ shared commitments | [open-loop-commitments.md](./open-loop-commitments.md) |
| Encryption ≠ privacy (four-layer stack) | [ADR-017](../adr/017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) |

## Non-goals (initial ADR programme)

- Protocol, crypto, or relay **implementation** (documentation only in this programme)
- Free-form LLM ↔ LLM conversation across the trust boundary
- Sharing inbox, calendar, memory, or world-model context with peers
- Raw model context windows on the wire
- Remote mutation of another Enigma's private state
- Blockchain or zero-knowledge proofs as requirements
- Treating OpenPGP as the coordination protocol, or inheriting PGP key-management UX
- Freezing a specific transport or crypto library beyond stated security properties
- Bespoke transport verb per product workflow
- Large capability catalogue before dinner proof
- Punching holes in Demo / Private / Shadow separation

## Future package boundary

Coordination runtime code is **not implemented**. When claimed, expect a dedicated package (e.g. `packages/coordination`) owning envelope validation, capability registry, ledger, and relay client — wired from `apps/api` and Assist UI. Do not add to [AGENTS.md](../../AGENTS.md) modular boundaries table until a ticket claims that package.

## Company-level framing

**Consumer:** Two friends' Enigmas negotiate dinner without either LLM seeing the other's full calendar.

**B2B:** A buyer's Enigma asks a supplier's Enigma "can you fulfil quantity X by date Y?" — not "show me your ERP."

Same architecture: private agent, trust protocol, verified execution. Different capability schemas and trust tiers.
