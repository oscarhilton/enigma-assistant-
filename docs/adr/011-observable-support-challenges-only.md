# ADR-011: Observable support challenges only — no diagnostic labels in benchmarks

## Status

Accepted

## Context

Enigma’s second benchmark dimension asks whether suggested help **reduces executive-function friction** — not whether the system correctly diagnosed a user. Product language and clinical labels (e.g. “ADHD=true”, “executive dysfunction score”) are tempting shortcuts for authoring personas and scoring runs, but they:

1. **Leak author intent into the runtime model** if ever wired into prompts, features, or UI.
2. **Conflate diagnosis with behaviour** — the benchmark should score observable situations and support quality, not medical classification.
3. **Block generalisation** — many users experience initiation friction, admin avoidance, or time-blindness without any labelled condition.

Alex v1 already encodes author-side persona traits (`admin_avoidance: moderate` in `persona.yaml`) for **scenario writing only**. Those traits must never become Enigma inputs or evaluator shortcuts that replace concrete support contracts.

## Decision

1. **No diagnostic or condition labels in benchmark datasets.** Do not add `adhd: true`, `executive_dysfunction`, or equivalent fields to scenario manifests, ground truth, or evaluation reports visible to Enigma.
2. **Encode friction via evaluator-only `support_challenges`.** Tags name *observable situations* (e.g. `task_initiation`, `admin_friction`, `time_blindness`) attached to checkpoints and support contracts — never to the user record Enigma reasons over.
3. **Persona traits remain author-side.** `persona.yaml` may guide arc writing; it is not ground truth for scoring and must not be ingested by simulation sources or attention.
4. **Support contracts are evaluator-only.** Like obligations and attention windows ([D06](../../tickets/demo-evaluation/D06-ground-truth.md)), `support:` blocks live under `ground_truth/` and are invisible to Enigma ingest paths.
5. **Two independent checkpoint questions** at each scored instant:
   - **Attention** — “What needs me?” (surface / silence / timing)
   - **Next action** — “What should I do next?” (actionability, size, friction reduction)

Architecture reference: [executive-function-support-benchmark.md](../architecture/executive-function-support-benchmark.md).

## Consequences

- Evaluators gain a stable vocabulary for support fitness without medical framing.
- Alex v2 arc authors tag challenges explicitly; v1 mapping is retrospective documentation only.
- LLM benchmark arms (Arm B/C) may return structured `attention` + `next_action` outputs scored against allowed support actions — not against hidden persona labels.
- UI and Private Mode must not display “ADHD support mode” derived from benchmark metadata.

## Related

- [ADR-007](./007-demo-corpus-provenance.md) — evaluator-only signal classes
- [D06 ground truth](../../tickets/demo-evaluation/D06-ground-truth.md)
- [V2-EF-01 support contract design](../../tickets/demo-scenario/V2-EF-01-support-contract-design.md)
