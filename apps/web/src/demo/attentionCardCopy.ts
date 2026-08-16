import type { DemoAttentionItem } from "./types";

/** Source-prefixed evidence narrative from obligations merge — not product copy. */
const EVIDENCE_PREFIX =
  /^(Reminder|Email|Calendar|Note):\s/i;
const EVIDENCE_SEGMENT =
  /;\s*(Reminder|Email|Calendar|Note):\s/i;

export function isEvidenceDumpBody(body: string | null | undefined): boolean {
  if (!body?.trim()) {
    return false;
  }
  const text = body.trim();
  return EVIDENCE_PREFIX.test(text) || EVIDENCE_SEGMENT.test(text);
}

/** One short sentence for the card face — never the evidence dump. */
export function cardReason(item: DemoAttentionItem): string | null {
  const glance = item.why_now_glance?.trim();
  if (glance) {
    return glance.endsWith(".") ? glance : `${glance}.`;
  }
  const body = item.body?.trim();
  if (body && !isEvidenceDumpBody(body)) {
    return body;
  }
  const when = item.when?.trim();
  if (when) {
    return when.endsWith(".") ? when : `${when}.`;
  }
  return null;
}

export function priorityLabel(priority: number): string | null {
  if (priority >= 4) {
    return "HIGH PRIORITY";
  }
  if (priority === 3) {
    return "MEDIUM";
  }
  if (priority >= 1) {
    return "LOW";
  }
  return null;
}

export function timingLabel(item: DemoAttentionItem): string | null {
  const glance = item.why_now_glance?.toLowerCase() ?? "";
  const when = item.when?.toLowerCase() ?? "";
  const haystack = `${glance} ${when}`;
  if (
    /deadline|due soon|approaching|before |today|tomorrow|overdue|urgent/.test(
      haystack,
    )
  ) {
    return "DUE SOON";
  }
  if (item.when?.trim()) {
    return item.when.trim().toUpperCase();
  }
  return null;
}

export function compactBadges(item: DemoAttentionItem): string[] {
  return [priorityLabel(item.priority), timingLabel(item)].filter(
    (label): label is string => Boolean(label),
  );
}

export function mattersNowHeadline(count: number): string {
  if (count <= 0) {
    return "Nothing needs you right now";
  }
  if (count === 1) {
    return "1 thing matters now";
  }
  return `${count} things matter now`;
}

export function canWaitLabel(suppressed: number): string {
  if (suppressed === 1) {
    return "Show 1 that can wait";
  }
  return `Show ${suppressed} that can wait`;
}
