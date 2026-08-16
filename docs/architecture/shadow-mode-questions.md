# Shadow Mode — unanswered questions (after synthetic Alex)

**Status:** Question inventory — rubric in [shadow-evaluation.md](./shadow-evaluation.md)  
**Mode scaffold:** S01 (`EnvironmentMode.SHADOW`, storage) — separate track  
**Eval tickets:** [SE01](../../tickets/shadow/SE01-action-vs-attention.md) · [SE02](../../tickets/shadow/SE02-suppressed-notification-audit.md) · [SE03](../../tickets/shadow/SE03-weekly-shadow-review.md)

Demo Mode can show that Enigma works on a coherent fictional life. It cannot yet answer whether a **real** life behaves like Alex’s synthetic one. These are the open questions Shadow evaluation must confront:

1. **Act-on recognition** — When the user actually acts on something, did Enigma surface it (or would it have)?
2. **Nearly-forgot** — Does Enigma catch obligations the user almost missed, or only the obvious ones?
3. **Importance overestimate** — How often does Enigma treat something as high-attention when the user correctly ignores it?
4. **Relationship correctness** — Are people, roles, and recurring ties resolved the way the user experiences them?
5. **Memory improvement** — Does the model get more useful over weeks of real evidence, or plateau / drift?
6. **Timing** — Does attention arrive early enough to help, or too late / too early to matter?
7. **Misses synthetic never taught** — What failure modes appear in real mail/calendar noise that Alex’s authored + corpus world never exercised?

**Design vs implementation:** Rubric + SE* tickets may land as docs after Phase 2.5 PASS. Do **not** conflate that with S01 env/storage work — evaluation PRs must not edit `EnvironmentMode`. Full UI, live notification delivery, and Demo→Shadow migration remain out of scope until their owning tickets say otherwise.
