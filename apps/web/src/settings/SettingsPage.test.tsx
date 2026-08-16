import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SettingsPage } from "../pages/SettingsPage";
import { FIXTURE_SETTINGS } from "./fixtures";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("SettingsPage", () => {
  it("lists calendars and Apple permission placeholders", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/settings")) {
        return jsonResponse(FIXTURE_SETTINGS);
      }
      throw new Error(`unexpected fetch ${url}`);
    }) as unknown as typeof fetch;

    render(<SettingsPage fetchImpl={fetchImpl} />);

    expect(await screen.findByRole("checkbox", { name: /work/i })).toBeChecked();
    expect(screen.getByRole("heading", { name: /apple permissions/i })).toBeInTheDocument();
    expect(screen.getByText(/calendar — read access/i)).toBeInTheDocument();
    expect(screen.getByText(/reminders — read access/i)).toBeInTheDocument();
    expect(screen.getByText(/contacts — read access/i)).toBeInTheDocument();
    expect(screen.getByText(/notes — automation/i)).toBeInTheDocument();
    expect(screen.getByText(/scheduled for sync:/i)).toHaveTextContent(
      /apple:work,\s*apple:personal/,
    );
  });

  it("persists toggles and drops disabled calendars from sync", async () => {
    let state = structuredClone(FIXTURE_SETTINGS);
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/settings") && (!init || !init.method || init.method === "GET")) {
        return jsonResponse(state);
      }
      if (url.endsWith("/api/settings/calendars") && init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as { enabled_ids: string[] };
        const enabled = new Set(body.enabled_ids);
        state = {
          ...state,
          calendars: state.calendars.map((cal) => ({
            ...cal,
            enabled: enabled.has(cal.id),
          })),
          scheduled_for_sync: [...enabled],
        };
        return jsonResponse(state);
      }
      throw new Error(`unexpected fetch ${url}`);
    }) as unknown as typeof fetch;

    render(<SettingsPage fetchImpl={fetchImpl} />);
    const work = await screen.findByRole("checkbox", { name: /work/i });
    fireEvent.click(work);

    await waitFor(() => {
      expect(screen.getByText(/scheduled for sync:/i)).toHaveTextContent("apple:personal");
      expect(screen.getByText(/scheduled for sync:/i)).not.toHaveTextContent("apple:work");
    });
  });
});
