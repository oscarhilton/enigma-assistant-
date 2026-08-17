import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceCourier } from "./EvidenceCourier";
import type { EvidenceBundle } from "./types";

const bundle: EvidenceBundle = {
  mission: {
    question: "work",
    request_kind: "catch_up",
    scope: "work",
    authority: "READ",
    planned_tools: ["attention.get_current", "agenda.get"],
  },
  searched_sources: ["calendar"],
  empty_sources: ["calendar"],
  unsearched_sources: ["attention"],
  unavailable_sources: [],
  evidence: [],
  grounded_assertions: [],
  unknowns: [],
  unresolved_referents: [],
  conflicts: [],
  challenges: [],
  coverage_adequate: false,
  courier_state: "partially_returned",
};

describe("EvidenceCourier", () => {
  it("renders courier coverage line", () => {
    render(<EvidenceCourier bundle={bundle} />);
    expect(screen.getByTestId("evidence-courier")).toHaveTextContent(/THE Goose/i);
  });
});
