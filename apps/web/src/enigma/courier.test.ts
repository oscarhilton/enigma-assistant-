import { describe, expect, it } from "vitest";
import { courierLine, deriveGooseState } from "./courier";
import type { EvidenceBundle } from "./types";

const baseBundle = (overrides: Partial<EvidenceBundle>): EvidenceBundle => ({
  mission: {
    question: "test",
    request_kind: "catch_up",
    scope: "work",
    authority: "READ",
    planned_tools: ["attention.get_current", "agenda.get"],
  },
  searched_sources: [],
  empty_sources: [],
  unsearched_sources: [],
  unavailable_sources: [],
  evidence: [],
  grounded_assertions: [],
  unknowns: [],
  unresolved_referents: [],
  conflicts: [],
  challenges: [],
  coverage_adequate: false,
  courier_state: "partially_returned",
  ...overrides,
});

describe("courierLine", () => {
  it("describes partial coverage when calendar alone was checked", () => {
    const line = courierLine(
      baseBundle({
        searched_sources: ["calendar"],
        unsearched_sources: ["attention", "world_changes", "world_blockers"],
        courier_state: "partially_returned",
      }),
    );
    expect(line).toContain("THE Goose");
    expect(line).toContain("calendar");
    expect(line).toContain("attention");
  });

  it("names blocked news", () => {
    const line = courierLine(
      baseBundle({
        unavailable_sources: ["news"],
        courier_state: "blocked",
      }),
    );
    expect(line).toContain("live news");
  });

  it("derives Goose state in the presentation layer only", () => {
    const state = deriveGooseState(
      baseBundle({
        evidence: [{ source: "calendar", evidence_ids: ["evt_1"] }],
        courier_state: "partially_returned",
      }),
    );
    expect(state).toBe("huffing");
  });
});
