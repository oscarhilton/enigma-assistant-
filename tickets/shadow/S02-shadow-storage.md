# S02 — Shadow storage isolation

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/S02-shadow-storage` |
| Domain | `shadow` |
| Baseline | `v0.2.0-demo` |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/environment.py` (secrets / root helpers only)
- May edit: `apps/api/src/personal_enigma/api/**` for DB URL / settings wiring to Shadow root
- May edit: `apps/worker/**` only for mode-aware storage resolution
- May edit: `packages/simulation/tests/**`, `apps/api/tests/**`
- May amend: `docs/adr/008-shadow-storage-roots.md` if wiring details change
- Must not edit: Demo roots / scenario packages, notification delivery, attention log schema (S04), Gmail OAuth

## Hard depends

- S01 `done`

## Soft depends (~)

- M00a persistence patterns

## Unlocks / enhances

- Safe Shadow boots without Private/Demo contamination
- Unlocks S04 attention log persistence under Shadow root

## Non-goals

- Migrating or importing Demo data (forever refused)
- Notification suppression implementation (S03)
- Eval comparison stubs (S05)

## Acceptance criteria

- [ ] Core + worker resolve SQLite, vectors, aliases, HMAC namespace under Shadow root only when `EnvironmentMode.SHADOW`
- [ ] Shadow HMAC / PERSON_* keys are generated fresh — not copied from Demo or Private
- [ ] Hostile test: pointing Shadow at a Demo path raises
- [ ] Hostile test: Demo→Shadow copy helper still has no successful path
- [ ] Private and Demo boots unchanged

## Test plan

- Env overrides for `ENIGMA_SHADOW_STORAGE_ROOT`
- Key namespace isolation assertions
- Boot with Demo DB URL under Shadow mode → refuse

## Privacy constraints

- Separate secrets bags; no credential laundering via Demo
