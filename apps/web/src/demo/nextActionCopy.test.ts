import { describe, expect, it } from "vitest";
import { FIXTURE_ATTENTION } from "./fixtures";
import {
  cycleNextIndex,
  durationFromAttention,
  FIXTURE_NEXT_ACTIONS,
  nextActionFromAttention,
  nextActionLine,
  nextSectionLabel,
  nextTitleFromAttention,
  resolveNextActionCandidates,
} from "./nextActionCopy";

describe("nextActionCopy", () => {
  it("derives NEXT from top attention without Attention chrome", () => {
    const atlas = FIXTURE_ATTENTION[0]!;
    const next = nextActionFromAttention(atlas);
    expect(nextTitleFromAttention(atlas)).toBe("Review the Atlas proposal");
    expect(nextActionLine(next)).toBe("Review the Atlas proposal · ~20 min");
    expect(next.optional).toBe(true);
    expect(next.category).toBe("obligation");
    expect(durationFromAttention(atlas)).toBe("~20 min");
  });

  it("keeps soft stubs optional and includes rest", () => {
    expect(FIXTURE_NEXT_ACTIONS.every((a) => a.optional)).toBe(true);
    expect(FIXTURE_NEXT_ACTIONS.some((a) => a.category === "rest")).toBe(true);
    expect(FIXTURE_NEXT_ACTIONS.some((a) => a.category === "movement")).toBe(true);
  });

  it("empty attention uses soft candidates with rest; never obligation-only", () => {
    const candidates = resolveNextActionCandidates([]);
    expect(candidates.length).toBeGreaterThan(0);
    expect(candidates[0]!.title).toMatch(/walk/i);
    expect(candidates.every((a) => a.optional)).toBe(true);
    expect(candidates.every((a) => a.category !== "obligation")).toBe(true);
    expect(candidates.some((a) => a.category === "rest")).toBe(true);
  });

  it("non-empty attention leads with derived obligation then soft options", () => {
    const candidates = resolveNextActionCandidates(FIXTURE_ATTENTION);
    expect(candidates[0]!.id).toBe("next-from-att-atlas-review");
    expect(candidates[0]!.category).toBe("obligation");
    expect(candidates.slice(1).every((a) => a.category !== "obligation")).toBe(
      true,
    );
    expect(nextSectionLabel(false)).toBe("NEXT");
    expect(nextSectionLabel(true)).toBe("YOU COULD");
  });

  it("cycles something-else index", () => {
    expect(cycleNextIndex(0, 4)).toBe(1);
    expect(cycleNextIndex(3, 4)).toBe(0);
  });
});
