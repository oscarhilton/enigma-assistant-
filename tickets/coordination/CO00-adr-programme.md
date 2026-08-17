# CO00 — Enigma coordination ADR programme

**Status:** done  
**Branch:** `ticket/CO00-adr-programme`  
**Domain:** coordination (documentation)  
**Package boundary:** `docs/adr/013-*.md` … `docs/adr/019-*.md`, `docs/architecture/enigma-coordination-protocol.md`, `tickets/coordination/**`, `docs/architecture/overview.md`, `tickets/README.md`

## Non-goals

- Protocol, crypto, API, or relay implementation
- Dinner prototype implementation (see CO01)
- Capability catalogue beyond illustrative examples in ADRs

## Deliverables

- [x] ADR-013 — Inter-Enigma coordination trust boundary
- [x] ADR-014 — Minimal semantic envelope protocol
- [x] ADR-015 — Capability-scoped disclosure, not data access
- [x] ADR-016 — Bilateral consent and shared commitments
- [x] ADR-017 — Cryptographic identity, signed envelopes, encrypted relay
- [x] ADR-018 — Disclosure ledger and inference-attack protection
- [x] ADR-019 — Delegated authority and execution ladder (A0–A5)
- [x] Companion doc `docs/architecture/enigma-coordination-protocol.md`
- [x] Cross-links from overview and tickets index
- [x] Programme README under `tickets/coordination/`
- [x] ADR-017 records PGP/OpenPGP as intellectual ancestry (identity, signatures, recipient encryption) without adopting PGP as protocol or UX; four-layer privacy stack cross-links 015/016/018/019

## Acceptance criteria

- [x] Seven ADRs match repo ADR format and date 2026-08-17
- [x] ADRs cross-link in sequence 013 → 019
- [x] Architecture doc describes end-to-end flow, dinner proof, non-goals, three layers, and the cryptographic / privacy stack
- [x] No contradiction with ADR-004, ADR-005, ADR-008, privacy-model, conversational-ui
- [x] ADR-019 documents A0–A5 as canonical; references C07 Assist without conflict
- [x] ADR-017 does not treat OpenPGP as the protocol; PGP UX ceremonies are rejected

## Privacy constraints

Documentation only. Programme must state Demo/Private/Shadow separation and no wholesale private export across boundary.

**Unlocks:** CO01 and future coordination implementation tickets
