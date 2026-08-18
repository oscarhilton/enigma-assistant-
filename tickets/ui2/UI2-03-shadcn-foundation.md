# UI2-03 — shadcn component foundation

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/UI2-03-shadcn-foundation` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/components/ui/**`
- May edit: `apps/web/src/lib/**`
- May edit: `apps/web/tailwind.config.ts`, `apps/web/src/v2/v2.css`
- Must not edit: v1 `styles.css` beyond shared tokens if needed

## Hard depends

- UI2-01 minimal shadcn bootstrap

## Frozen spec (launchpad)

**shadcn-style UI** — restrained primitives, typography, spacing.

## Acceptance criteria

- [ ] Full shadcn-style token set (radius, colours, typography scale)
- [ ] Core primitives: Button, Input, Textarea, ScrollArea, Separator, Sheet, Dialog, Tooltip
- [ ] Dark mode ready (class strategy)
- [ ] v2 shell uses primitives exclusively (no ad-hoc v2 CSS for covered cases)

## Test plan

- Storybook or vitest smoke per primitive
- Visual regression not required for v2 launchpad

## Privacy constraints

- N/A (presentation only)
