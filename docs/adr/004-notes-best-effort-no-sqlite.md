# ADR-004: Notes best-effort opt-in; no SQLite scraping

## Status

Accepted

## Context

Apple Notes lacks a first-class framework API comparable to EventKit/Contacts. Scraping Notes’ internal SQLite would be brittle and invasive.

## Decision

- Notes support is **macOS only**, **read-only**, **best-effort**, **explicit opt-in**.
- Access via Apple Events / AppleScript automation.
- Do **not** reverse-engineer or modify Notes SQLite databases.
- Default remote privacy level for Notes is **HIGH**; never transmit wholesale note bodies by default.
- Attachments, OCR, handwriting, audio, and rich formatting fidelity are out of MVP.

## Consequences

- Capability report marks Notes with `quality: "best_effort"`.
- Local relevance detection + passage extraction precede any remote reasoning (tickets M13, M14, M04).
