# Forensic dumps (Demo Alex)

These files are **Demo Mode** captures (persona Alex Morgan / `alex_v1`). They are not a private-world recording.

| File | What |
| --- | --- |
| `alex_jan19_continuity_integrity.dump.txt` | Full 61-turn forensic UI blob (C23 source of truth) |
| `alex_jan19_continuity_integrity.turns.yaml` | Compact turn index: exact user utterances + gate tags |

The web formatter that *produces* this blob is `apps/web/src/enigma/forensicDump.ts`. Do not treat that module as the dump.

Life Script that quotes the gate utterances: `packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml` ([C23](../../../../tickets/conversational-ui/C23-continuity-integrity-life-script.md)).
