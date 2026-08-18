import type { WorldId, WorldsPayload } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export async function fetchWorlds(): Promise<WorldsPayload> {
  const response = await fetch(`${API_BASE}/worlds`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.url}`);
  }
  return (await response.json()) as WorldsPayload;
}

export async function switchWorld(world: WorldId): Promise<WorldId> {
  const response = await fetch(`${API_BASE}/worlds/switch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ world }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.url}`);
  }
  const body = (await response.json()) as { active: { id: WorldId } };
  return body.active.id;
}
