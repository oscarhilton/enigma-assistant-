import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DemoEnigmaClient } from "./DemoEnigmaClient";
import { EnigmaProvider, useEnigmaConversation } from "./EnigmaProvider";
import { isWorldConflictError } from "./readApiJson";
import { PrivateWorldClient } from "../pilot/PrivateWorldClient";
import { WorldProvider } from "../pilot/WorldProvider";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const SILENCE = {
  simulated_time: "2026-08-18T12:00:00+00:00",
  checkpoint_id: null,
  needs_you: [],
  context: [],
  next_actions: [],
  can_wait_summary: null,
  presentation: {
    chat_opening_count: 0,
    notification_slot_count: 0,
    proactive_silence: true,
  },
};

function ErrorProbe() {
  const { error, loading } = useEnigmaConversation();
  if (loading) {
    return <div data-testid="conversation-host">loading</div>;
  }
  return (
    <div data-testid="conversation-host">
      {error ? <p role="alert">{error}</p> : "ok"}
    </div>
  );
}

/** Covers v2's shared bootstrap: WorldProvider hydrate + EnigmaProvider initial fetch. */
describe("EnigmaProvider world-aware routes", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does not hit /demo/conversation or /demo/attention/state when API active world is my_enigma", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/worlds")) {
        return jsonResponse({ active: "my_enigma", worlds: [] });
      }
      if (url.includes("/worlds/my_enigma/conversation")) {
        return jsonResponse({ items: [] });
      }
      if (url.includes("/worlds/my_enigma/attention/state")) {
        return jsonResponse(SILENCE);
      }
      if (url.includes("/demo/")) {
        return jsonResponse(
          { detail: "Demo timeline controls require Alex Lab as the active world" },
          409,
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <WorldProvider persistToApi initialWorld="alex_lab">
        <EnigmaProvider client={new PrivateWorldClient()}>
          <ErrorProbe />
        </EnigmaProvider>
      </WorldProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("conversation-host")).toHaveTextContent("ok");
    });

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(urls.some((url) => url.includes("/demo/conversation"))).toBe(false);
    expect(urls.some((url) => url.includes("/demo/attention/state"))).toBe(false);
    expect(urls.some((url) => url.includes("/worlds/my_enigma/conversation"))).toBe(true);
    expect(urls.some((url) => url.includes("/worlds/my_enigma/attention/state"))).toBe(true);
  });

  it("blocks subscribe refetches after a world-conflict 409 instead of looping", async () => {
    let conversationCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/demo/conversation")) {
        conversationCalls += 1;
        return jsonResponse(
          { detail: "Demo timeline controls require Alex Lab as the active world" },
          409,
        );
      }
      if (url.includes("/demo/attention/state")) {
        return jsonResponse(
          { detail: "Demo timeline controls require Alex Lab as the active world" },
          409,
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <WorldProvider initialWorld="alex_lab">
        <EnigmaProvider client={new DemoEnigmaClient()}>
          <ErrorProbe />
        </EnigmaProvider>
      </WorldProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Alex Lab as the active world/);
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(conversationCalls).toBeLessThanOrEqual(2);
  });

  it("detects demo-route world conflict copy", () => {
    expect(
      isWorldConflictError("Demo timeline controls require Alex Lab as the active world"),
    ).toBe(true);
  });
});
