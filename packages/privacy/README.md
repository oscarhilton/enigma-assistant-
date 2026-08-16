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

Forbidden: raw `PrivatePerson` fields, emails, phones, wholesale Notes bodies
(without an explicit `PolicyException`), and any non-allowlisted keys.

Source of truth: `personal_enigma.privacy.allowlist` (`REMOTE_PAYLOAD_ALLOWLIST_DOC`).

## Notes

Default level is **HIGH**. Marking a note remote-safe requires
`PolicyException`; wholesale bodies also need `allow_wholesale_note_body=True`.

## Remote inference disabled

`RemoteInferenceConfig(enabled=False)` (default) blocks transmission via
`may_send_remotely` even when a payload’s `may_transmit_remotely` bit is true,
so Apple ingestion / local transform remain testable without hosted calls.
