import { describe, expect, it } from "vitest";
import { formatApiError } from "./readApiJson";

const DEMO_CONVERSATION_URL = "http://localhost:5173/demo/conversation";
const DEMO_MESSAGE_URL = "http://localhost:5173/demo/conversation/message";

describe("formatApiError", () => {
  it("surfaces world-conflict 409 detail instead of a raw URL", () => {
    const body = JSON.stringify({
      detail: "Demo timeline controls require Alex Lab as the active world",
    });
    const message = formatApiError(409, DEMO_CONVERSATION_URL, body);
    expect(message).toContain("Demo timeline controls require Alex Lab as the active world");
    expect(message).toContain("Switch the world switcher to match");
    expect(message).not.toContain(DEMO_CONVERSATION_URL);
    expect(message).not.toMatch(/conversationDismiss/);
  });

  it("does not turn a /demo/conversation/message 409 into messageDismiss", () => {
    const body = JSON.stringify({
      detail: "Demo timeline controls require Alex Lab as the active world",
    });
    const message = formatApiError(409, DEMO_MESSAGE_URL, body);
    expect(message).not.toContain(DEMO_MESSAGE_URL);
    expect(message).not.toMatch(/messageDismiss/);
  });

  it("keeps status+URL when the body has no FastAPI detail", () => {
    expect(formatApiError(409, DEMO_CONVERSATION_URL, "<html>nope</html>")).toBe(
      `HTTP 409 ${DEMO_CONVERSATION_URL}`,
    );
  });
});
