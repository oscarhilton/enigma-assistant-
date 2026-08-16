import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FIXTURE_STATUS } from "./fixtures";
import { TimelineControls } from "./TimelineControls";

describe("TimelineControls", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders step, day, and speed controls", () => {
    render(<TimelineControls initialStatus={FIXTURE_STATUS} fetchImpl={vi.fn()} />);

    expect(screen.getByRole("heading", { name: /timeline/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next event/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next day/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^1×$/i })).toBeInTheDocument();
    expect(screen.getByTestId("simulated-time")).toHaveTextContent("2026-01-01T09:00:00+00:00");
  });

  it("advancing a day updates displayed simulated time", async () => {
    const dayStatus = {
      ...FIXTURE_STATUS,
      simulated_time: "2026-01-02T09:00:00+00:00",
    };
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/demo/timeline/day") && init?.method === "POST") {
        return Response.json(dayStatus);
      }
      return Response.json(FIXTURE_STATUS);
    }) as unknown as typeof fetch;

    render(<TimelineControls fetchImpl={fetchImpl} initialStatus={FIXTURE_STATUS} />);

    fireEvent.click(screen.getByRole("button", { name: /next day/i }));

    await waitFor(() => {
      expect(screen.getByTestId("simulated-time")).toHaveTextContent("2026-01-02T09:00:00+00:00");
    });
  });

  it("auto-plays hour steps when speed is greater than zero", async () => {
    let hours = 9;
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/demo/timeline/step") && init?.method === "POST") {
        hours += 1;
        return Response.json({
          ...FIXTURE_STATUS,
          speed: 10,
          paused: false,
          simulated_time: `2026-01-01T${String(hours).padStart(2, "0")}:00:00+00:00`,
        });
      }
      if (url.includes("/demo/timeline/speed") && init?.method === "POST") {
        return Response.json({
          ...FIXTURE_STATUS,
          speed: 10,
          paused: false,
          simulated_time: `2026-01-01T${String(hours).padStart(2, "0")}:00:00+00:00`,
        });
      }
      return Response.json(FIXTURE_STATUS);
    }) as unknown as typeof fetch;

    render(<TimelineControls fetchImpl={fetchImpl} initialStatus={FIXTURE_STATUS} />);

    fireEvent.click(screen.getByRole("button", { name: /^10×$/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^10×$/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });

    await waitFor(() => {
      expect(screen.getByTestId("simulated-time").textContent).not.toBe(
        "2026-01-01T09:00:00+00:00",
      );
    });
    expect(
      fetchImpl.mock.calls.some(
        ([input, init]) =>
          String(input).includes("/demo/timeline/step") && init?.method === "POST",
      ),
    ).toBe(true);
  });
});
