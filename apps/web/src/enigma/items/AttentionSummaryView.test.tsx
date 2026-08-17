import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AttentionSummaryView } from "./AttentionSummaryView";
import { MOCK_ATTENTION_JAN19 } from "../fixtures";
import type { AttentionState } from "../types";

const MOCK_ATTENTION_WITH_RADAR: AttentionState = {
  ...MOCK_ATTENTION_JAN19,
  context: [
    ...MOCK_ATTENTION_JAN19.context,
    {
      id: "item-obligation_brunch_book",
      title: "Book Saturday brunch for Elena's parents",
      explanation: "Waiting on venue confirmation.",
      policy_decision: "context",
      bucket: "context",
      reasons: [{ code: "WAITING", label: "Waiting" }],
      evidence_ids: ["rem-brunch-book"],
    },
    {
      id: "item-obligation_atlas_review",
      title: "Review Atlas proposal",
      explanation: "Due later this week.",
      policy_decision: "context",
      bucket: "context",
      reasons: [{ code: "NEAR_TERM", label: "Near term" }],
      evidence_ids: ["mail-atlas"],
    },
  ],
};

describe("AttentionSummaryView", () => {
  it("shows next action once and excludes coalesced context from radar", () => {
    render(
      <AttentionSummaryView
        state={MOCK_ATTENTION_WITH_RADAR}
        at={MOCK_ATTENTION_WITH_RADAR.simulated_time}
        demoMode
      />,
    );

    expect(screen.getByText(/^Nothing needs you\.$/)).toBeInTheDocument();
    expect(screen.getByText(/^A good thing you could do:$/)).toBeInTheDocument();
    expect(screen.getAllByText(/token inventory/i)).toHaveLength(1);
    expect(screen.getByText(/^Context · Optional$/)).toBeInTheDocument();
    expect(screen.queryByText(/^CONTEXT$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/held as context/i)).not.toBeInTheDocument();

    const radar = screen.getByText(/^Also on my radar · 2$/).closest("details");
    expect(radar).not.toBeNull();
    const radarScope = within(radar as HTMLElement);
    expect(radarScope.getByText(/Book Saturday brunch/i)).toBeInTheDocument();
    expect(radarScope.getByText(/Review Atlas proposal/i)).toBeInTheDocument();
    expect(radarScope.queryByText(/token inventory/i)).not.toBeInTheDocument();
  });

  it("hides radar section when all context is coalesced into next actions", () => {
    render(
      <AttentionSummaryView
        state={MOCK_ATTENTION_JAN19}
        at={MOCK_ATTENTION_JAN19.simulated_time}
        demoMode
      />,
    );

    expect(screen.getAllByText(/token inventory/i)).toHaveLength(1);
    expect(screen.queryByText(/Also on my radar/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/keeping in mind/i)).not.toBeInTheDocument();
  });

  it("expands radar rows on click without showing badges when collapsed", () => {
    const onWhy = vi.fn();
    render(
      <AttentionSummaryView
        state={MOCK_ATTENTION_WITH_RADAR}
        at={MOCK_ATTENTION_WITH_RADAR.simulated_time}
        onWhy={onWhy}
        demoMode
      />,
    );

    expect(screen.queryByText(/^CONTEXT$/)).not.toBeInTheDocument();

    const radar = screen.getByText(/^Also on my radar · 2$/).closest("details");
    expect(radar).not.toBeNull();
    const radarScope = within(radar as HTMLElement);
    expect(radarScope.queryByRole("button", { name: /^Why now\?$/ })).not.toBeInTheDocument();

    fireEvent.click(radarScope.getByRole("button", { name: /Book Saturday brunch/i }));

    expect(radarScope.getByText(/Waiting on venue confirmation/i)).toBeInTheDocument();
    fireEvent.click(radarScope.getByRole("button", { name: /^Why now\?$/ }));
    expect(onWhy).toHaveBeenCalledWith("item-obligation_brunch_book");
  });
});
