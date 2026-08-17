# M21 — Chat message schemas

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M21-chat-message-schemas` |
| Domain | `domain-model` |

## Package boundary (hard)

- May edit: `packages/domain/**`, `packages/privacy/src/personal_enigma/privacy/levels.py`, `packages/privacy/tests/test_levels.py`, `packages/privacy/src/personal_enigma/privacy/inspector.py`, `packages/identity/**` (phone on `PrivatePersonRef`), `docs/adr/003-source-type-vs-provider.md`, `docs/architecture/privacy-model.md`, `docs/architecture/overview.md`
- Must not edit: ingestion `sources/*.py`, simulation adapters (D19), alex-v1 timeline (D08f)

## Hard depends

- M01

## Soft depends (~)

- None

## Goal

Canonical chat evidence distinct from Gmail-shaped `PrivateMessage`. WhatsApp is a provider of `CHAT_MESSAGE`, not a mail subtype.

## Acceptance criteria

- [x] `SourceType.CHAT_MESSAGE`
- [x] `PrivateChatMessage` + `ChatEvidence`
- [x] Optional `phone` on `PrivatePersonRef`
- [x] Chat defaults to `PrivacyLevel.VERY_HIGH`
- [x] Round-trip tests; no WhatsApp wire types in domain

## Privacy constraints

- Chat bodies are PRIVATE_RAW. Domain models are local-only.
- Identity may unify on phone; remote payloads still use `PERSON_*` only.
