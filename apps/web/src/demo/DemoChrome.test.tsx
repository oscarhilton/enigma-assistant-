import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { AttentionDashboard } from "./AttentionDashboard";
import { DEMO_BANNER_TEXT, DemoModeBanner } from "./DemoModeBanner";
import {
  FIXTURE_ATTENTION,
  FIXTURE_ATTENTION_PAYLOAD,
  FIXTURE_MEMORY,
  FIXTURE_WHY,
} from "./fixtures";
import { MemoryBrowser } from "./MemoryBrowser";
import { PrivacyInspectorHook } from "./PrivacyInspectorHook";
import { WhyView } from "./WhyView";

describe("Demo chrome stubs", () => {
  it("renders persistent DEMO MODE banner copy", () => {
    render(<DemoModeBanner active scenarioLabel="Alex Morgan v1" />);
    expect(screen.getByText(DEMO_BANNER_TEXT)).toBeInTheDocument();
    expect(screen.getByText(/Scenario: Alex Morgan v1/i)).toBeInTheDocument();
  });

  it("keeps the DEMO MODE banner on /demo routes", () => {
    render(
      <MemoryRouter initialEntries={["/demo"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText(DEMO_BANNER_TEXT)).toBeInTheDocument();
  });

  it("AttentionDashboard uses private UI names and split priority/confidence", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json(FIXTURE_ATTENTION_PAYLOAD),
    ) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <AttentionDashboard fetchImpl={fetchImpl} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Review Atlas proposal/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /^attention$/i })).toBeInTheDocument();
    expect(screen.getByText(/What actually matters right now\./i)).toBeInTheDocument();
    expect(screen.getByText(/Fictional scenario · Alex Morgan/i)).toBeInTheDocument();
    expect(screen.getByText(/Follow up with Maya/i)).toBeInTheDocument();
    expect(screen.queryByText(/PERSON_A/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/score\s+0\./i)).not.toBeInTheDocument();
    expect(screen.getByText("4/5")).toBeInTheDocument();
    expect(screen.getByText("0.91")).toBeInTheDocument();
    expect(screen.getByText(/2 items surfaced · 47 signals suppressed/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /why\?/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /^done$/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /^snooze$/i }).length).toBeGreaterThan(0);
    expect(screen.queryByText(/scenario truth/i)).not.toBeInTheDocument();
  });

  it("AttentionDashboard Done removes an item via stub action", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/demo/attention/") && init?.method === "POST") {
        return Response.json({
          ok: true,
          item_id: "att-atlas-review",
          action: "done",
          items: FIXTURE_ATTENTION.filter((item) => item.id !== "att-atlas-review"),
          surfaced_count: 1,
          suppressed_count: 47,
        });
      }
      return Response.json(FIXTURE_ATTENTION_PAYLOAD);
    }) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <AttentionDashboard fetchImpl={fetchImpl} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Review Atlas proposal/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByRole("button", { name: /^done$/i })[0]!);
    await waitFor(() => {
      expect(screen.queryByText(/Review Atlas proposal/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText(/Follow up with Maya/i)).toBeInTheDocument();
  });

  it("AttentionDashboard refetches when simulatedTime changes", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json(FIXTURE_ATTENTION_PAYLOAD),
    ) as unknown as typeof fetch;

    const { rerender } = render(
      <MemoryRouter>
        <AttentionDashboard
          fetchImpl={fetchImpl}
          simulatedTime="2026-01-05T08:00:00+00:00"
        />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchImpl).toHaveBeenCalledTimes(1);
    });

    rerender(
      <MemoryRouter>
        <AttentionDashboard
          fetchImpl={fetchImpl}
          simulatedTime="2026-01-06T08:00:00+00:00"
        />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchImpl).toHaveBeenCalledTimes(2);
    });
  });

  it("MemoryBrowser lists memories without ground-truth overlay", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json({ items: FIXTURE_MEMORY }),
    ) as unknown as typeof fetch;

    render(<MemoryBrowser fetchImpl={fetchImpl} />);

    await waitFor(() => {
      expect(screen.getByText(/PERSON_A is a frequent collaborator/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("tab", { name: /people/i })).toBeInTheDocument();
    expect(screen.queryByText(/scenario truth/i)).not.toBeInTheDocument();
  });

  it("WhyView renders Evidence → Inference → Decision → Why now? with split metrics", async () => {
    const fetchImpl = vi.fn(async () => Response.json(FIXTURE_WHY)) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <WhyView itemId="att-atlas-review" fetchImpl={fetchImpl} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/WHY ENIGMA THINKS THIS MATTERS/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /^evidence$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^inference$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^decision$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^why now\?$/i })).toBeInTheDocument();
    expect(screen.getByText(/USER made a commitment to PERSON_A/i)).toBeInTheDocument();
    expect(screen.getByText(/Surface as a high-priority item/i)).toBeInTheDocument();
    expect(screen.getByText(/still enough time to act/i)).toBeInTheDocument();
    expect(screen.getByText("4/5")).toBeInTheDocument();
    expect(screen.getByText("0.91")).toBeInTheDocument();
    expect(screen.queryByText(/Priority score/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/reason codes/i)).toHaveTextContent(
      /USER_COMMITMENT · DEADLINE_APPROACHING/,
    );
  });

  it("PrivacyInspectorHook links to shared inspector", () => {
    render(
      <MemoryRouter>
        <PrivacyInspectorHook />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: /open privacy inspector/i })).toHaveAttribute(
      "href",
      "/privacy",
    );
  });
});
