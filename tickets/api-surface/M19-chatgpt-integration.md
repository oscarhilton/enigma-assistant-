# M19 — ChatGPT integration

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M19-chatgpt-integration` |
| Domain | `api-surface` |

## Package boundary (hard)

- May edit: `packages/reasoning/src/**/openai*` or equivalent adapter under `packages/reasoning`
- May edit: `apps/api/src/personal_enigma/api/routes/external/chat/**` (create)
- May edit: `apps/web/src/pages/Chat*` / `apps/web/src/chat/**` (create) for minimal UX
- Must not bypass privacy inspector / M04 invariants
- Must not edit: apple-bridge, ingestion sources

## Hard depends

- M05, M17, M18

## Soft depends (~)

- None

## Unlocks / enhances

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
