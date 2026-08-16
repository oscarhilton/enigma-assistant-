# S06 — Shadow exit criteria (post Phase 2.5)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/S06-shadow-exit-criteria` |
| Domain | `shadow` |
| Baseline | `v0.2.0-demo` |

## Package boundary (hard)

- May edit: `docs/architecture/shadow-mode.md`, `docs/reports/**` for a Shadow exit template
- May edit: `packages/evaluation/**` for a Shadow exit checklist / stub collector
- May edit: matching tests
- May amend: `docs/architecture/milestone-map.md`, `tickets/README.md`
- Must not edit: Demo F-* gates (historical PASS stays immutable), Gmail OAuth, live notification enablement without checklist

## Hard depends

- S01 `done`
- Phase 2.5 PASS (bootstrap prerequisite — already true)

## Soft depends (~)

- S03–S05 for a meaningful exit artefact

## Unlocks / enhances

- Clear gate before enabling Private notifications on real attention
- Prevents “Demo was green → ship nagging”

## Non-goals

- Declaring Shadow complete in this ticket’s first landing
- Re-opening Demo Mode for more synthetic tuning
- Waiving privacy invariants

## Acceptance criteria

- [ ] Documented Shadow → Private promotion checklist derived from the seven evaluation goals
- [ ] Explicit statement that Phase 2.5 PASS authorises Shadow *bootstrap*, not notification enablement
- [ ] Stub exit report template (PASS/FAIL placeholders) under `docs/reports/` or evaluation package
- [ ] No code path auto-enables notifications solely because Demo / Phase 2.5 passed

## Test plan

- Template renders with PENDING status by default
- Guard test: Shadow mode still suppresses notifications even when Phase 2.5 report is PASS

## Privacy constraints

- Exit artefacts stay local; no wholesale private corpus upload
