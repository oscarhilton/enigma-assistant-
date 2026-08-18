import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, type ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EnigmaProvider } from "../enigma/EnigmaProvider";
import type { AgentWorkSnapshot } from "../enigma/goosePixels";
import { WorldProvider } from "../pilot/WorldProvider";
import { CONVERSATION_STREAM_PATH, streamConversationMessage } from "./conversationStreamClient";
import { gooseFromAgentWork } from "./gooseFromAgentWork";
import { parseConversationStream } from "./parseConversationStream";
import { appendStreamingText, V2ConversationViewport } from "./V2ConversationViewport";
import { V2Composer } from "./V2Composer";
import { useV2StreamingConversation } from "./useV2StreamingConversation";

const IN_FLIGHT: AgentWorkSnapshot = {
  exists: true,
  phase: "in_flight",
  semanticToken: "in-flight",
  inspectTarget: null,
  inspectLabels: ["Checked your calendar"],
};

const COMPLETE: AgentWorkSnapshot = {
  ...IN_FLIGHT,
  phase: "complete",
  semanticToken: "Checked your calendar",
};

function sseResponse(chunks: string[], { hang = false }: { hang?: boolean } = {}): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      if (!hang) {
        controller.close();
      }
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function delayedSse(): {
  response: Response;
  push: (chunk: string) => void;
  close: () => void;
} {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array> | undefined;
  const stream = new ReadableStream<Uint8Array>({
    start(next) {
      controller = next;
    },
  });
  return {
    response: new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }),
    push(chunk: string) {
      controller?.enqueue(encoder.encode(chunk));
    },
    close() {
      controller?.close();
    },
  };
}

function wrap(ui: ReactElement) {
  return (
    <MemoryRouter>
      <WorldProvider>
        <EnigmaProvider>{ui}</EnigmaProvider>
      </WorldProvider>
    </MemoryRouter>
  );
}

