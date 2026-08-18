import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WorldProvider } from "./WorldProvider";
import { WorldSwitcher } from "./WorldSwitcher";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("WorldProvider API hydrate", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("follows GET /worlds before mounting conversation clients", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/worlds")) {
        return jsonResponse({ active: "my_enigma", worlds: [] });
      }
      throw new Error(`unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <WorldProvider persistToApi initialWorld="alex_lab">
        <WorldSwitcher />
      </WorldProvider>,
    );

    expect(screen.getByTestId("world-hydrating")).toBeInTheDocument();
    expect(screen.queryByTestId("world-switcher")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("world-switcher")).toHaveValue("my_enigma");
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
