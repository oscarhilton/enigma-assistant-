import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FIXTURE_STATUS } from "./fixtures";
import { TimelineControls } from "./TimelineControls";

describe("TimelineControls", () => {
  it("renders step, day, speed, and reset controls", () => {
    render(<TimelineControls initialStatus={FIXTURE_STATUS} fetchImpl={vi.fn()} />);

    expect(screen.getByRole("heading", { name: /timeline/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next event/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next day/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset demo/i })).toBeInTheDocument();
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

  it("Reset demo confirms then POSTs /demo/reset and restores epoch time", async () => {
    const resetStatus = {
      ...FIXTURE_STATUS,
      simulated_time: "2026-01-01T09:00:00+00:00",
      reset: true,
      storage_wiped: true,
    };
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/demo/reset") && init?.method === "POST") {
        return Response.json(resetStatus);
      }
      return Response.json({
        ...FIXTURE_STATUS,
        simulated_time: "2026-01-05T09:00:00+00:00",
      });
    }) as unknown as typeof fetch;
    const confirmImpl = vi.fn(() => true);

    render(
      <TimelineControls
        fetchImpl={fetchImpl}
        confirmImpl={confirmImpl}
        initialStatus={{
          ...FIXTURE_STATUS,
          simulated_time: "2026-01-05T09:00:00+00:00",
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /reset demo/i }));

    await waitFor(() => {
      expect(confirmImpl).toHaveBeenCalledOnce();
      expect(fetchImpl).toHaveBeenCalledWith(
        expect.stringContaining("/demo/reset"),
        expect.objectContaining({ method: "POST" }),
      );
      expect(screen.getByTestId("simulated-time")).toHaveTextContent("2026-01-01T09:00:00+00:00");
    });
  });

  it("Reset demo does nothing when confirm is cancelled", async () => {
    const fetchImpl = vi.fn(async () => Response.json(FIXTURE_STATUS)) as unknown as typeof fetch;
    const confirmImpl = vi.fn(() => false);

    render(
      <TimelineControls
        fetchImpl={fetchImpl}
        confirmImpl={confirmImpl}
        initialStatus={FIXTURE_STATUS}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /reset demo/i }));

    await waitFor(() => {
      expect(confirmImpl).toHaveBeenCalledOnce();
    });
    expect(fetchImpl).not.toHaveBeenCalledWith(
      expect.stringContaining("/demo/reset"),
      expect.anything(),
    );
  });
});
