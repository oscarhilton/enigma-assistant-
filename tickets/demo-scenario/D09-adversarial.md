# D09 — Adversarial scenario pack

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D09-adversarial` |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/attacks/**` and/or `scenarios/feature/adversarial/**`
- May edit: evaluation hooks that assert zero-leak under attack (tests in `packages/evaluation` or `packages/privacy`)
- Must not edit: main Alex timeline authorship (D8) except attack cross-links

## Hard depends

- D1, D3

## Soft depends (~)

- D6, D7, M04 privacy invariants

## Unlocks / enhances

- Privacy demo + Phase 3 exit confidence

## Non-goals

- Live malicious provider network calls in CI without fixtures

## Acceptance criteria

- [ ] Packs for prompt injection, secrets, re-identification, malicious provider, provider failure
- [ ] Privacy invariants remain zero-leak under the pack

## Test plan

- Run adversarial pack through transform + privacy gate
- Assert known direct identifiers / secrets never appear in remote payloads

## Privacy constraints

- Attack fixtures may *contain* synthetic secrets; they must never leave the allowlist
