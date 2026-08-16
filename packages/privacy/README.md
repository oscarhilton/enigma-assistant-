# packages/privacy

Privacy levels, remote-payload allowlist, and CI invariant gates.

## Governing rule

> Select first → transform second → transmit last.

## Remote payload allowlist

Only these top-level keys may appear on the wire to a hosted model:

| Key | Notes |
| --- | --- |
| `summary` | Sanitised text; `PERSON_*` tokens OK |
| `entities` | Opaque `PERSON_*` IDs only |
| `metadata` | Subset in `REMOTE_METADATA_KEYS` |
| `may_transmit_remotely` | Still requires remote inference enabled |

Forbidden: raw `PrivatePerson` fields, emails, phones, wholesale Notes bodies,
and any non-allowlisted keys. Notes may only become remote-safe via an explicit
`NotesRemotePolicyException` (passage-only; never wholesale).

Source of truth: `personal_enigma.privacy.allowlist` (`REMOTE_PAYLOAD_ALLOWLIST_DOC`).

## Notes

Default level is **HIGH**. Wholesale note bodies cannot be marked remote-safe;
`NotesRemotePolicyException` authorises passages only.

## Remote inference disabled

`RemoteInferenceConfig(enabled=False)` (default) blocks transmission via
`may_send_remotely` even when a payload’s `may_transmit_remotely` bit is true,
so Apple ingestion / local transform remain testable without hosted calls.
