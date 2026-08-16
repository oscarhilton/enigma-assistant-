# M04 — Privacy invariant tests

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M04-privacy-invariant-tests` |
| Domain | `privacy` |

## Package boundary (hard)

- May edit: `packages/privacy/**`
- May add invariant tests under `packages/privacy/tests/**` that import other packages read-only
- Must not edit: transformation implementation beyond necessary hooks already exported

## Hard depends

- M01, M03

## Soft depends (~)

- M02

## Unlocks / enhances

- Hard-unlocks M05, M11, M17 confidence for remote-facing work

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
