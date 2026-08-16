/** Demo Mode API client + offline fixtures for UI (D10). */

export type DemoStatus = {
  active: boolean;
  mode: string;
  banner: string;
  scenario: string | null;
  simulated_time: string | null;
  speed: number | null;
  paused: boolean | null;
  storage_root: string | null;
  ground_truth_visible?: boolean;
};

export type DemoAttentionItem = {
  id: string;
  title: string;
  body: string;
  kind: string;
  score: number;
  reason_codes: string[];
};

export type DemoMemoryItem = {
  id: string;
  category: string;
  statement: string;
  confidence: number;
  evidence_count: number;
  first_observed: string;
  last_observed: string;
};

export type DemoWhyPayload = {
  item_id: string;
  title: string;
  headline: string;
  evidence: string[];
  inference: string[];
  decision: string[];
  reason_codes: string[];
};

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export const FIXTURE_STATUS: DemoStatus = {
  active: true,
  mode: "demo",
  banner: "DEMO MODE — FICTIONAL DATA ONLY",
  scenario: "alex-v1",
  simulated_time: "2026-01-01T09:00:00+00:00",
  speed: 1,
  paused: false,
  storage_root: "/tmp/enigma-demo/alex-v1",
  ground_truth_visible: false,
};

export const FIXTURE_DEMO_STATUS = FIXTURE_STATUS;

export const FIXTURE_ATTENTION: DemoAttentionItem[] = [
  {
    id: "att-atlas-review",
    title: "Review Atlas proposal before Friday",
    body: "Open loop from a prior commitment; deadline approaching.",
    kind: "commitment",
    score: 0.91,
    reason_codes: ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
  },
  {
    id: "att-follow-up",
    title: "Follow up with PERSON_A on scheduling",
    body: "Cross-source thread still unresolved.",
    kind: "follow_up",
    score: 0.72,
    reason_codes: ["FOLLOW_UP_RECEIVED"],
  },
];

export const FIXTURE_MEMORY: DemoMemoryItem[] = [
  {
    id: "mem-person-a",
    category: "People",
    statement: "PERSON_A is probably important at work.",
    confidence: 0.86,
    evidence_count: 4,
    first_observed: "2026-01-10T09:00:00+00:00",
    last_observed: "2026-02-15T16:00:00+00:00",
  },
  {
    id: "mem-atlas",
    category: "Projects",
    statement: "PROJECT_B (Atlas) has an active review commitment.",
    confidence: 0.78,
    evidence_count: 3,
    first_observed: "2026-01-28T11:00:00+00:00",
    last_observed: "2026-03-01T10:00:00+00:00",
  },
  {
    id: "mem-open-loop",
    category: "Open loops",
    statement: "USER committed to review PROJECT_B before Friday.",
    confidence: 0.9,
    evidence_count: 2,
    first_observed: "2026-03-14T09:03:00+00:00",
    last_observed: "2026-03-14T11:12:00+00:00",
  },
];

export const FIXTURE_WHY: DemoWhyPayload = {
  item_id: "att-atlas-review",
  title: "Review Atlas proposal before Friday",
  headline: "WHY ENIGMA THINKS THIS MATTERS",
  evidence: [
    "Email: PERSON_A requested review.",
    "Email: USER said they would review before Friday.",
    "Calendar: Review meeting Friday 15:00.",
  ],
  inference: ["An unresolved commitment exists."],
  decision: ["Deadline approaching within useful action window.", "Priority score: 0.91"],
  reason_codes: ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
};

export const FIXTURE_WHY_BY_ID: Record<string, DemoWhyPayload> = {
  "att-atlas-review": FIXTURE_WHY,
  "att-follow-up": {
    item_id: "att-follow-up",
    title: "Follow up with PERSON_A on scheduling",
    headline: "WHY ENIGMA THINKS THIS MATTERS",
    evidence: ["Cross-source thread still unresolved."],
    inference: ["A follow-up remains open."],
    decision: ["Surfaced at moderate priority."],
    reason_codes: ["FOLLOW_UP_RECEIVED"],
  },
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

function advanceIso(iso: string, days: number, hours = 0): string {
  const current = new Date(iso);
  current.setUTCDate(current.getUTCDate() + days);
  current.setUTCHours(current.getUTCHours() + hours);
  return current.toISOString().replace(".000Z", "+00:00");
}

export async function fetchDemoStatus(fetchImpl: typeof fetch = fetch): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(await fetchImpl(`${API_BASE}/demo/status`));
  } catch {
    return structuredClone(FIXTURE_STATUS);
  }
}

export async function advanceDemoDay(fetchImpl: typeof fetch = fetch): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(
      await fetchImpl(`${API_BASE}/demo/timeline/day`, { method: "POST" }),
    );
  } catch {
    const next = structuredClone(FIXTURE_STATUS);
    next.simulated_time = advanceIso(FIXTURE_STATUS.simulated_time ?? "2026-01-01T09:00:00Z", 1);
    return next;
  }
}

export async function advanceDemoStep(fetchImpl: typeof fetch = fetch): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(
      await fetchImpl(`${API_BASE}/demo/timeline/step`, { method: "POST" }),
    );
  } catch {
    const next = structuredClone(FIXTURE_STATUS);
    next.simulated_time = advanceIso(
      FIXTURE_STATUS.simulated_time ?? "2026-01-01T09:00:00Z",
      0,
      1,
    );
    return next;
  }
}

export async function setDemoSpeed(
  speed: number,
  fetchImpl: typeof fetch = fetch,
): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(
      await fetchImpl(`${API_BASE}/demo/timeline/speed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speed }),
      }),
    );
  } catch {
    const next = structuredClone(FIXTURE_STATUS);
    next.speed = speed;
    next.paused = speed === 0;
    return next;
  }
}

export async function fetchDemoAttention(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoAttentionItem[]> {
  try {
    const body = await readJson<{ items: DemoAttentionItem[] }>(
      await fetchImpl(`${API_BASE}/demo/attention`),
    );
    return body.items;
  } catch {
    return structuredClone(FIXTURE_ATTENTION);
  }
}

export async function fetchDemoMemory(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoMemoryItem[]> {
  try {
    const body = await readJson<{ items: DemoMemoryItem[] }>(
      await fetchImpl(`${API_BASE}/demo/memory`),
    );
    return body.items;
  } catch {
    return structuredClone(FIXTURE_MEMORY);
  }
}

export async function fetchDemoWhy(
  itemId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<DemoWhyPayload | null> {
  try {
    return await readJson<DemoWhyPayload>(await fetchImpl(`${API_BASE}/demo/why/${itemId}`));
  } catch {
    return structuredClone(FIXTURE_WHY_BY_ID[itemId] ?? null);
  }
}
