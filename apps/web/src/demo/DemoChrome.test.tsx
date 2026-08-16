import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { AttentionDashboard } from "./AttentionDashboard";
import { DEMO_BANNER_TEXT, DemoModeBanner } from "./DemoModeBanner";
import { FIXTURE_ATTENTION, FIXTURE_MEMORY, FIXTURE_WHY } from "./fixtures";
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

  it("AttentionDashboard lists items with Why links and no ground truth", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json({ items: FIXTURE_ATTENTION }),
    ) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <AttentionDashboard fetchImpl={fetchImpl} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Review Atlas proposal/i)).toBeInTheDocument();
    });
    expect(screen.getAllByRole("link", { name: /why\?/i }).length).toBeGreaterThan(0);
    expect(screen.queryByText(/scenario truth/i)).not.toBeInTheDocument();
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

  it("WhyView renders evidence / inference / decision layers", async () => {
    const fetchImpl = vi.fn(async () => Response.json(FIXTURE_WHY)) as unknown as typeof fetch;

    render(
      <MemoryRouter>
        <WhyView itemId="att-review-atlas" fetchImpl={fetchImpl} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/WHY ENIGMA THINKS THIS MATTERS/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /^evidence$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^inference$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^decision$/i })).toBeInTheDocument();
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