function StreamingHarness({ autoSend }: { autoSend?: string }) {
  const session = useV2StreamingConversation();
  useEffect(() => {
    if (autoSend) {
      void session.sendMessage(autoSend);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSend]);
  return (
    <div>
      <span data-testid="busy">{String(session.busy)}</span>
      <span data-testid="disconnected">{String(session.disconnected)}</span>
      <span data-testid="streaming-text">{session.streamingText}</span>
      <span data-testid="goose-motion">{session.gooseLicence.motion}</span>
      <button type="button" onClick={() => session.cancel()}>
        cancel-harness
      </button>
      <button type="button" onClick={() => void session.reconnect()}>
        reconnect-harness
      </button>
    </div>
  );
}

describe("UI2-02 streaming", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("parses agent_work before prose across chunk boundaries", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: agent_work\ndata: {"exists":true,"phase":"in_flight","inspect_labels":[]}\n'));
        controller.enqueue(encoder.encode("\nevent: prose\ndata: {\"delta\":\"Hello \"}\n\n"));
        controller.enqueue(
          encoder.encode('event: turn_complete\ndata: {"items":[{"kind":"enigma_message","text":"Hello world","at":"t"}]}\n\n'),
        );
        controller.close();
      },
    });
    const events: string[] = [];
    for await (const event of parseConversationStream(stream)) {
      events.push(event.type);
    }
    expect(events[0]).toBe("agent_work");
    expect(events).toContain("prose");
    expect(events.at(-1)).toBe("turn_complete");
  });

  it("appendStreamingText renders partial assistant text", () => {
    const first = appendStreamingText(null, "Saturday ");
    const second = appendStreamingText(first, "is free.");
    expect(second.text).toBe("Saturday is free.");
    expect(second.streaming).toBe(true);
    render(<V2ConversationViewport items={[]} streamingRow={second} />);
    const bubble = screen.getByTestId("v2-message-assistant");
    expect(bubble).toHaveAttribute("data-streaming", "true");
    expect(bubble).toHaveTextContent("Saturday is free.");
  });

  it("Goose motion follows agent_work, not prose", () => {
    expect(gooseFromAgentWork(IN_FLIGHT).motion).toBe("walk");
    expect(gooseFromAgentWork(COMPLETE).motion).toBe("return");
    expect(gooseFromAgentWork(COMPLETE).inspectLabels).toEqual(["Checked your calendar"]);
  });

  it("composer Stop cancels and Reconnect is available after a drop", () => {
    const onCancel = vi.fn();
    const onReconnect = vi.fn();
    const { rerender } = render(
      <V2Composer onSend={async () => undefined} busy onCancel={onCancel} />,
    );
    fireEvent.click(screen.getByTestId("v2-composer-stop"));
    expect(onCancel).toHaveBeenCalledOnce();
    rerender(
      <V2Composer
        onSend={async () => undefined}
        disconnected
        onReconnect={onReconnect}
      />,
    );
    fireEvent.click(screen.getByTestId("v2-composer-reconnect"));
    expect(onReconnect).toHaveBeenCalledOnce();
  });

  it("stream renders partial text before turn_complete and Goose can return while prose continues", async () => {
    const delayed = delayedSse();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes(CONVERSATION_STREAM_PATH)) {
          return delayed.response;
        }
        throw new Error(`unexpected fetch ${url}`);
      }),
    );
    render(wrap(<StreamingHarness autoSend="What's on tomorrow?" />));
    await waitFor(() => expect(screen.getByTestId("busy").textContent).toBe("true"));
    delayed.push(
      'event: agent_work\ndata: {"exists":true,"phase":"in_flight","semantic_token":"in-flight","inspect_labels":[]}\n\n',
    );
    await waitFor(() => expect(screen.getByTestId("goose-motion").textContent).toBe("walk"));
    delayed.push('event: prose\ndata: {"delta":"Team "}\n\n');
    await waitFor(() => expect(screen.getByTestId("streaming-text").textContent).toBe("Team "));
    expect(screen.getByTestId("goose-motion").textContent).toBe("walk");
    delayed.push(
      'event: agent_work\ndata: {"exists":true,"phase":"complete","semantic_token":"Checked your week","inspect_labels":["Checked your week"]}\n\n',
    );
    await waitFor(() => expect(screen.getByTestId("goose-motion").textContent).toBe("return"));
    delayed.push('event: prose\ndata: {"delta":"standup"}\n\n');
    await waitFor(() => expect(screen.getByTestId("streaming-text").textContent).toBe("Team standup"));
    expect(screen.getByTestId("goose-motion").textContent).toBe("return");
    delayed.push(
      'event: turn_complete\ndata: {"items":[{"kind":"enigma_message","text":"Team standup","at":"t"}],"conversation":{"items":[{"kind":"user_message","text":"What\'s on tomorrow?","at":"t"},{"kind":"enigma_message","text":"Team standup","at":"t"}]}}\n\n',
    );
    delayed.close();
    await waitFor(() => expect(screen.getByTestId("busy").textContent).toBe("false"));
  });

  it("cancel aborts fetch and clears busy state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(Object.assign(new Error("Aborted"), { name: "AbortError" }));
          });
        });
      }),
    );
    render(wrap(<StreamingHarness autoSend="ping" />));
    await waitFor(() => expect(screen.getByTestId("busy").textContent).toBe("true"));
    fireEvent.click(screen.getByText("cancel-harness"));
    await waitFor(() => expect(screen.getByTestId("busy").textContent).toBe("false"));
  });

  it("reconnect retries when turn_complete never arrived", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes(CONVERSATION_STREAM_PATH)) {
        return sseResponse([
          'event: agent_work\ndata: {"exists":true,"phase":"in_flight","inspect_labels":[]}\n\n',
          'event: error\ndata: {"message":"dropped"}\n\n',
        ]);
      }
      throw new Error(`unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchImpl);
    render(wrap(<StreamingHarness autoSend="retry me" />));
    await waitFor(() => expect(screen.getByTestId("disconnected").textContent).toBe("true"));
    fireEvent.click(screen.getByText("reconnect-harness"));
    await waitFor(() => expect(fetchImpl.mock.calls.length).toBeGreaterThanOrEqual(2));
    expect(
      fetchImpl.mock.calls.some((call) => String(call[0]).includes(CONVERSATION_STREAM_PATH)),
    ).toBe(true);
  });

  it("streamConversationMessage documents aborted vs disconnected outcomes", async () => {
    const controller = new AbortController();
    controller.abort();
    const outcome = await streamConversationMessage("hi", {
      signal: controller.signal,
      onEvent: () => undefined,
      fetchImpl: async () => {
        throw Object.assign(new Error("Aborted"), { name: "AbortError" });
      },
    });
    expect(outcome).toBe("aborted");
  });
});
