import { parseConversationStream } from "./parseConversationStream";
import type { ConversationStreamEvent } from "./streamTypes";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export const CONVERSATION_STREAM_PATH = "/worlds/my_enigma/conversation/message/stream";

export type StreamOutcome = "complete" | "aborted" | "disconnected";

/**
 * Reconnect / resume semantics (UI2-02):
 *
 * The SSE stream is **not** byte-offset resumable. Core commits the turn
 * (session conversation) when `agent_work` complete is emitted — before prose
 * deltas. After a drop:
 *
 * 1. GET `/worlds/my_enigma/conversation` to recover the committed snapshot.
 * 2. Retry this POST only when `turn_complete` never arrived (abort / drop
 *    during in-flight work). Do not retry after `turn_complete` or you will
 *    duplicate the user turn.
 *
 * v1 `POST /worlds/my_enigma/conversation/message` stays request/response.
 */
export async function streamConversationMessage(
  text: string,
  options: {
    signal?: AbortSignal;
    onEvent: (event: ConversationStreamEvent) => void;
    fetchImpl?: typeof fetch;
  },
): Promise<StreamOutcome> {
  const fetchImpl = options.fetchImpl ?? fetch;
  try {
    const response = await fetchImpl(`${API_BASE}${CONVERSATION_STREAM_PATH}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ text }),
      signal: options.signal,
    });
    if (!response.ok) {
      options.onEvent({
        type: "error",
        data: { message: `HTTP ${response.status} ${response.url || CONVERSATION_STREAM_PATH}` },
      });
      return "disconnected";
    }
    if (!response.body) {
      options.onEvent({ type: "error", data: { message: "Stream had no body" } });
      return "disconnected";
    }
    for await (const event of parseConversationStream(response.body)) {
      if (options.signal?.aborted) {
        return "aborted";
      }
      options.onEvent(event);
      if (event.type === "error") {
        return "disconnected";
      }
    }
    return options.signal?.aborted ? "aborted" : "complete";
  } catch (cause: unknown) {
    if (options.signal?.aborted) {
      return "aborted";
    }
    if (cause instanceof DOMException && cause.name === "AbortError") {
      return "aborted";
    }
    if (cause instanceof Error && cause.name === "AbortError") {
      return "aborted";
    }
    options.onEvent({
      type: "error",
      data: { message: cause instanceof Error ? cause.message : "Stream disconnected" },
    });
    return "disconnected";
  }
}
