import type { AgentWorkPhase, AgentWorkSnapshot } from "../enigma/goosePixels";
import type { ConversationStreamEvent, TurnCompleteStreamEvent } from "./streamTypes";

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function normalizeAgentWork(raw: Record<string, unknown>): AgentWorkSnapshot {
  const phaseRaw = raw.phase;
  const phase: AgentWorkPhase | null =
    phaseRaw === "in_flight" || phaseRaw === "waiting" || phaseRaw === "complete"
      ? phaseRaw
      : null;
  const labels = raw.inspect_labels ?? raw.inspectLabels;
  const token = raw.semantic_token ?? raw.semanticToken;
  const target = raw.inspect_target ?? raw.inspectTarget;
  return {
    exists: raw.exists !== false,
    phase,
    semanticToken: typeof token === "string" ? token : "",
    inspectTarget: asString(target),
    inspectLabels: Array.isArray(labels) ? labels.map(String) : [],
  };
}

export function parseSseBlock(block: string): ConversationStreamEvent | null {
  const trimmed = block.trim();
  if (!trimmed || trimmed.startsWith(":")) {
    return null;
  }
  let name = "message";
  const dataLines: string[] = [];
  for (const line of trimmed.split("\n")) {
    if (line.startsWith("event:")) {
      name = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  const raw = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
  if (name === "agent_work") {
    return { type: "agent_work", data: normalizeAgentWork(raw) };
  }
  if (name === "prose") {
    return { type: "prose", data: { delta: String(raw.delta ?? "") } };
  }
  if (name === "turn_complete") {
    return { type: "turn_complete", data: raw as TurnCompleteStreamEvent };
  }
  if (name === "error") {
    return { type: "error", data: { message: String(raw.message ?? "Stream error") } };
  }
  return null;
}

/** Parse an Enigma-native SSE body into typed conversation stream events. */
export async function* parseConversationStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<ConversationStreamEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const readChunk = (): Promise<ReadableStreamReadResult<Uint8Array>> => {
    if (signal?.aborted) {
      return Promise.reject(Object.assign(new Error("Aborted"), { name: "AbortError" }));
    }
    if (!signal) {
      return reader.read();
    }
    return new Promise((resolve, reject) => {
      const onAbort = () => {
        signal.removeEventListener("abort", onAbort);
        void reader.cancel();
        reject(Object.assign(new Error("Aborted"), { name: "AbortError" }));
      };
      signal.addEventListener("abort", onAbort, { once: true });
      reader.read().then(
        (result) => {
          signal.removeEventListener("abort", onAbort);
          resolve(result);
        },
        (error: unknown) => {
          signal.removeEventListener("abort", onAbort);
          reject(error);
        },
      );
    });
  };
  try {
    while (true) {
      const { done, value } = await readChunk();
      if (done) {
        buffer += decoder.decode();
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const event = parseSseBlock(part);
        if (event) {
          yield event;
        }
      }
    }
    if (buffer.trim()) {
      const event = parseSseBlock(buffer);
      if (event) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
