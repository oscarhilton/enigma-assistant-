# ADR-002: Local-only Apple Bridge transport and auth

## Status

Accepted

## Context

The Apple Bridge translates Apple-native data into Enigma’s canonical model. It must never become an internet-facing API.

## Decision

- Prefer a **Unix domain socket**; otherwise bind **`127.0.0.1` only** — never `0.0.0.0`.
- Require `Authorization: Bearer <local-secret>` even for localhost.
- Generate the secret in Enigma Core at install time; store it in **macOS Keychain**.
- Bridge does not call LLM providers.

## Consequences

- Core is the only intended client.
- Later work can drop TCP entirely in favour of the Unix socket (ticket M07).
