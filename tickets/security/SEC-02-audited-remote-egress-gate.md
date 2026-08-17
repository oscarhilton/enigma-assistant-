# SEC-02 — Single audited remote egress gate

**Status:** done  
**Branch:** `ticket/SEC02-audited-remote-egress-gate`  
**Domain:** security  
**May edit:** `packages/privacy/**`, `packages/reasoning/src/personal_enigma/reasoning/privacy_gate.py`, new `packages/privacy/.../egress_gate.py` (or `apps/api/.../egress/**`), `apps/api/src/personal_enigma/api/demo_orchestrator.py` (wire gate only), `apps/web` (disclosure UI), `apps/api/tests/**`, `packages/privacy/tests/**`, `packages/reasoning/tests/**`  
**Must not edit:** `packages/ingestion/.../sources/gmail.py`, attention policy weights, demo simulation sources

**Hard depends:** [SEC-01](./SEC-01-secrets-encrypted-storage.md) (disclosure record storage in encrypted `audit/`)  
**Soft (~):** [C09](../conversational-ui/C09-llm-conversational-boundary.md), [R03](../reasoning/R03-llm-judge.md) transport patterns

## Goal

Consolidate all **Private-mode remote inference** behind a **single audited egress gateway** that enforces **data classification**, allowlist, transformation, kill switch, safe logging, and per-request disclosure.

Only **REMOTE_SAFE** payloads may cross the boundary ([ADR-022](../../docs/adr/022-private-vault-storage.md)).

## Architectural rule

```text
handler / orchestrator
    ↓
transform (PrivateDerived → RemoteSafe if needed)
    ↓
egress_gate.submit(RemoteSafeContext, purpose, correlation_id)
    ├── classification guard — reject PrivateRaw / PrivateDerived at type boundary
    ├── assert_remote_safe / allowlist
    ├── may_send_remotely (global disable)
    ├── redacted audit log (ids · hashes · reason codes only)
    ├── disclosure record → encrypted audit/ store
    └── transport (Fireworks / OpenAI / …)
```

No direct provider transport calls from demo intents, orchestrator, or ingestion.

## Deliverables

### Classification enforcement

- [x] `RemoteSafeContext` type (name TBD) — sole accepted payload type for `egress_gate.submit()`
- [x] Runtime / static guard rejecting `PrivateRaw`, `PrivateDerived`, and unclassified dict payloads
- [x] Gate module is the **only** place where PRIVATE_* → wire conversion may occur (after transform)
- [x] Document mapping from [ADR-022 classification table](../../docs/adr/022-private-vault-storage.md#data-classification-model) to code types

### Egress gate module

- [x] `EgressGate` (name TBD) module — sole entry for remote LLM HTTP in Private / live paths
- [x] Reuse [`packages/privacy` allowlist](../../packages/privacy/README.md) and `may_send_remotely`
- [x] Wire C09 orchestrator live path through gate when `ENIGMA_DEMO_LLM_CONVERSATION=1` on Private roots
- [x] **Fireworks ZDR note:** gate rejects disallowed fields regardless of provider retention policy; document that ZDR is defence in depth only ([ADR-021](../../docs/adr/021-personal-data-security-boundary.md))
- [x] **Fireworks / raw body:** gate must block any payload containing PRIVATE_RAW fields — verified by test ([SEC-05 Q6](./SEC-05-personal-data-pilot-gate.md))

### "What left my machine?" disclosure

Per remote inference request, persist a **user-inspectable disclosure record** in encrypted `audit/` ([SEC-01](./SEC-01-secrets-encrypted-storage.md)):

| Field | Purpose |
| --- | --- |
| `correlation_id` | Tie to conversation / tool loop |
| `timestamp` | When bytes crossed boundary |
| `purpose` | e.g. `conversation.orchestrate`, `reasoning.semantic_judge` |
| `provider` | `openai`, `fireworks`, … |
| `payload_field_summary` | Allowlisted keys present (not raw content) |
| `transformation_profile` | e.g. `remote_safe_v1` |
| `payload_hash` | Falsifiable fingerprint of wire payload |
| `byte_count` | Approximate egress size |
| `blocked` | True if gate rejected |
| `classification` | Must be `REMOTE_SAFE` for successful egress |

- [x] API: `GET /private/disclosure/recent` (or equivalent) for last N egress events
- [ ] Web UI panel: **"What left my machine?"** — list recent disclosures with expand for field summary (no raw private text on screen by default)
- [x] Demo Mode may use stub disclosure store; Private pilot requires real records

## Acceptance criteria

- [x] Grep shows zero Private-path `FireworksChatTransport` / OpenAI client instantiation outside gate module
- [x] Attempt to submit raw email body / `PrivateRaw` payload → gate **blocks** with auditable reason
- [x] Attempt to submit embedding vector / `PrivateDerived` payload without transform → gate **blocks**
- [x] `RemoteInferenceConfig(enabled=False)` → gate returns blocked disclosure row; no HTTP
- [x] Each successful inference creates exactly one disclosure record retrievable via API
- [ ] UI shows at least provider, timestamp, purpose, payload hash, field summary
- [x] Logs contain correlation id + purpose + reason codes — not full wire payload, bodies, or tokens
- [x] No Fireworks/OpenAI request in test captures contains raw email body bytes

## Test plan

- Unit tests: classification reject, allowlist reject, kill switch, hash stability
- Integration: orchestrator mock transport through gate with `RemoteSafeContext` only
- Regression: privacy CI invariants still pass
- Negative: inject `PrivateRaw` fixture at gate boundary → blocked + disclosure row

## Privacy constraints

- Disclosure records describe **what crossed the boundary** — they must not duplicate raw private content
- Align with outbound disclosure discipline in [ADR-018](../../docs/adr/018-disclosure-ledger-and-inference-attack-protection.md) (local ledger; different counterparty model)

**Unlocks:** SEC-03 (egress assertions), SEC-04, SEC-05

## Related ADR

[ADR-021](../../docs/adr/021-personal-data-security-boundary.md) · [ADR-022](../../docs/adr/022-private-vault-storage.md)

## Implementation notes

- Module: `packages/privacy/src/personal_enigma/privacy/egress/` (`AuditedEgressGate`, `RemoteSafeContext`, `PrivateRaw`, `PrivateDerived`, `assert_remote_safe`, `EgressDisclosure`)
- Provider HTTP: `egress/providers/openai.py`, `egress/providers/fireworks.py` (+ gate-internal `execute_fireworks_completion` in reasoning)
- Migrated call sites: `demo_orchestrator.OpenAIConversationLLM`, `PaygReasoningService`, `OpenAIChatTransport`, `FireworksChatTransport`, `apps/api/routes/external/chat.py`
- Disclosure API: `GET /private/disclosure/recent` in `apps/api/src/personal_enigma/api/routes/disclosure.py`
- Tests: `packages/privacy/tests/test_egress_gate.py`, `test_egress_disclosure.py`, `test_egress_no_bypass.py`
