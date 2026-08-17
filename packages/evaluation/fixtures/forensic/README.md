# Forensic dumps (Demo Alex)

These files are **Demo Mode** captures (persona Alex Morgan / `alex_v1`). They are not a private-world recording.

| File | What |
| --- | --- |
| `alex_jan19_continuity_integrity.dump.txt` | Full 61-turn forensic UI blob (C23 source of truth) |
| `alex_jan19_continuity_integrity.turns.yaml` | Compact turn index: exact user utterances + gate tags |
| `alex_jan19_brunch_details_regression.trace.yaml` | Brunch details regression trace (C15/C21/C20/C22; outside C23 gate) |

The web formatter that *produces* this blob is `apps/web/src/enigma/forensicDump.ts`. Do not treat that module as the dump.

Life Script that quotes the gate utterances: `packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml` ([C23](../../../../tickets/conversational-ui/C23-continuity-integrity-life-script.md)).

Brunch details regression script: `packages/evaluation/scripts/alex_jan19_brunch_details_regression.script.yaml`.
