import type { DemoAttentionItem, DemoNextAction } from "./types";

/** Demo stubs — always optional; never HIGH PRIORITY Attention. */
export const FIXTURE_NEXT_ACTIONS: DemoNextAction[] = [
  {
    id: "next-walk",
    title: "Go for a short walk",
    duration_label: "~15 min",
    reason: "You've got a clear hour before your next commitment.",
    category: "movement",
    optional: true,
  },
  {
    id: "next-junk-mail",
    title: "Clear a few junk / newsletter messages",
    duration_label: "~10 min",
    reason: "A small tidy pass — nothing here needs you urgently.",
    category: "maintenance",
    optional: true,
  },
  {
    id: "next-open-loop",
    title: "Close one small open loop",
    duration_label: "~5 min",
    reason: "Pick something tiny you can finish without opening a new thread.",
    category: "open_loop",
    optional: true,
  },
  {
    id: "next-rest",
    title: "Do nothing with this gap",
    duration_label: "~15 min",
    reason: "Rest is a legitimate option — you do not have to optimise this hour.",
    category: "rest",
    optional: true,
  },
];

/** Shorten attention titles for NEXT line (not a second card). */
export function nextTitleFromAttention(item: DemoAttentionItem): string {
  let title = item.title.trim();
  title = title.replace(/\s+before\s+.+$/i, "");
  title = title.replace(/\s+by\s+.+$/i, "");
  if (/^review\s+/i.test(title) && !/^review the\s+/i.test(title)) {
    title = title.replace(/^review\s+/i, "Review the ");
  }
  return title.trim() || item.title.trim();
}

export function durationFromAttention(item: DemoAttentionItem): string {
  if (item.priority >= 4) {
    return "~20 min";
  }
  if (item.kind === "follow_up") {
    return "~10 min";
  }
  return "~15 min";
}

/** Derive a NEXT suggestion from the top attention item when attention is non-empty. */
export function nextActionFromAttention(item: DemoAttentionItem): DemoNextAction {
  return {
    id: `next-from-${item.id}`,
    title: nextTitleFromAttention(item),
    duration_label: durationFromAttention(item),
    reason: "A useful next step on what already needs you — optional, not another alert.",
    category: "obligation",
    optional: true,
  };
}

export function nextActionLine(action: DemoNextAction): string {
  return `${action.title} · ${action.duration_label}`;
}

export function nextSectionLabel(attentionEmpty: boolean): string {
  return attentionEmpty ? "YOU COULD" : "NEXT";
}

/**
 * Resolve the candidate list for cycling.
 * When attention has items, lead with a derived obligation NEXT, then soft stubs.
 */
export function resolveNextActionCandidates(
  items: DemoAttentionItem[],
  fromPayload?: DemoNextAction[] | null,
): DemoNextAction[] {
  const stubs =
    fromPayload && fromPayload.length > 0
      ? fromPayload.filter((a) => a.optional)
      : FIXTURE_NEXT_ACTIONS;

  if (items.length > 0) {
    const top = [...items].sort((a, b) => b.attention_rank - a.attention_rank)[0]!;
    const derived = nextActionFromAttention(top);
    const rest = stubs.filter((a) => a.category !== "obligation");
    return [derived, ...rest];
  }

  // Empty attention: soft candidates only — must include rest.
  const soft = stubs.filter((a) => a.category !== "obligation");
  const hasRest = soft.some((a) => a.category === "rest");
  if (!hasRest) {
    const restStub = FIXTURE_NEXT_ACTIONS.find((a) => a.category === "rest");
    return restStub ? [...soft, restStub] : soft;
  }
  return soft.length > 0 ? soft : FIXTURE_NEXT_ACTIONS;
}

export function cycleNextIndex(current: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return (current + 1) % total;
}
