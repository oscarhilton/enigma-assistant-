import type {
  CanWaitCategoryId,
  CanWaitGroup,
  DemoAttentionItem,
  DemoSuppressedItem,
  DemoSuppressionReason,
} from "./types";

/** Source-prefixed evidence narrative from obligations merge — not product copy. */
const EVIDENCE_PREFIX =
  /^(Reminder|Email|Calendar|Note):\s/i;
const EVIDENCE_SEGMENT =
  /;\s*(Reminder|Email|Calendar|Note):\s/i;

const TERSE_GLANCE =
  /^(deadline approaching|thread waiting on you|open reminder|on your calendar|thread or follow-up|open loop)$/i;

export const CAN_WAIT_CATEGORY_LABELS: Record<CanWaitCategoryId, string> = {
  upcoming_calendar: "Upcoming calendar",
  open_threads: "Open threads",
  informational: "Informational",
  automated_noise: "Automated / noise",
};

export function isEvidenceDumpBody(body: string | null | undefined): boolean {
  if (!body?.trim()) {
    return false;
  }
  const text = body.trim();
  return EVIDENCE_PREFIX.test(text) || EVIDENCE_SEGMENT.test(text);
}

function withSentenceEnd(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return trimmed;
  }
  return /[.!?]$/.test(trimmed) ? trimmed : `${trimmed}.`;
}

