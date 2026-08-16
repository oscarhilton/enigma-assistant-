# Apple Bridge

Preferred architecture:

```text
                       macOS

┌────────────────────────────────────────────────────────────┐
│                    ENIGMA APPLE BRIDGE                     │
│   Calendar ───────── EventKit                              │
│   Reminders ──────── EventKit                              │
│   Contacts ───────── Contacts.framework                    │
│   Notes ──────────── Notes automation (Apple Events)       │
│                          ▼                                 │
│                   canonical events                         │
└──────────────────────────┼─────────────────────────────────┘
                           │ localhost / Unix socket
                           ▼
                 ENIGMA CORE (FastAPI)
```

## Why native?

Use Apple’s supported OS interfaces rather than poking undocumented databases:

- normal macOS privacy prompts
- calendars configured on the Mac (any provider)
- clearer permission / revocation
- less breakage on OS updates

The bridge contains **no reasoning logic**.

## Transport and auth

- Prefer Unix domain socket; otherwise bind `127.0.0.1` only — never `0.0.0.0`
- Authenticate even on localhost (`Authorization: Bearer <local-secret>`)
- At install time, Core generates a bridge token stored in macOS Keychain

Possible API surface:

```text
GET /capabilities
GET /calendar/changes
GET /reminders/changes
GET /contacts/changes
GET /notes/changes
```

## Capability discovery

```json
{
  "calendar": { "available": true, "authorised": true },
  "reminders": { "available": true, "authorised": true },
  "contacts": { "available": true, "authorised": true },
  "notes": {
    "available": true,
    "authorised": false,
    "quality": "best_effort"
  }
}
```

Enigma must not assume every Apple source exists. Permissions are individually revocable; Core continues when some are disabled.

## Notes quality

Notes is a **different quality of integration**: macOS only, read-only, best-effort, explicit opt-in, via Apple Events / AppleScript — never by reverse-engineering Notes SQLite.

Scaffold: [`apps/apple-bridge`](../../apps/apple-bridge).
