import type { WorldId } from "../pilot/types";
import { createThread, type V2Thread } from "./threadTypes";

const THREADS_KEY = "enigma.v2.threads";
const ACTIVE_KEY = "enigma.v2.activeThread";

function storageKey(prefix: string, world: WorldId): string {
  return `${prefix}.${world}`;
}

function readJson<T>(key: string, fallback: T): T {
  if (typeof localStorage === "undefined") {
    return fallback;
  }
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  if (typeof localStorage === "undefined") {
    return;
  }
  localStorage.setItem(key, JSON.stringify(value));
}

export function loadThreads(world: WorldId): V2Thread[] {
  const threads = readJson<V2Thread[]>(storageKey(THREADS_KEY, world), []);
  if (threads.length === 0) {
    const seed = createThread();
    writeJson(storageKey(THREADS_KEY, world), [seed]);
    writeJson(storageKey(ACTIVE_KEY, world), seed.id);
    return [seed];
  }
  return threads;
}

export function saveThreads(world: WorldId, threads: V2Thread[]): void {
  writeJson(storageKey(THREADS_KEY, world), threads);
}

export function loadActiveThreadId(world: WorldId, threads: V2Thread[]): string {
  const stored = readJson<string | null>(storageKey(ACTIVE_KEY, world), null);
  if (stored && threads.some((thread) => thread.id === stored)) {
    return stored;
  }
  return threads[0]?.id ?? createThread().id;
}

export function saveActiveThreadId(world: WorldId, threadId: string): void {
  writeJson(storageKey(ACTIVE_KEY, world), threadId);
}

export function clearThreadStorage(world: WorldId): void {
  if (typeof localStorage === "undefined") {
    return;
  }
  localStorage.removeItem(storageKey(THREADS_KEY, world));
  localStorage.removeItem(storageKey(ACTIVE_KEY, world));
}
