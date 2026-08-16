/** Demo Mode API client + offline fixtures for UI (D10). */

import type {
  DemoAttentionItem,
  DemoMemoryItem,
  DemoStatus,
  DemoWhyPayload,
} from "./types";
import {
  FIXTURE_ATTENTION,
  FIXTURE_DEMO_STATUS,
  FIXTURE_MEMORY,
  FIXTURE_WHY_BY_ID,
} from "./fixtures";

export type {
  DemoAttentionItem,
  DemoMemoryItem,
  DemoStatus,
  DemoWhyPayload,
} from "./types";
export {
  FIXTURE_ATTENTION,
  FIXTURE_DEMO_STATUS,
  FIXTURE_MEMORY,
  FIXTURE_STATUS,
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
