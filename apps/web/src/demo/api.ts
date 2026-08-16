/** Demo Mode API client + offline fixtures for UI (D10 / D13). */

import type {
  DemoAttentionActionResult,
  DemoAttentionItem,
  DemoAttentionPayload,
  DemoMemoryItem,
  DemoStatus,
  DemoSuppressedPayload,
  DemoSuppressionReason,
  DemoWhyPayload,
} from "./types";
import {
  FIXTURE_ATTENTION,
  FIXTURE_ATTENTION_PAYLOAD,
  FIXTURE_DEMO_STATUS,
  FIXTURE_MEMORY,
  FIXTURE_SUPPRESSED,
  FIXTURE_WHY_BY_ID,
} from "./fixtures";

export type {
  DemoAttentionActionResult,
  DemoAttentionItem,
  DemoAttentionPayload,
  DemoMemoryItem,
  DemoStatus,
  DemoSuppressedItem,
  DemoSuppressedPayload,
  DemoSuppressionReason,
  DemoWhyPayload,
} from "./types";
export {
  FIXTURE_ATTENTION,
  FIXTURE_ATTENTION_PAYLOAD,
  FIXTURE_CAN_WAIT_GROUPS,
  FIXTURE_DEMO_STATUS,
  FIXTURE_MEMORY,
  FIXTURE_STATUS,
  FIXTURE_SUPPRESSED,
  FIXTURE_WHY,
  FIXTURE_WHY_BY_ID,
} from "./fixtures";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

function sortByAttentionRank(items: DemoAttentionItem[]): DemoAttentionItem[] {
  return [...items].sort((a, b) => b.attention_rank - a.attention_rank);
}

export async function fetchDemoStatus(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(await fetchImpl(`${API_BASE}/demo/status`));
  } catch {
    return structuredClone(FIXTURE_DEMO_STATUS);
  }
}

export async function advanceDemoDay(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(
      await fetchImpl(`${API_BASE}/demo/timeline/day`, { method: "POST" }),
    );
  } catch {
    const next = structuredClone(FIXTURE_DEMO_STATUS);
    const current = new Date(FIXTURE_DEMO_STATUS.simulated_time ?? "2026-01-01T09:00:00Z");
    current.setUTCDate(current.getUTCDate() + 1);
    next.simulated_time = current.toISOString().replace(".000Z", "+00:00");
    return next;
  }
}

export async function advanceDemoStep(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(
      await fetchImpl(`${API_BASE}/demo/timeline/step`, { method: "POST" }),
    );
  } catch {
    const next = structuredClone(FIXTURE_DEMO_STATUS);
    const current = new Date(FIXTURE_DEMO_STATUS.simulated_time ?? "2026-01-01T09:00:00Z");
    current.setUTCHours(current.getUTCHours() + 1);
    next.simulated_time = current.toISOString().replace(".000Z", "+00:00");
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
    const next = structuredClone(FIXTURE_DEMO_STATUS);
    next.speed = speed;
    next.paused = speed === 0;
    return next;
  }
}

export async function resetDemo(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoStatus> {
  try {
    return await readJson<DemoStatus>(
      await fetchImpl(`${API_BASE}/demo/reset`, { method: "POST" }),
    );
  } catch {
    return structuredClone(FIXTURE_DEMO_STATUS);
  }
}

export async function fetchDemoAttention(
  fetchImpl: typeof fetch = fetch,
): Promise<DemoAttentionPayload> {
  try {
    const body = await readJson<DemoAttentionPayload>(
      await fetchImpl(`${API_BASE}/demo/attention`),
    );
    return {
      ...body,
      items: sortByAttentionRank(body.items),
    };
  } catch {
    return structuredClone(FIXTURE_ATTENTION_PAYLOAD);
  }
}

export async function postDemoAttentionAction(
  itemId: string,
  action: "done" | "snooze",
  fetchImpl: typeof fetch = fetch,
): Promise<DemoAttentionActionResult> {
  try {
    const body = await readJson<DemoAttentionActionResult>(
      await fetchImpl(`${API_BASE}/demo/attention/${itemId}/${action}`, {
        method: "POST",
      }),
    );
    return {
      ...body,
      items: sortByAttentionRank(body.items),
    };
  } catch {
    const remaining = FIXTURE_ATTENTION.filter((item) => item.id !== itemId);
    const suppressed = FIXTURE_ATTENTION_PAYLOAD.suppressed_count ?? 0;
    return {
      ok: true,
      item_id: itemId,
      action,
      items: sortByAttentionRank(remaining),
      signals_considered: remaining.length + suppressed,
      surfaced_count: remaining.length,
      suppressed_count: suppressed,
    };
  }
}

export async function fetchDemoSuppressed(
  reason?: DemoSuppressionReason | null,
  fetchImpl: typeof fetch = fetch,
): Promise<DemoSuppressedPayload> {
  try {
    const params = reason != null ? `?reason=${encodeURIComponent(reason)}` : "";
    return await readJson<DemoSuppressedPayload>(
      await fetchImpl(`${API_BASE}/demo/suppressed${params}`),
    );
  } catch {
    const next = structuredClone(FIXTURE_SUPPRESSED);
    if (reason) {
      next.filter = reason;
      next.items = next.items.filter((item) => item.suppression_reason === reason);
      next.sample_count = next.items.length;
    }
    return next;
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
