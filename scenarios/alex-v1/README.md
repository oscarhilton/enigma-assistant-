# scenarios/alex-v1

Canonical Demo Mode scenario package for **Alex Morgan** (fictional).

## Release

| Field | Value |
| --- | --- |
| Version | `0.2.1` |
| Status | `benchmark` |
| Span | 3 weeks (2026-01-05 → 2026-01-25) in 0.2.1. Six-month ordinary events (2026-01 → 2026-06) is the [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md) version bump — nested month dirs are scaffold, **not loaded** until 0.3.0. |

## Immutability

Once released as a benchmark, treat the package as **immutable**.

- Do **not** edit released timeline semantics in place.
- **v0.2.1** is an evaluator-correction release: additive `ground_truth/` only
  (obligations, support contracts, windows) — no timeline edits.
- Ship changes by bumping `version` in `scenario.yaml` while keeping package id / directory `alex-v1`.
- Only introduce a new directory (new manifest `id`) if the corpus is intentionally forked into a separate package. **Do not** fork Alex into `scenarios/alex-v2/` for six months — that is a version bump here ([D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)).

## Layout

```text
scenario.yaml      Package metadata
persona.yaml       Declarative fictional persona
background.yaml    Demo/canonical background density (evaluator metadata)
entities/          Contacts roster
timeline/          week-01.yaml … week-03.yaml (0.2.1 January)
                   2026-01/ … 2026-06/  (D08f scaffold; source events only; ignored until 0.3.0)
content/           Email / notes bodies
ground_truth/      Obligations, commitments, windows, checkpoints, background signals
attacks/           Adversarial packs (D9)
```

## Background profiles (D08c)

Default `profile: demo` loads a **small** finepersonas-mini slice for CI.
`profiles.canonical` documents the Phase-2 ~5k message target (D08e; not enabled in PR CI).

## Themes covered

Work planning, personal logistics, project ambiguity (checkout), relationships,
deadlines, newsletter/promo noise, and cross-source merges (mail+reminder+calendar).

Intentional open loop at end of week 3: Sam empty-state reply (attention eval).
