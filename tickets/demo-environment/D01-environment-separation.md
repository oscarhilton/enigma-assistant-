# D01 — Environment separation

| Field | Value |
| --- | --- |
| Status | `done` (merged #22) |
| Branch | `ticket/D01-environment-separation` |
| Domain | `demo-environment` |
| Baseline | `v0.1.0-mvp` (`6253f96`) |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/environment.py`
- May edit: `packages/simulation/src/personal_enigma/simulation/__init__.py`
- May edit: `packages/simulation/tests/test_environment.py` (and env-only tests)
- May edit: `apps/api/src/personal_enigma/api/**` only to wire Core to receive an `Environment` (mode banner stub OK)
- May edit: `apps/web/src/**` only for a minimal DEMO MODE banner stub (full chrome is D10)
- May add/amend: `docs/adr/005-demo-private-storage-roots.md`, `docs/architecture/demo-mode.md`
- Must not edit: synthetic source bodies (D04), clock domain migration (D02), scenario corpora (D03/D08), eval runner (D07)

## Hard depends

- MVP complete (`v0.1.0-mvp`)

## Soft depends (~)

- None

## Unlocks / enhances

- Hard-unlocks D02–D12
- Makes “REAL SOURCE ACCESS = IMPOSSIBLE” a structural property, not a UI flag

## Non-goals

- Scenario loading / simulation engine
- Full demo UI chrome
- Filling `scenarios/alex-v1/` with content
- Refactoring MVP attention/obligations unless required to accept an `Environment`

## Acceptance criteria

- [ ] `Environment` protocol (or equivalent) exposes `mode`, `storage`, `sources`, `secrets` (or `SecretNamespace`)
- [ ] `PrivateEnvironment` registers only real connectors; `DemoEnvironment` registers only synthetic slots and sets real credential fields to `None`
- [ ] Core boots from an environment object — not scattered `if settings.demo_mode` checks for source construction
- [ ] Storage roots split immediately per [ADR-005](../../docs/adr/005-demo-private-storage-roots.md):

```text
~/.enigma/
├── private/   # enigma.db, vectors/, state/, secrets/
└── demo/<scenario>/  # enigma.db, vectors/, state/, config/
```

- [ ] Separate SQLite, embedding indexes, aliases, HMAC namespaces/keys, source cursors, audit + attention history
- [ ] Demo runtime does **not** load `GOOGLE_CLIENT_SECRET`, `GMAIL_TOKEN`, `APPLE_BRIDGE_TOKEN`, or `PRIVATE_HMAC_KEY` into its secret namespace
- [ ] Registering or instantiating a real connector under `EnvironmentMode.DEMO` raises
- [ ] API/web expose an unmistakable DEMO MODE banner stub (full surfaces = D10)

## Test plan

- Storage root separation + env overrides
- **Hostile boot test (must-have):** with `ExplodingRealSource` / exploding factories for `GmailSource`, `GoogleCalendarSource`, `AppleBridgeClient` (and siblings), booting the app under `ENIGMA_ENVIRONMENT=demo` (or `ENIGMA_ENVIRONMENT_MODE=demo`) **never constructs** those classes — not merely “doesn’t call them”
- Assert Demo secret namespace lacks private credential keys
- Private mode still constructs real sources normally

## Privacy constraints

- When Demo Mode is active: `REAL SOURCE ACCESS = IMPOSSIBLE`
- Demo must never pollute Private learned memory (separate roots + keys)
