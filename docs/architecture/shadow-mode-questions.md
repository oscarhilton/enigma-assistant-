# Shadow Mode — unanswered questions (evaluation goals)

**Status:** Evaluation goals for Phase 3 — not an implementation checklist.  
**Architecture:** [shadow-mode.md](./shadow-mode.md)  
**Prerequisite:** Phase 2.5 PASS (`v0.2.0-demo`) — satisfied; Shadow tickets may proceed.

Demo Mode showed that Enigma works on a coherent fictional life. Shadow Mode asks whether a **real** life behaves like Alex’s synthetic one. Treat these as **evaluation goals** for journals, metrics, and comparison stubs (S05) — not as features to implement in the S01 scaffold.

1. **Act-on recognition** — When the user actually acts on something, did Enigma surface it (or would it have)?
2. **Nearly-forgot** — Does Enigma catch obligations the user almost missed, or only the obvious ones?
3. **Importance overestimate** — How often does Enigma treat something as high-attention when the user correctly ignores it?
4. **Relationship correctness** — Are people, roles, and recurring ties resolved the way the user experiences them?
5. **Memory improvement** — Does the model get more useful over weeks of real evidence, or plateau / drift?
6. **Timing** — Does attention arrive early enough to help, or too late / too early to matter?
7. **Misses synthetic never taught** — What failure modes appear in real mail/calendar noise that Alex’s authored + corpus world never exercised?

Implementation order (env → storage → suppress notifications → attention log → comparison stubs → exit) lives under [tickets/shadow/](../../tickets/shadow/). Do not invent Demo/F-* polish tickets to answer these.
