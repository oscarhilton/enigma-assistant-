# scenarios/alex-v1

Canonical Demo Mode scenario package for **Alex Morgan** (fictional).

## Immutability

Once this scenario is **released** as a benchmark (evaluation baselines published
or CI gates pinned to it), treat the package as **immutable**.

- Do **not** edit released timeline / ground-truth semantics in place.
- Ship changes as `alex-v1.1` or `alex-v2` (see Phase 2 scenario versioning).
- Scaffold / pre-release edits are allowed until D8 marks the corpus released.

## Layout

```text
scenario.yaml      Package metadata
persona.yaml       Declarative fictional persona
entities/          Contacts, orgs, projects, places (D8)
timeline/          Time-ordered events (D8)
content/           Email / notes / attachments bodies (D8)
ground_truth/      Obligations, commitments, checkpoints (D6/D8)
attacks/           Adversarial packs (D9)
```

## Ownership

| Concern | Ticket |
| --- | --- |
| Schema / loader | D3 |
| Full 3-month corpus | D8 |
| Ground-truth models | D6 |
| Attacks | D9 |
