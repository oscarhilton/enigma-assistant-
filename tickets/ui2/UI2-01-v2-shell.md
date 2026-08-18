# UI2-01 — v2 shell + world switch + persistent Assistant + build identity + existing Goose

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/UI2-01-v2-shell` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/**` (create)
- May edit: `apps/web/src/components/ui/**` (create — shadcn primitives)
- May edit: `apps/web/src/lib/**` (create — cn utility)
- May edit: `apps/web/src/App.tsx`, `apps/web/src/App.test.tsx` (v2 route only)
- May edit: `apps/web/vite.config.ts` (build commit inject, `/worlds` proxy if needed)
- May edit: `apps/web/package.json`, `apps/web/tailwind.config.ts`, `apps/web/postcss.config.js`
- May edit: `tickets/ui2/**`, `tickets/README.md` (ui2 row)
- Minimal hooks into `apps/web/src/pilot/**` — reuse `WorldProvider`, `WorldSwitcher`, `PrivateWorldClient` patterns; do not fork semantics
- Must not edit: `packages/domain`, `apps/api` behaviour (except env for commit hash if already exists), P03 hardware proof worker paths, #89

## Hard depends

- P01 world isolation + pilot shell (`done`)
- C35 Goose pixel licence (`done`)

## Soft depends (~)

- UI2-02 streaming (non-streaming stub OK for this ticket)
- UI2-03 shadcn foundation (minimal Button/Input/ScrollArea/Separator OK here)

## Unlocks / enhances

- UI2-02 true streaming
- UI2-04 conversation continuity
- UI2-05 inspectability minimal
- UI2-06 Alex Life Scripts through v2

## Non-goals

- Mutating v1 pilot shell into v2
- Today dashboard, Cases workspace, Memory Explorer
- UI2-DEBUG full panel (stub route only)
- Streaming (UI2-02)
- Port v1 fossils wholesale

## Frozen spec (launchpad)

**North star:** Start familiar. Make it excellent. Let Enigma earn its uniqueness.

**Hard requirements:** Streaming (deferred UI2-02) · shadcn-style UI · Basically ChatGPT (sidebar, history placeholder, bottom composer, minimal chrome).

**Architecture:** v2 beside v1 at `/v2/*` · read-model driven · fossil policy.

## Acceptance criteria

- [x] v2 app shell at `/v2` route (React Router); v1 unchanged at `/`
- [x] Layout: sidebar (Chats placeholder), main conversation area, bottom composer, world switcher (reuse P01 `WorldProvider` / `PrivateWorldClient` patterns)
- [x] Goose in chrome (C35 — no changes to goose logic)
- [x] Build identity in footer/chrome: `Enigma v2 · {commit}` from env or build inject
- [x] shadcn init: `components/ui`, tailwind config; use Button, Input, ScrollArea, Separator minimally
- [x] Wire My Enigma conversation to `/worlds/my_enigma/conversation/message` — non-streaming OK for stub; composer + message list structured for streaming later
- [x] World switch remounts conversation state (ADR-040)
- [x] Vitest smoke: v2 shell renders, world switcher present, build identity

## Test plan

- Render `/v2` — shell, sidebar placeholder, composer, build identity
- World switcher present and functional (mock client in test mode)
- v1 `/` pilot shell still renders unchanged

## Privacy constraints

- Same world isolation as P01; no cross-world conversation leakage
