# Milestone → ticket map

Revised MVP order. Each milestone is a ticket under `tickets/<domain>/`.

Platform tickets (M00*) were added after the ticket-system review to own persistence and settings so agents do not dump those concerns into unrelated PRs.

| # | Milestone | Ticket |
| --- | --- | --- |
| 00a | Private persistence | [tickets/platform/M00a-persistence.md](../../tickets/platform/M00a-persistence.md) |
| 00b | Settings / calendar selection | [tickets/platform/M00b-settings.md](../../tickets/platform/M00b-settings.md) |
| 01 | Core schemas | [tickets/domain-model/M01-core-schemas.md](../../tickets/domain-model/M01-core-schemas.md) |
| 02 | Synthetic fixture pipeline | [tickets/fixtures/M02-synthetic-fixture-pipeline.md](../../tickets/fixtures/M02-synthetic-fixture-pipeline.md) |
| 03 | Enigma transformation | [tickets/transformation/M03-enigma-transformation.md](../../tickets/transformation/M03-enigma-transformation.md) |
| 04 | Privacy invariant tests | [tickets/privacy/M04-privacy-invariant-tests.md](../../tickets/privacy/M04-privacy-invariant-tests.md) |
| 05 | PAYG reasoning provider | [tickets/reasoning/M05-payg-reasoning-provider.md](../../tickets/reasoning/M05-payg-reasoning-provider.md) |
| 06 | Attention engine | [tickets/attention/M06-attention-engine.md](../../tickets/attention/M06-attention-engine.md) |
| 07 | macOS Apple Bridge shell | [tickets/apple-bridge/M07-bridge-shell.md](../../tickets/apple-bridge/M07-bridge-shell.md) |
| 08 | Apple Calendar | [tickets/apple-bridge/M08-apple-calendar.md](../../tickets/apple-bridge/M08-apple-calendar.md) |
| 09 | Apple Reminders | [tickets/apple-bridge/M09-apple-reminders.md](../../tickets/apple-bridge/M09-apple-reminders.md) |
| 10 | Apple Contacts / entity resolution | [tickets/apple-bridge/M10-apple-contacts.md](../../tickets/apple-bridge/M10-apple-contacts.md) |
| 11 | Gmail | [tickets/google/M11-gmail.md](../../tickets/google/M11-gmail.md) |
| 12 | Google Calendar | [tickets/google/M12-google-calendar.md](../../tickets/google/M12-google-calendar.md) |
| 13 | Apple Notes experimental adapter | [tickets/apple-bridge/M13-apple-notes.md](../../tickets/apple-bridge/M13-apple-notes.md) |
| 14 | Local embedding / retrieval | [tickets/retrieval/M14-local-embeddings.md](../../tickets/retrieval/M14-local-embeddings.md) |
| 15 | Cross-source obligation merging | [tickets/obligations/M15-cross-source-merging.md](../../tickets/obligations/M15-cross-source-merging.md) |
| 16 | Commitment tracking | [tickets/obligations/M16-commitment-tracking.md](../../tickets/obligations/M16-commitment-tracking.md) |
| 17 | Privacy inspector | [tickets/privacy/M17-privacy-inspector.md](../../tickets/privacy/M17-privacy-inspector.md) |
| 18 | External sanitised API | [tickets/api-surface/M18-external-sanitised-api.md](../../tickets/api-surface/M18-external-sanitised-api.md) |
| 19 | ChatGPT integration | [tickets/api-surface/M19-chatgpt-integration.md](../../tickets/api-surface/M19-chatgpt-integration.md) |

## Suggested waves

0. M01 (domain exclusive)
1. M02 ∥ M07 ∥ M00b
2. M03 → M04; M06; M00a after M01
3. M08 ∥ M09 ∥ M10 (pinned ingestion files)
4. M11 ∥ M12 ∥ M13; M05 ∥ M17
5. M14 → M15 → M16
6. M18 → M19

Apple-first ordering means Enigma can become useful on a Mac before every cloud connector lands.
