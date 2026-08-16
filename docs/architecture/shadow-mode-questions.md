# Shadow Mode — unanswered questions (after synthetic Alex)

**Status:** Design note only — not an implementation ticket.  
**Prerequisite:** Prove F-* exit criteria and Phase 2.5 freeze before any Shadow code.

Demo Mode can show that Enigma works on a coherent fictional life. It cannot yet answer whether a **real** life behaves like Alex’s synthetic one. These are the open questions that Shadow (or an equivalent quiet observation phase) would need to confront:

1. **Act-on recognition** — When the user actually acts on something, did Enigma surface it (or would it have)?
2. **Nearly-forgot** — Does Enigma catch obligations the user almost missed, or only the obvious ones?
3. **Importance overestimate** — How often does Enigma treat something as high-attention when the user correctly ignores it?
4. **Relationship correctness** — Are people, roles, and recurring ties resolved the way the user experiences them?
5. **Memory improvement** — Does the model get more useful over weeks of real evidence, or plateau / drift?
6. **Timing** — Does attention arrive early enough to help, or too late / too early to matter?
7. **Misses synthetic never taught** — What failure modes appear in real mail/calendar noise that Alex’s authored + corpus world never exercised?

Until F-* gates and Phase 2.5 exit are green (or explicitly waived by ADR), do **not** add `EnvironmentMode.SHADOW`, Shadow tickets, or Shadow storage/notification scaffolding.
