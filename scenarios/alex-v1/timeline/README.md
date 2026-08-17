# alex-v1 timeline

Source events only. No biography. No pre-baked obligations, commitments, or attention items.

```text
week-01.yaml … week-03.yaml   # 0.2.1 January — loaded (timeline/*.yaml)
2026-01/                      # pointer; do not duplicate the week files
2026-02/ … 2026-06/           # D08f scaffold — NOT loaded until 0.3.0 recursive glob
```

**Rule:** don’t write six months of biography; write six months of ordinary events. Discover Alex only as much as the next episode requires. No `ALEX_BIOGRAPHY.md`.

Spec: [demo-corpus.md](../../../docs/architecture/demo-corpus.md#six-month-ordinary-life-d08f) · [D08f](../../../tickets/demo-scenario/D08f-alex-six-month.md)

Chat-shaped evidence uses existing types (`email.receive`, `note.upsert`) until a synthetic message source is ticketed under D04. Do not edit `packages/ingestion/.../sources/*` from Demo tickets.
