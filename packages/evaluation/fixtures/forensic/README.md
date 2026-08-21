# Forensic dumps (Demo Alex)

These files are **Demo Mode** captures (persona Alex Morgan / `alex_v1`). They are not a private-world recording.

| File | What |
| --- | --- |
| `alex_jan19_continuity_integrity.dump.txt` | Full 61-turn forensic UI blob (C23 source of truth) |
| `alex_jan19_continuity_integrity.turns.yaml` | Compact turn index: exact user utterances + gate tags |
| `alex_jan19_brunch_details_regression.trace.yaml` | Brunch details regression trace (C15/C21/C20/C22; outside C23 gate) |
| `alex_jan17_coverage_regression` (script) | 14-turn coverage session — calendar-only vs catch-up (C25) |
| `alex_brunch_token_goose_forensic.dump.txt` | 12-turn brunch / token / Goose dump (C33; BUILD UNKNOWN — not a current-main bug report) |
| `alex_brunch_token_goose_forensic.turns.yaml` | Compact utterance index + named freeze cases |
| `alex_brunch_token_goose_forensic.bootstrap.yaml` | Relational bootstrap sketch (ADR-038; not a C09 payload) |

The web formatter that *produces* this blob is `apps/web/src/enigma/forensicDump.ts`. Do not treat that module as the dump.

Life Script that quotes the gate utterances: `packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml` ([C23](../../../../tickets/conversational-ui/C23-continuity-integrity-life-script.md)).

Brunch details regression script: `packages/evaluation/scripts/alex_jan19_brunch_details_regression.script.yaml`.

Coverage regression script (Jan 17 14-turn dump): `packages/evaluation/scripts/alex_jan17_coverage_regression.script.yaml` ([C25](../../../../tickets/conversational-ui/C25-evidence-coverage-bundle.md)).
