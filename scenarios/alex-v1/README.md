# scenarios/alex-v1

Canonical Demo Mode scenario package for **Alex Morgan** (fictional).

## Release

| Field | Value |
| --- | --- |
| Version | `0.2.0` |
| Status | `benchmark` |
| Span | 3 weeks (2026-01-05 → 2026-01-25) |

## Immutability

Once released as a benchmark, treat the package as **immutable**.

- Do **not** edit released timeline / ground-truth semantics in place.
- Ship changes by bumping `version` in `scenario.yaml` while keeping package id / directory `alex-v1`.
- Only introduce a new directory (new manifest `id`) if the corpus is intentionally forked into a separate package.

## Layout

```text
scenario.yaml      Package metadata
persona.yaml       Declarative fictional persona
entities/          Contacts roster
timeline/          week-01.yaml … week-03.yaml
content/           Email / notes bodies
ground_truth/      Obligations, commitments, windows, checkpoints
attacks/           Adversarial packs (D9)
```

## Themes covered

Work planning, personal logistics, project ambiguity (checkout), relationships,
deadlines, newsletter/promo noise, and cross-source merges (mail+reminder+calendar).

Intentional open loop at end of week 3: Sam empty-state reply (attention eval).
