# D16 — Demo Mode reset (wipe + reseed)

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/demo-reset` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/api/src/personal_enigma/api/routes/demo*.py`, `apps/api/tests/test_demo*.py`
- May edit: `apps/web/src/demo/**`, demo styles in `apps/web/src/styles.css` if needed for the control
- May edit: `packages/simulation/.../checkpoints.py`, `.../engine.py` (`assert_demo_storage_root` / bootstrap helpers only), matching simulation tests
- May edit: `tickets/demo-ui/D16-*.md`, `tickets/README.md` (domain index only), `docs/architecture/milestone-map.md` (D16 row)
- Must not edit: scenario corpus (`scenarios/**`), Private/Shadow storage defaults, AGENTS.md merge-gate wording unless required

## Hard depends

- D01 (Demo/Private storage roots)
- D05 (`reset_demo_storage` / demo layout)
- D10 (`/demo/*` chrome)

## Soft depends (~)

- D14 live attention pipeline (reset should remain valid with stubs or live attention)

## Unlocks / enhances

- Restart alex-v1 (or the active demo scenario) without manual DB surgery
- Safer demos / CI loops that need a clean Demo root

## Non-goals

- New corpus science, D08e scale loads, or attention UX polish
- Wiping Private or Shadow roots
- Desktop Tauri `demo_reset` IPC (S* — post Phase 2.5)

## Acceptance criteria

- [x] `POST /demo/reset` (and timeline reset wired to the same wipe) clears Demo storage for the active scenario only
- [x] After reset: demo layout reseeds; session status reflects a fresh run (epoch clock + restored attention stubs / bootstrap)
- [x] Reset refuses Private and Shadow roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
- [x] Idempotent: second reset leaves a clean layout and fresh status
- [x] `/demo` UI exposes a **Reset demo** control with confirm

## Test plan

- `uv run pytest apps/api/tests/test_demo.py` (reset clears demo data; private/shadow untouched; idempotent)
- `pnpm --filter @personal-enigma/web test` (Reset demo confirm + POST)

## Privacy constraints

- Never point Demo reset at Private/Shadow storage
- Never migrate Demo data into Shadow/Private
