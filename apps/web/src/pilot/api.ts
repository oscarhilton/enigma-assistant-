import { readApiJson } from "../enigma/readApiJson";
import type { WorldId, WorldsPayload } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export async function fetchWorlds(): Promise<WorldsPayload> {
  return readApiJson<WorldsPayload>(await fetch(`${API_BASE}/worlds`));
}

export async function switchWorld(world: WorldId): Promise<WorldId> {
  const body = await readApiJson<{ active: { id: WorldId } }>(
    await fetch(`${API_BASE}/worlds/switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ world }),
    }),
  );
  return body.active.id;
}
