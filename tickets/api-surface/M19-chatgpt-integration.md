# M19 — ChatGPT integration

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M19-chatgpt-integration` |
| Domain | `api-surface` |

## Package boundary (hard)

- May edit: reasoning provider adapter + api routes + minimal web UX
- Must not bypass privacy inspector / invariants

## Depends on

- M05, M17, M18

## Unlocks

- End-user remote reasoning UX

## Non-goals

- Fine-tuning on private data
- Uploading full mail/notes corpora

## Acceptance criteria

- [ ] ChatGPT (or OpenAI API) used only with sanitised transformed context
- [ ] User can run Enigma with remote inference disabled; Apple sources still work
- [ ] Privacy inspector preview before send (default on)
- [ ] Clear labelling of what left the machine

## Test plan

- Mock OpenAI tests
- Disabled-mode network guard
- End-to-end fixture → attention → sanitised prompt snapshot

## Privacy constraints

- Architectural acceptance: Apple services enrich the private model; they do not enlarge the remote model’s view of it
