# S01 — Shadow Mode scaffold (env flag)

| Field | Value |
| --- | --- |
| Status | `done` (merged #65) |
| Branch | `ticket/S01-shadow-scaffold` |
| Domain | `shadow` |
| Baseline | `v0.2.0-demo` (Phase 2.5 PASS) |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/environment.py`
- May edit: `packages/simulation/src/personal_enigma/simulation/__init__.py`
- May edit: `packages/simulation/tests/test_environment.py` (and shadow-env tests)
- May edit: `apps/api/src/personal_enigma/api/**` only to wire `/shadow/banner` (and thin env stub)
- May edit: `apps/web/src/**` only for a minimal SHADOW MODE banner stub
- May add/amend: `docs/adr/008-shadow-storage-roots.md`, `docs/architecture/shadow-mode.md`, `docs/architecture/shadow-mode-questions.md`, `docs/architecture/milestone-map.md`, `tickets/README.md`, `tickets/shadow/**`
- Must not edit: Demo scenario corpora, F-* eval gates, Gmail OAuth, notification delivery (S03), attention log persistence (S04)

## Hard depends

- Phase 2.5 exit PASS (`docs/reports/phase-2.5-exit-report.md`, tag `v0.2.0-demo`)

## Soft depends (~)

- None

## Unlocks / enhances

- Hard-unlocks S02–S06
- Makes Demo→Shadow migration structurally impossible

## Non-goals

- Full Shadow UI chrome
- Notification channel wiring beyond a suppressed flag stub
- Attention log schema (S04)
- Comparison metrics implementation (S05)
- Gmail OAuth / connector changes
- Demo Mode polish (F-*, D14+)

## Acceptance criteria

- [x] `EnvironmentMode.SHADOW` parsable from `ENIGMA_ENVIRONMENT_MODE=shadow`
- [x] Storage root stub for Shadow (`~/.enigma/shadow` / `ENIGMA_SHADOW_STORAGE_ROOT`)
- [x] `ShadowEnvironment` with wall clock; unmistakable banner text
- [x] Hard refuse Demo→Shadow (and Demo→Private) data migration — no successful path
- [x] API/web expose a SHADOW MODE banner stub
- [x] Architecture doc + ADR-008 + S02–S06 tickets landed
- [x] Demo Mode remains untouched for polish

## Test plan

- Parse `shadow` mode; default remains `private`
- Shadow storage root ≠ private ≠ demo
- `refuse_demo_data_migration` / `ShadowEnvironment.migrate_from_demo` always raise
- Banner active only when mode is shadow
- Existing Demo/Private tests still pass

## Privacy constraints

- Shadow must not open Demo DBs or reuse Demo HMAC / PERSON_* keys
- Never send wholesale Notes / `PrivatePerson` to hosted models (unchanged)
