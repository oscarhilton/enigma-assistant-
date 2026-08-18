import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ALEX_CONVERSATION_CANARY } from "../pilot/WorldMockClient";
import { CONVERSATION_STREAM_PATH } from "./conversationStreamClient";
import { clearThreadStorage } from "./threadStorage";

const PRIVATE_CANARY = "V2_PRIVATE_THREAD_MUST_NOT_LEAK";

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function mockPrivateStream(userText: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes(CONVERSATION_STREAM_PATH)) {
        return sseResponse([
          `event: turn_complete\ndata: {"items":[{"kind":"enigma_message","text":"ack","at":"t"}],"conversation":{"items":[{"kind":"user_message","text":${JSON.stringify(userText)},"at":"t"},{"kind":"enigma_message","text":"ack","at":"t"}]}}\n\n`,
        ]);
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );
}

async function waitForWorldReady() {
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

async function switchWorld(world: "alex_lab" | "my_enigma") {
  fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: world } });
  await waitFor(() => {
    expect(screen.getByTestId("world-switcher")).toHaveValue(world);
    expect(screen.getByTestId("v2-shell")).toHaveAttribute("data-world", world);
  });
  await waitForWorldReady();
}

describe("UI2-04 conversation continuity", () => {
  beforeEach(() => {
    clearThreadStorage("my_enigma");
    clearThreadStorage("alex_lab");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("WORLD_SWITCH — private thread does not appear in Alex after switch", async () => {
    mockPrivateStream(PRIVATE_CANARY);
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();

    const input = screen.getByTestId("v2-composer-input");
    fireEvent.change(input, { target: { value: PRIVATE_CANARY } });
    fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() => {
      expect(screen.getByTestId("v2-message-user")).toHaveTextContent(PRIVATE_CANARY);
    });

    await switchWorld("alex_lab");
    expect(screen.queryByTestId("v2-message-user")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("v2-message-assistant")).toHaveTextContent(ALEX_CONVERSATION_CANARY);
    });
  });

  it("WORLD_SWITCH — Alex thread does not appear in private", async () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();
    await switchWorld("alex_lab");
    await waitFor(() => {
      expect(screen.getByTestId("v2-message-assistant")).toHaveTextContent(ALEX_CONVERSATION_CANARY);
    });

    await switchWorld("my_enigma");
    const assistant = screen.queryByTestId("v2-message-assistant");
    if (assistant) {
      expect(assistant).not.toHaveTextContent(ALEX_CONVERSATION_CANARY);
    }
  });

  it("thread survives refresh within the same world", async () => {
    mockPrivateStream(PRIVATE_CANARY);
    const { unmount } = render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();

    const input = screen.getByTestId("v2-composer-input");
    fireEvent.change(input, { target: { value: PRIVATE_CANARY } });
    fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() => {
      expect(screen.getByTestId("v2-message-user")).toHaveTextContent(PRIVATE_CANARY);
    });
    unmount();

    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();
    expect(screen.getByTestId("v2-message-user")).toHaveTextContent(PRIVATE_CANARY);
  });
});
