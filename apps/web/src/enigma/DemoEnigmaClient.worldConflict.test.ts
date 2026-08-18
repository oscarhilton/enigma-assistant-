import { afterEach, describe, expect, it, vi } from "vitest";
import { DemoEnigmaClient } from "./DemoEnigmaClient";

const DETAIL = "Demo timeline controls require Alex Lab as the active world";

function conflictResponse(): Response {
  return new Response(JSON.stringify({ detail: DETAIL }), {
    status: 409,
    headers: { "Content-Type": "application/json" },
  });
}

async function rejectionMessage(run: () => Promise<unknown>): Promise<string> {
  try {
    await run();
  } catch (cause: unknown) {
    return cause instanceof Error ? cause.message : String(cause);
  }
  throw new Error("expected request to reject");
}

describe("DemoEnigmaClient world conflict", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does not report /demo/conversation 409 as conversationDismiss", async () => {
    vi.stubGlobal("fetch", async () => conflictResponse());
    const message = await rejectionMessage(() => new DemoEnigmaClient().getConversation());
    expect(message).toContain(DETAIL);
    expect(message).toContain("Switch the world switcher to match");
    expect(message).not.toMatch(/conversationDismiss/);
  });

  it("does not report /demo/conversation/message 409 as messageDismiss", async () => {
    vi.stubGlobal("fetch", async () => conflictResponse());
    const message = await rejectionMessage(() => new DemoEnigmaClient().sendMessage("hello"));
    expect(message).toContain(DETAIL);
    expect(message).not.toMatch(/messageDismiss/);
  });
});
