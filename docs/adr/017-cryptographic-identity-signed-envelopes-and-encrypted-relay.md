# ADR-017: Cryptographic identity, signed envelopes, and encrypted relay

## Status

Accepted

## Date

2026-08-17

## Context

Cross-boundary messages ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)) must be authentic, integrity-protected, replay-resistant, and confidential in transit. Display names and email addresses are not security identities. Local bridge auth ([ADR-002](./002-bridge-local-transport-auth.md)) covers Apple Bridge only; inter-Enigma coordination needs a separate identity and transport story that keeps the relay deliberately dumb.

PGP / OpenPGP is the right **intellectual ancestry** for that envelope layer: public-key identity, tamper-evident signatures, and encryption to a recipient so an untrusted relay can carry ciphertext without reading the payload. Classic PGP does **not** solve Enigma's interesting problems — capability, consent, cumulative inference, expiry, versioned commitment, or execution. This ADR records that split so later tickets do not treat "PGP for agents" as the coordination protocol.

## Decision

Enigma adopts the public-key identity, recipient encryption and message-signing properties associated with PGP/OpenPGP, but does not adopt PGP's user-facing key-management model or treat OpenPGP as the coordination protocol.

```text
PGP-ish crypto  →  protects the envelope
Enigma protocol →  defines meaning + authority + consent
```

PGP can prove who said something and keep others from reading it. Enigma still has to decide what they're allowed to say, learn and cause.

Concrete algorithms, libraries, and wire encodings are **not frozen here**. Choose later for device keys, forward secrecy, group messaging, rotation, and modern libraries — not because the format is historically called OpenPGP.

### What the cryptographic layer provides

Excellent fit from the PGP tradition:

- **Public-key identity** — "this message really came from Enigma A"
- **Signatures** — tamper-evident, attributable envelopes
- **Encryption to recipient** — relay carries ciphertext without reading payload

Envelope flow:

```text
sender private key
    → sign protocol envelope
    → encrypt to recipient public key
    → opaque relay
    → decrypt
    → recipient verifies signature
```

Philosophical overlap with PGP: no central server needs everyone's secrets. Enigma identities are based on keypairs. Messages remain verifiable through an untrusted relay.

### What cryptography does not provide

Classic PGP secures "Oscar sent Tobi these bytes." It does **not** decide:

- whether those bytes represent `event.propose` vs `availability.query` vs `dependency.complete` ([ADR-014](./014-minimal-semantic-envelope-protocol.md))
- whether Oscar was authorised to ask that question ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md))
- whether Tobi already disclosed too much through previous queries ([ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md))
- whether acceptance requires human approval ([ADR-016](./016-bilateral-consent-and-shared-commitments.md), [ADR-019](./019-delegated-authority-and-execution-ladder.md))
- whether a proposal expired
- how shared commitment is versioned ([ADR-016](./016-bilateral-consent-and-shared-commitments.md))
- what capability the sender possesses ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md))
- whether an accepted commitment has been executed ([ADR-019](./019-delegated-authority-and-execution-ladder.md))

### Privacy stack (encryption ≠ privacy)

Encrypted availability probes still reconstruct a calendar: "Are you free at 09:00?" / "09:30?" / "10:00?" … remains an inference attack even when every byte is ciphertext.

| Layer | Question | Owner |
| --- | --- | --- |
| **1. Cryptographic privacy** | Who can read this? | This ADR |
| **2. Semantic privacy** | What are they allowed to ask? | [ADR-015](./015-capability-scoped-disclosure-not-data-access.md) |
| **3. Inference privacy** | What can they learn cumulatively? | [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md) |
| **4. Consent** | What are they allowed to cause? | [ADR-016](./016-bilateral-consent-and-shared-commitments.md), [ADR-019](./019-delegated-authority-and-execution-ladder.md) |

PGP-shaped crypto tackles **layer 1** plus authentication and signatures. Layers 2–4 are the Enigma protocol.

### Invisible crypto (product UX)

Do **not** inherit historic PGP ergonomics: ASCII-armored key blocks, fingerprints as identity, manual trust ceremonies, or uploading keys to servers.

Product identity is a person / device relationship:

```text
Tobi ✓ Verified contact
Devices: MacBook active, iPhone active
Security: Identity verified
```

