# M04 — Privacy invariant tests

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M04-privacy-invariant-tests` |
| Domain | `privacy` |

## Package boundary (hard)

- May edit: `packages/privacy/**`
- May add cross-package tests that only *assert* invariants (prefer privacy package)
- May read: transformation, domain, fixtures

## Depends on

- M01, M03

## Unlocks

- M05, M17, confidence for all remote-facing work

## Non-goals

- UI privacy inspector (M17)
- Real Keychain integration

## Acceptance criteria

- [ ] Invariant suite fails CI if raw `PrivatePerson` fields appear in remote payloads
- [ ] Notes default HIGH; wholesale note body cannot be marked remote-safe without explicit policy exception
- [ ] Documented allowlist for what remote payloads may contain
- [ ] Apple integrations remain testable with remote inference disabled

## Test plan

- Property / invariant tests over transformed fixture corpora
- Negative tests attempting to mark secrets as remote-safe

## Privacy constraints

- This ticket *is* the privacy gate; keep it strict
