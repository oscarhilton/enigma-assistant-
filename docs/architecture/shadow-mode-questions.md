# Shadow Mode — unanswered questions (evaluation goals)

**Status:** Evaluation goals for Phase 3 — rubric in [shadow-evaluation.md](./shadow-evaluation.md)  
**Architecture:** [shadow-mode.md](./shadow-mode.md)  
**Prerequisite:** Phase 2.5 PASS (`v0.2.0-demo`) — satisfied; Shadow tickets may proceed.  
**Scaffold:** S01 `done` (#65) — env/banner/storage refuse. Eval artefacts: SE01–SE03 (soft deps).

Demo Mode showed that Enigma works on a coherent fictional life. Shadow Mode asks whether a **real** life behaves like Alex’s synthetic one. Treat these as **evaluation goals** for journals, metrics, and comparison stubs — not as features to re-implement in the S01 scaffold.

1. **Act-on recognition** — When the user actually acts on something, did Enigma surface it (or would it have)?
2. **Nearly-forgot** — Does Enigma catch obligations the user almost missed, or only the obvious ones?
3. **Importance overestimate** — How often does Enigma treat something as high-attention when the user correctly ignores it?
4. **Relationship correctness** — Are people, roles, and recurring ties resolved the way the user experiences them?
5. **Memory improvement** — Does the model get more useful over weeks of real evidence, or plateau / drift?
6. **Timing** — Does attention arrive early enough to help, or too late / too early to matter?
7. **Misses synthetic never taught** — What failure modes appear in real mail/calendar noise that Alex’s authored + corpus world never exercised?

## How we will measure

| Questions | Ticket |
| --- | --- |
| Interface stubs for all seven goals | [S05](../../tickets/shadow/S05-comparison-stubs.md) |
| 1, 2, 3, 6 — user actions vs attention | [SE01](../../tickets/shadow/SE01-action-vs-attention.md) |
| 3 — would-notify waste (suppress audit) | [SE02](../../tickets/shadow/SE02-suppressed-notification-audit.md) |
| 4, 5, 7 (+ weekly rollup) | [SE03](../../tickets/shadow/SE03-weekly-shadow-review.md) |

Mode order (env → storage → suppress → attention log → comparison stubs → exit): [tickets/shadow/](../../tickets/shadow/) S01–S06. SE* refine measurement artefacts; they must **not** edit `EnvironmentMode` or re-ship the SHADOW MODE banner.
