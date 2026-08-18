import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { licenseGoosePixels, type AgentWorkSnapshot } from "../enigma/goosePixels";
import type { ProvenanceView } from "../enigma/types";
import { buildWhyProjection } from "./whyProjection";
import { V2InspectSheet } from "./V2InspectSheet";

const WORK: AgentWorkSnapshot = {
  exists: true,
  phase: "complete",
  semanticToken: "checked-calendar",
  inspectTarget: "item-cal-check",
  inspectLabels: ["Checked your calendar"],
};

const PROVENANCE: ProvenanceView = {
  item_id: "item-cal-check",
  headline: "WHY ENIGMA HOLDS THIS",
  evidence: ["cal-1"],
  inference: ["Hold is not a booking."],
  decision: ["Reminder still open."],
  why_now: ["Calendar hold is not a reservation."],
  reason_codes: ["CALENDAR_PROXIMITY"],
};

async function waitForV2Ready() {
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

describe("UI2-05 inspectability minimal", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("buildWhyProjection passes licence labels through unchanged", () => {
    const licence = licenseGoosePixels(WORK, "restrained");
    const projection = buildWhyProjection(licence, PROVENANCE, false);
    expect(projection.workLabels).toEqual(["Checked your calendar"]);
    expect(projection.provenance?.why_now).toEqual(["Calendar hold is not a reservation."]);
  });

  it("V2InspectSheet renders work labels and provenance why_now", () => {
    const licence = licenseGoosePixels(WORK, "restrained");
    const projection = buildWhyProjection(licence, PROVENANCE, false);
    render(
      <V2InspectSheet open onOpenChange={() => undefined} projection={projection} />,
    );
    expect(screen.getByTestId("v2-inspect-sheet")).toBeInTheDocument();
    expect(screen.getByTestId("v2-inspect-work-labels")).toHaveTextContent("Checked your calendar");
    expect(screen.getByTestId("v2-inspect-why")).toHaveTextContent(
      "Calendar hold is not a reservation.",
    );
  });

  it("Goose click opens compact sheet with work labels from licence", async () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForV2Ready();
    fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: "alex_lab" } });
    await waitFor(() => {
      expect(screen.getByTestId("v2-shell")).toHaveAttribute("data-world", "alex_lab");
    });
    await waitForV2Ready();

    const goose = await screen.findByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-motion", "return");
    fireEvent.click(screen.getByRole("button", { name: /explain checked why this matters/i }));

    await waitFor(() => {
      expect(screen.getByTestId("v2-inspect-sheet")).toBeInTheDocument();
    });
    expect(screen.getByTestId("v2-inspect-work-labels")).toHaveTextContent("Checked why this matters");
    expect(screen.queryByTestId("cortex-panel-root")).not.toBeInTheDocument();
    expect(screen.queryByTestId("v2-work-explanation")).not.toBeInTheDocument();
  });

  it("sheet dismisses on world switch without stale AgentWork", async () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForV2Ready();
    fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: "alex_lab" } });
    await waitForV2Ready();

    fireEvent.click(
      await screen.findByRole("button", { name: /explain checked why this matters/i }),
    );
    await waitFor(() => {
      expect(screen.getByTestId("v2-inspect-sheet")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: "my_enigma" } });
    await waitFor(() => {
      expect(screen.getByTestId("v2-shell")).toHaveAttribute("data-world", "my_enigma");
    });
    await waitFor(() => {
      expect(screen.queryByTestId("v2-inspect-sheet")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("Checked why this matters")).not.toBeInTheDocument();
  });
});
