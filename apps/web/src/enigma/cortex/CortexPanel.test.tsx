import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EnigmaClient } from "../client";
import { MOCK_DISCLOSURES } from "../fixtures";
import type { DemoEvent } from "../types";
import { CortexPanel } from "./CortexPanel";
import { resetBrainEventIdsForTests } from "./mapEvents";

function mockClient(options?: {
  demo?: boolean;
  events?: DemoEvent[];
}): EnigmaClient {
  const handlers = new Set<(event: Parameters<EnigmaClient["subscribe"]>[0] extends infer H ? H : never) => void>();
  return {
    getConversation: vi.fn(),
    sendMessage: vi.fn(),
    getAttentionState: vi.fn(),
    getQualificationDebug: vi.fn(),
    getProvenance: vi.fn(),
    proposeAssist: vi.fn(),
    approveAssist: vi.fn(),
    jumpCheckpoint: vi.fn(),
    listCheckpoints: vi.fn(),
    getDemoEvents: vi.fn().mockResolvedValue(
      options?.events ?? [
        {
          kind: "checkpoint_loaded",
          at: "2026-01-19T10:00:00+00:00",
          checkpoint_id: "alex-jan-19-am",
        } satisfies DemoEvent,
        {
          kind: "attention_surfaced",
          at: "2026-01-19T10:05:00+00:00",
          checkpoint_id: "alex-jan-19-am",
          needs_you_count: 2,
        } satisfies DemoEvent,
      ],
    ),
    getDemoStatus: vi.fn(),
    advanceDemoDay: vi.fn(),
    advanceDemoStep: vi.fn(),
    setDemoSpeed: vi.fn(),
    getRecentDisclosures: vi.fn().mockResolvedValue(MOCK_DISCLOSURES),
    subscribe: vi.fn((handler) => {
      handlers.add(handler);
      return () => handlers.delete(handler);
    }),
    isDemo: vi.fn(() => options?.demo ?? true),
  };
}

describe("CortexPanel", () => {
  it("shows region legend and projected events when opened", async () => {
    resetBrainEventIdsForTests();
    render(<CortexPanel client={mockClient()} />);

    fireEvent.click(screen.getByRole("button", { name: /^cortex$/i }));

    expect(await screen.findByTestId("cortex-region-legend")).toBeInTheDocument();
    const legend = screen.getByTestId("cortex-region-legend");
    expect(within(legend).getByText("Input")).toBeInTheDocument();
    expect(within(legend).getByText("Membrane")).toBeInTheDocument();
    expect(await screen.findByText(/World state · checkpoint loaded/i)).toBeInTheDocument();
    expect(screen.getByText(/Attention · surface/i)).toBeInTheDocument();
    expect(screen.getByText(/Egress · conversation.orchestrate/i)).toBeInTheDocument();
  });

  it("filters to membrane events in privacy mode", async () => {
    resetBrainEventIdsForTests();
    render(<CortexPanel client={mockClient()} />);

    fireEvent.click(screen.getByRole("button", { name: /^cortex$/i }));
    await screen.findByText(/World state · checkpoint loaded/i);

    fireEvent.click(screen.getByRole("button", { name: /what left the brain/i }));

    const log = screen.getByLabelText("Brain event log");
    expect(within(log).queryByText(/World state/i)).not.toBeInTheDocument();
    expect(within(log).getByText(/Egress · conversation.orchestrate/i)).toBeInTheDocument();
  });

  it("renders SEC-07 retention slider stub", async () => {
    render(<CortexPanel client={mockClient({ demo: false })} />);

    fireEvent.click(screen.getByRole("button", { name: /^cortex$/i }));

    const slider = await screen.findByTestId("cortex-retention-slider");
    expect(within(slider).getByRole("slider", { name: "Retention stage" })).toBeInTheDocument();
    expect(within(slider).getByText("88%")).toBeInTheDocument();
    expect(within(slider).getByText("4%")).toBeInTheDocument();
  });
});
