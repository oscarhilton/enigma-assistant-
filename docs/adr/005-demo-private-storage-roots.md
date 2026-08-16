# ADR-005: Demo vs Private storage roots

## Status

Accepted

## Context

Demo Mode must replay fictional lives with known ground truth without risking contamination of a user's private model. Shared databases, HMAC keys, vector indexes, or cursors would make "REAL SOURCE ACCESS = IMPOSSIBLE" unverifiable and could leak private identifiers into demo evaluation artefacts.

## Decision

- Persist Demo and Private under **separate storage roots**, not shared schemas.
- Default conceptual layout: `~/.enigma/private/...` vs `~/.enigma/demo/<scenario>/...`.
- Paths are **configurable** (env / settings) for tests and CI; defaults encode the separation.
- Demo never reuses Private HMAC / PERSON_* keys, credentials, or audit logs.
- `EnvironmentMode` (`demo` | `private`; later `shadow` per [ADR-008](./008-shadow-storage-roots.md)) is part of runtime identity and must appear on jobs / audit records once those land.

## Consequences

- Resetting a demo scenario deletes only under the demo root.
- Agents must not point Demo at the Private DB URL or vice versa.
- Shadow Mode is a **third** storage identity (not a Private policy layer); see [ADR-008](./008-shadow-storage-roots.md).
