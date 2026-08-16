# ADR-008: Shadow storage roots and no Demo→Shadow migration

## Status

Accepted

## Context

Phase 2.5 exit is PASS (`v0.2.0-demo`). Shadow Mode must observe a real life without contaminating Private learned memory and without treating Demo’s fictional continuity as a warm start. [ADR-005](./005-demo-private-storage-roots.md) separated Demo from Private and left Shadow as a possible “Private policy layer.” That under-specifies Phase 3: Shadow needs its own durable root, and Demo artefacts must never be migrated into it.

## Decision

1. **Dedicated Shadow storage root.** Persist Shadow under `~/.enigma/shadow/...` (configurable via `ENIGMA_SHADOW_STORAGE_ROOT` / `ENIGMA_HOME`), separate from `private/` and `demo/<scenario>/`.
2. **Fresh private DB.** First Shadow boot creates empty Shadow databases, vector indexes, cursors, and HMAC / PERSON_* namespaces. It does not open Private or Demo DB URLs.
3. **No Demo→Shadow migration.** Copying, hard-linking, remapping, or re-keying Demo scenario storage (or Demo secrets) into Shadow is forbidden. Any migration helper must raise (`DemoDataMigrationError` / equivalent). There is no successful path.
4. **No Demo→Private warm-start either.** The same refuse applies when the target is Private; Shadow’s “fresh DB” rule must not become a backdoor that launders Demo state through Private.
5. **`EnvironmentMode.SHADOW`.** Runtime identity includes `shadow` alongside `demo` | `private`. Jobs / audit records must carry mode once those land.
6. **Supersedes ADR-005’s Shadow note.** Shadow is not “Private with notifications off”; it is a third storage identity with notification suppression as policy (see [shadow-mode.md](../architecture/shadow-mode.md)).

## Consequences

- Resetting Shadow deletes only under the Shadow root.
- Agents must not point `ENIGMA_DATABASE_URL` for Shadow at Demo or Private paths.
- Comparison to Demo metrics (evaluation goals) uses exported scores / reports, never shared DBs or keys.
- Demo Mode remains frozen for polish; Shadow tickets own Phase 3 scaffolding.