Underneath = public/private keys. Users never manage 40-character fingerprints.

### Identity and key hierarchy

- Every Enigma user / installation / organisation has a **verifiable cryptographic identity**.
- **Display names are never security identities.** UI maps identity refs to local Contacts / labels.
- Support **key rotation**, **revocation**, **device replacement**, **identity verification** (out-of-band or org policy), and **compromised-key recovery**.

Borrow PGP's long-lived identity vs device-key split:

```text
Enigma identity
├── user identity key
├── device key: laptop
├── device key: phone
└── device key: server
```

The long-lived identity signs / authorises device keys. Devices sign protocol envelopes.

```text
Oscar (authorised) → Oscar's Mac (signed) → event proposal
```

Lost device: revoke the device key without replacing the whole network identity.

Organisations:

```text
Acme Ltd identity → authorises Procurement Agent, Sales Agent, Support Agent
```

"Acme Procurement attests X" must be cryptographically distinguishable from a random employee laptop.

### Message security properties

Every protocol envelope ([ADR-014](./014-minimal-semantic-envelope-protocol.md)) must be:

- Signed by a device key authorised by the sender identity
- Authenticated to intended recipient
- Expiry-bound (`expires_at`)
- Nonce / replay protected
- Integrity protected
- **End-to-end encrypted in transit** (relay sees ciphertext + routing metadata only)

### Relay responsibilities (deliberately boring)

The relay **may** provide:

- Identity / key discovery (directory)
- Encrypted envelope routing
- Delivery receipts
- Revocation metadata propagation
- Public capability metadata (for policy UI — not private payloads)

The relay **must not** require:

- Private world data
- Reasoning context
- Plaintext coordination payloads

### Portable shared commitments (future property)

Signed protocol records enable contract-like proof **without a blockchain**:

```text
Oscar PROPOSES dinner (signed, hash ABC)
Tobi ACCEPTS (signed, hash XYZ, references ABC)
```

Neither Enigma needs to trust the relay's database. Two parties independently signed the same state transition ([ADR-016](./016-bilateral-consent-and-shared-commitments.md)). Implementation of portable proof packs is deferred; the envelope and identity design must not preclude it.

### Non-requirements

- **No blockchain requirement.**
- **No zero-knowledge proof requirement** in the initial programme.
- **Do not freeze** OpenPGP, a single library, or a single transport (HTTP, queue, etc.) beyond the security properties above.
- Transport TLS is not a substitute for end-to-end envelope encryption.

## Consequences

- Implementation tickets own concrete algorithms (signatures, key agreement, AEAD, rotation) without reopening this ancestry-vs-protocol decision.
- Demo proofs may use fixture keys under Demo storage roots; never reuse Private HMAC / PERSON keys ([ADR-005](./005-demo-private-storage-roots.md)).
- Audit logs record envelope ids and capability names, not decrypted payloads, where logs leave the device.
- Assist and contact UI show verified-person / active-device state, not raw key material ([ADR-019](./019-delegated-authority-and-execution-ladder.md)).
- Capability checks, disclosure ledger, and consent ladder remain mandatory after successful decrypt-and-verify ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md), [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md), [ADR-016](./016-bilateral-consent-and-shared-commitments.md)).

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Treat OpenPGP as the coordination protocol ("PGP for agents") | Secures bytes, not meaning, capability, consent, inference, expiry, or execution. |
| Historic PGP UX (armored keys, fingerprints, key servers, web of trust) | Product identity is person/device; those ceremonies are the pain to avoid. |
| Email/SMS as transport | No E2E authenticity; phishing and replay; not machine-verifiable. |
| Mutual TLS only (no E2E) | Relay and operators can read coordination content. |
| Blockchain identity registry | Operational cost and complexity; signed records suffice for portable proof. |
| Encryption of a calendar export blob | Cryptographic privacy without semantic privacy; still wholesale data transfer ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md)). |

## References

- [ADR-013](./013-inter-enigma-coordination-trust-boundary.md) · [ADR-014](./014-minimal-semantic-envelope-protocol.md) · [ADR-015](./015-capability-scoped-disclosure-not-data-access.md) · [ADR-016](./016-bilateral-consent-and-shared-commitments.md) · [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md) · [ADR-019](./019-delegated-authority-and-execution-ladder.md)
- [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