function personFromTitle(title: string): string | null {
  const withMatch = title.match(/\bwith\s+([A-Z][a-z]+)\b/);
  if (withMatch?.[1]) {
    return withMatch[1];
  }
  const possessive = title.match(/\b([A-Z][a-z]+)'s\b/);
  if (possessive?.[1]) {
    return possessive[1];
  }
  return null;
}

/** Derive one natural face sentence from obligation / deadline fields. */
export function deriveNaturalReason(item: DemoAttentionItem): string | null {
  const when = item.when?.trim() ?? "";
  const whenLower = when.toLowerCase();
  const title = item.title.trim();
  const person = personFromTitle(title);

  if (
    when &&
    (/before |due |friday|today|tomorrow|deadline/i.test(when) ||
      item.priority >= 4)
  ) {
    const deadlinePhrase = whenLower.startsWith("before ")
      ? whenLower
      : whenLower.startsWith("due ")
        ? when.replace(/^due\s+/i, "by ").toLowerCase()
        : `before ${whenLower}`;
    const verb = /review/i.test(title) ? "review" : "finish";
    return `You said you'd ${verb} this ${deadlinePhrase}, and it still appears unfinished.`;
  }

  if (
    person &&
    (/follow|schedul|waiting|reply|thread/i.test(title) ||
      /waiting|thread|follow/i.test(item.why_now_glance ?? "") ||
      item.kind === "follow_up")
  ) {
    return `${person} is still waiting for a scheduling response.`;
  }

  if (when) {
    return withSentenceEnd(when);
  }
  return null;
}

/**
 * One short natural sentence for the card face — never the evidence dump,
 * never terse internal glances like "Deadline approaching".
 */
export function cardReason(item: DemoAttentionItem): string | null {
  const body = item.body?.trim();
  if (body && !isEvidenceDumpBody(body)) {
    return withSentenceEnd(body);
  }

  const derived = deriveNaturalReason(item);
  if (derived) {
    return withSentenceEnd(derived);
  }

  const glance = item.why_now_glance?.trim();
  if (glance && !TERSE_GLANCE.test(glance)) {
    return withSentenceEnd(glance);
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
  const body = item.body?.toLowerCase() ?? "";
  const haystack = `${glance} ${when} ${body}`;
  if (
    /deadline|due soon|approaching|before |today|tomorrow|overdue|urgent|unfinished/.test(
      haystack,
    )
  ) {
    return "DUE SOON";
  }
  // Freeform `when` belongs in cardReason, not the compact badge row.
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
    return "1 thing needs your attention";
  }
  return `${count} things need your attention`;
}

export function canWaitLabel(suppressed: number): string {
  if (suppressed === 1) {
    return "Show 1 that can wait";
  }
  return `Show ${suppressed} that can wait`;
}

export function holdingSignalsNote(suppressed: number): string {
  if (suppressed === 1) {
    return "Enigma is holding 1 lower-priority signal out of view so you can focus on what matters now.";
  }
  return `Enigma is holding ${suppressed} lower-priority signals out of view so you can focus on what matters now.`;
}

export function lastEvaluatedLabel(
  evaluatedAtMs: number,
  nowMs: number = Date.now(),
): string {
  const deltaSec = Math.max(0, Math.floor((nowMs - evaluatedAtMs) / 1000));
  if (deltaSec < 45) {
    return "Last evaluated just now";
  }
  const minutes = Math.max(1, Math.round(deltaSec / 60));
  if (minutes === 1) {
    return "Last evaluated 1 minute ago";
  }
  if (minutes < 60) {
    return `Last evaluated ${minutes} minutes ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours === 1) {
    return "Last evaluated 1 hour ago";
  }
  return `Last evaluated ${hours} hours ago`;
}

function categoryFromSuppression(
  reason: DemoSuppressionReason,
  classification: string,
): CanWaitCategoryId {
  if (reason === "newsletter" || classification === "informational") {
    return "informational";
  }
  if (reason === "spam" || reason === "background" || classification === "unsolicited") {
    return "automated_noise";
  }
  if (reason === "duplicate" || reason === "low_priority") {
    return "open_threads";
  }
  if (reason === "resolved") {
    return "upcoming_calendar";
  }
  return "informational";
}

/** Best-effort map of suppressed stubs → secondary can-wait buckets. */
export function groupCanWaitFromSuppressed(
  items: DemoSuppressedItem[],
  suppressedTotal: number,
): CanWaitGroup[] {
  const counts: Record<CanWaitCategoryId, number> = {
    upcoming_calendar: 0,
    open_threads: 0,
    informational: 0,
    automated_noise: 0,
  };

  for (const item of items) {
    const id =
      item.can_wait_category ??
      categoryFromSuppression(item.suppression_reason, item.classification);
    counts[id] += 1;
  }

  const sampled = Object.values(counts).reduce((sum, n) => sum + n, 0);
  if (sampled === 0 && suppressedTotal > 0) {
    return defaultCanWaitGroups(suppressedTotal);
  }

  if (sampled > 0 && sampled < suppressedTotal) {
    // Scale sample proportions to the known suppressed total.
    const ids = Object.keys(counts) as CanWaitCategoryId[];
    let assigned = 0;
    for (let i = 0; i < ids.length; i += 1) {
      const id = ids[i]!;
      if (i === ids.length - 1) {
        counts[id] = Math.max(0, suppressedTotal - assigned);
      } else {
        const scaled = Math.round((counts[id] / sampled) * suppressedTotal);
        counts[id] = scaled;
        assigned += scaled;
      }
    }
  }

  return (Object.keys(CAN_WAIT_CATEGORY_LABELS) as CanWaitCategoryId[])
    .map((id) => ({
      id,
      label: CAN_WAIT_CATEGORY_LABELS[id],
      count: counts[id],
    }))
    .filter((group) => group.count > 0);
}

/** Deterministic demo buckets when only a suppressed count is known. */
export function defaultCanWaitGroups(suppressed: number): CanWaitGroup[] {
  if (suppressed <= 0) {
    return [];
  }
  const upcoming = Math.max(1, Math.round(suppressed * 0.26));
  const threads = Math.max(1, Math.round(suppressed * 0.17));
  const info = Math.max(1, Math.round(suppressed * 0.32));
  const noise = Math.max(0, suppressed - upcoming - threads - info);
  const groups: CanWaitGroup[] = [
    { id: "upcoming_calendar", label: CAN_WAIT_CATEGORY_LABELS.upcoming_calendar, count: upcoming },
    { id: "open_threads", label: CAN_WAIT_CATEGORY_LABELS.open_threads, count: threads },
    { id: "informational", label: CAN_WAIT_CATEGORY_LABELS.informational, count: info },
    {
      id: "automated_noise",
      label: CAN_WAIT_CATEGORY_LABELS.automated_noise,
      count: noise,
    },
  ];
  return groups.filter((group) => group.count > 0);
}

export function resolveCanWaitGroups(
  suppressed: number,
  groups?: CanWaitGroup[] | null,
  suppressedItems?: DemoSuppressedItem[] | null,
): CanWaitGroup[] {
  if (groups && groups.length > 0) {
    return groups.filter((group) => group.count > 0);
  }
  if (suppressedItems && suppressedItems.length > 0) {
    return groupCanWaitFromSuppressed(suppressedItems, suppressed);
  }
  return defaultCanWaitGroups(suppressed);
}
