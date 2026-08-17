import { describe, expect, it } from "vitest";
import {
  DISCLOSURE_RECENT_PATH,
  DisclosureUnavailableError,
  disclosureErrorFromUnknown,
  readDisclosureList,
} from "./disclosureFetch";

function htmlResponse(status = 200): Response {
  return new Response("<!doctype html><html><body>Vite</body></html>", {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("readDisclosureList", () => {
  it("turns HTML (SPA fallback) into a structured disclosure error, never JSON.parse", async () => {
    await expect(
      readDisclosureList(htmlResponse(), {
        correlationId: "corr-html",
        includePreview: true,
      }),
    ).rejects.toMatchObject({
      name: "DisclosureUnavailableError",
      message: "Privacy disclosure unavailable",
      status: 200,
      endpoint: DISCLOSURE_RECENT_PATH,
      expected: "application/json",
      received: "text/html",
      correlationId: "corr-html",
      preview: expect.stringMatching(/^<!doctype html>/i),
    });
  });

  it("treats a missing or empty disclosures array as an empty list", async () => {
    await expect(
      readDisclosureList(jsonResponse({}), { correlationId: "corr-empty" }),
    ).resolves.toEqual([]);
    await expect(
      readDisclosureList(jsonResponse({ disclosures: [] }), { correlationId: "corr-empty" }),
    ).resolves.toEqual([]);
  });

  it("does not leak a JSON.parse exception for non-JSON bodies", async () => {
    const response = new Response("not-json-at-all", {
      status: 200,
      headers: { "content-type": "text/plain" },
    });
    try {
      await readDisclosureList(response, { correlationId: "corr-plain" });
      throw new Error("expected readDisclosureList to fail");
    } catch (err) {
      expect(err).toBeInstanceOf(DisclosureUnavailableError);
      expect(String(err)).not.toMatch(/unexpected token/i);
      expect((err as DisclosureUnavailableError).message).toBe("Privacy disclosure unavailable");
    }
  });
});

describe("disclosureErrorFromUnknown", () => {
  it("rewrites a raw JSON.parse crash into the product error", () => {
    const error = disclosureErrorFromUnknown(
      new Error(`Unexpected token '<', "<!doctype "... is not valid JSON`),
      "corr-sanitize",
    );
    expect(error).toBeInstanceOf(DisclosureUnavailableError);
    expect(error.message).toBe("Privacy disclosure unavailable");
    expect(error.received).toBe("text/html");
    expect(error.status).toBe(200);
    expect(error.correlationId).toBe("corr-sanitize");
    expect(error.preview).toBeUndefined();
  });
});
