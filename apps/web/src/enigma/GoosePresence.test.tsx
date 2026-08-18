import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GoosePresence } from "./GoosePresence";
import { licenseGoosePixels, type AgentWorkSnapshot } from "./goosePixels";
import { CortexPanel } from "./cortex/CortexPanel";
import type { EnigmaClient } from "./client";

const WORK: AgentWorkSnapshot = {
  exists: true,
  phase: "complete",
  semanticToken: "stable-work-1",
  inspectTarget: "item-obligation_token_audit",
  inspectLabels: ["Checked why this matters"],
};

describe("GoosePresence", () => {
  it("NO_WORK: renders nothing", () => {
    const { container } = render(
      <GoosePresence licence={licenseGoosePixels(null, "playful")} />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
  });

  it("WORK_EXISTS: motion tracks work; click explains work not mascot mood", () => {
    const onInspect = vi.fn();
    render(
      <GoosePresence licence={licenseGoosePixels(WORK, "restrained")} onInspect={onInspect} />,
    );
    const goose = screen.getByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-motion", "return");
    expect(goose).toHaveAttribute("data-layer", "surface");
    expect(goose).toHaveAttribute("data-authority", "none");
    expect(goose).toHaveAttribute("data-evidence", "false");
    expect(goose).not.toHaveTextContent(/ground truth|authoritative|evidence/i);
    screen.getByRole("button", { name: /explain checked why this matters/i }).click();
    expect(onInspect).toHaveBeenCalledOnce();
  });

  it("SERIOUS_FRAME vs PLAYFUL_FRAME: same motion, different expressiveness", () => {
    const serious = licenseGoosePixels(WORK, "restrained");
    const { rerender } = render(<GoosePresence licence={serious} />);
    const goose = screen.getByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-motion", "return");
    expect(goose).toHaveAttribute("data-expressiveness", "restrained");

    rerender(<GoosePresence licence={licenseGoosePixels(WORK, "playful")} />);
    expect(screen.getByTestId("surface-goose")).toHaveAttribute("data-motion", "return");
    expect(screen.getByTestId("surface-goose")).toHaveAttribute("data-expressiveness", "playful");
  });

  it("does not crowbar into Cortex forensic chrome", () => {
    const client = {
      isDemo: vi.fn(() => false),
      getDemoEvents: vi.fn(),
      getRecentDisclosures: vi.fn().mockResolvedValue([]),
      subscribe: vi.fn(() => () => undefined),
    } as unknown as EnigmaClient;
    render(<CortexPanel client={client} />);
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
  });
});
