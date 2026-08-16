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
  FIXTURE_STATUS,
  FIXTURE_SUPPRESSED,
  FIXTURE_WHY,
} from "./fixtures";
import { MemoryBrowser } from "./MemoryBrowser";
import { PrivacyInspectorHook } from "./PrivacyInspectorHook";
import { SimulationStatus } from "./SimulationStatus";
import { SuppressionInspector } from "./SuppressionInspector";
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

  it("AttentionDashboard shows compact product cards without evidence dumps", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json({
        ...FIXTURE_ATTENTION_PAYLOAD,
        items: [
          {
            ...FIXTURE_ATTENTION[0]!,
            body: "Reminder: Review proposal; Email: Re: Proposal; Calendar: Proposal review",
          },
          FIXTURE_ATTENTION[1]!,
        ],
      }),
    ) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <AttentionDashboard fetchImpl={fetchImpl} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Review Atlas proposal/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId("attention-headline")).toHaveTextContent(
      /2 things need your attention/i,
    );
    expect(screen.getByText(/Fictional scenario · Alex Morgan/i)).toBeInTheDocument();
    expect(screen.getByText(/Follow up with Maya/i)).toBeInTheDocument();
    expect(screen.getByTestId("attention-badges-att-atlas-review")).toHaveTextContent(
      /HIGH PRIORITY · DUE SOON/i,
    );
    expect(
      screen.getByText(
        /You said you'd review this before Friday, and it still appears unfinished\./i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Maya is still waiting for a scheduling response\./i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Deadline approaching\./i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Thread waiting on you\./i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Reminder:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Email:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Calendar:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/PERSON_A/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/score\s+0\./i)).not.toBeInTheDocument();
    expect(screen.queryByText("4/5")).not.toBeInTheDocument();
    expect(screen.queryByText("0.91")).not.toBeInTheDocument();
    expect(screen.getByTestId("attention-holding-note")).toHaveTextContent(
      /holding 47 lower-priority signals/i,
    );
    expect(screen.getByTestId("attention-can-wait")).toHaveTextContent(
      /Show 47 that can wait/i,
    );
    expect(screen.getByTestId("attention-last-evaluated")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /why\?/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /^done$/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /^snooze$/i }).length).toBeGreaterThan(0);
    expect(screen.queryByText(/scenario truth/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^refresh$/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("attention-can-wait"));
    expect(screen.getByTestId("attention-can-wait")).toHaveTextContent(
      /Hide what can wait/i,
    );
    expect(screen.getByTestId("attention-can-wait-groups")).toHaveTextContent(
      /Upcoming calendar/i,
    );
    expect(screen.getByTestId("attention-can-wait-groups")).toHaveTextContent(
      /Open threads/i,
    );
    expect(screen.getByTestId("attention-can-wait-groups")).toHaveTextContent(
      /Informational/i,
    );
    expect(screen.getByTestId("attention-can-wait-groups")).toHaveTextContent(
      /Automated \/ noise/i,
    );
  });

  it("AttentionDashboard empty silence keeps holding copy without Refresh", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json({
        ...FIXTURE_ATTENTION_PAYLOAD,
        items: [],
        surfaced_count: 0,
        suppressed_count: 47,
        evaluated_at: "2026-01-01T08:58:00+00:00",
      }),
    ) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <AttentionDashboard
          fetchImpl={fetchImpl}
          nowMs={Date.parse("2026-01-01T09:00:00Z")}
        />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("attention-headline")).toHaveTextContent(
        /Nothing needs you right now/i,
      );
    });
    expect(screen.getByText(/Fictional scenario · Alex Morgan/i)).toBeInTheDocument();
    expect(screen.getByTestId("attention-holding-note")).toHaveTextContent(
      /holding 47 lower-priority signals out of view/i,
    );
    expect(screen.getByTestId("attention-can-wait")).toHaveTextContent(
      /^Show 47 that can wait$/,
    );
    expect(screen.getByTestId("attention-last-evaluated")).toHaveTextContent(
      /Last evaluated 2 minutes ago/i,
    );
    expect(screen.queryByRole("button", { name: /^refresh$/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Great job/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/No open attention items/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("attention-can-wait"));
    expect(screen.getByTestId("attention-can-wait")).toHaveTextContent(
      /Hide what can wait/i,
    );
    expect(screen.getByTestId("attention-can-wait-groups")).toBeInTheDocument();
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

  it("SimulationStatus shows signals considered vs surfaced from /demo/status", () => {
    render(<SimulationStatus status={FIXTURE_STATUS} />);
    expect(screen.getByTestId("status-compression")).toHaveTextContent(
      /49 considered · 2 surfaced · 47 suppressed/,
    );
    expect(screen.queryByText(/signal_class/i)).not.toBeInTheDocument();
  });

  it("SuppressionInspector lists why-not samples without ground-truth labels", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("reason=spam")) {
        return Response.json({
          ...FIXTURE_SUPPRESSED,
          filter: "spam",
          items: FIXTURE_SUPPRESSED.items.filter((item) => item.suppression_reason === "spam"),
          sample_count: 1,
        });
      }
      return Response.json(FIXTURE_SUPPRESSED);
    }) as unknown as typeof fetch;

    render(<SuppressionInspector fetchImpl={fetchImpl} />);

    await waitFor(() => {
      expect(screen.getByText(/Newsletter announcing/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId("suppression-compression")).toHaveTextContent(
      /49 signals considered · 2 surfaced · 47 suppressed/,
    );
    expect(screen.getByText(/Developer-only/i)).toBeInTheDocument();
    expect(screen.queryByText(/signal_class/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ground.?truth/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^spam$/i }));
    await waitFor(() => {
      expect(screen.getByText(/Urgent prize claim/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Newsletter announcing/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /why was this not surfaced/i }));
    expect(screen.getByTestId("why-not-sup-spam-1")).toHaveTextContent(/unsolicited/i);
  });

  it("mounts /demo/suppressed without adding it to the main demo nav", () => {
    render(
      <MemoryRouter initialEntries={["/demo/suppressed"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: /suppressed signals/i })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: /^demo$/i });
    expect(nav).not.toHaveTextContent(/suppressed/i);
  });
});
