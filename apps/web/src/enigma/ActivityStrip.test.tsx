import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActivityStrip } from "./ActivityStrip";
import type { EnigmaActivityEvent } from "./activity";

function event(
  partial: Partial<EnigmaActivityEvent> & Pick<EnigmaActivityEvent, "id" | "kind" | "label">,
): EnigmaActivityEvent {
  return {
    at: "2026-01-19T10:00:00Z",
    phase: "done",
    forensic_only: false,
    ...partial,
  };
}

describe("ActivityStrip", () => {
  it("renders a single completed hop as a one-liner", () => {
    render(
      <ActivityStrip
        events={[event({ id: "a1", kind: "availability.checked", label: "Checked your calendar" })]}
      />,
    );
    expect(screen.getByTestId("activity-strip")).toHaveTextContent("Checked your calendar");
    expect(screen.queryByText(/checked 1 things/i)).not.toBeInTheDocument();
  });

  it("collapses several hops into Checked N things", () => {
    render(
      <ActivityStrip
        events={[
          event({ id: "a1", kind: "attention.queried", label: "Checked what needs you" }),
          event({ id: "a2", kind: "world.explained", label: "Checked why this matters" }),
        ]}
      />,
    );
    const strip = screen.getByTestId("activity-strip");
    expect(strip).toHaveTextContent("Checked 2 things");
    fireEvent.click(screen.getByText("Checked 2 things"));
    expect(strip).toHaveTextContent("Checked what needs you");
    expect(strip).toHaveTextContent("Checked why this matters");
  });

  it("hides forensic-only and assist-card events", () => {
    const { container } = render(
      <ActivityStrip
        events={[
          event({ id: "e", kind: "egress.allowed", label: "Remote inference allowed", forensic_only: true }),
          event({ id: "p", kind: "assist.proposed", label: "Prepared an action" }),
        ]}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
