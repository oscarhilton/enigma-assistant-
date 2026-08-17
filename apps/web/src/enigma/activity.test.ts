import { describe, expect, it } from "vitest";
import { projectActivityFromTrace, threadActivityFromTrace } from "./activity";
import { MOCK_LLM_TRACE_LLM, MOCK_LLM_TRACE_ROUTER } from "./fixtures";
import type { LlmTrace } from "./types";

function traceWithTools(tools: LlmTrace["tool_results"], extra?: Partial<LlmTrace>): LlmTrace {
  return {
    ...MOCK_LLM_TRACE_LLM,
    tool_results: tools,
    disclosure: null,
    ...extra,
  };
}

describe("projectActivityFromTrace", () => {
  it("maps world.explain to Checked why this matters", () => {
    const events = projectActivityFromTrace(MOCK_LLM_TRACE_LLM, { at: "2026-01-19T10:00:00Z" });
    expect(events.some((event) => event.kind === "world.explained")).toBe(true);
    expect(events.find((event) => event.kind === "world.explained")?.label).toBe(
      "Checked why this matters",
    );
  });

  it("maps availability.check to Checked your calendar", () => {
    const events = threadActivityFromTrace(
      traceWithTools([{ name: "availability.check", ok: true, data: {} }]),
    );
    expect(events).toEqual([
      expect.objectContaining({
        kind: "availability.checked",
        label: "Checked your calendar",
        forensic_only: false,
      }),
    ]);
  });

  it("omits failed tool hops", () => {
    const events = threadActivityFromTrace(
      traceWithTools([{ name: "availability.check", ok: false, data: {} }]),
    );
    expect(events).toEqual([]);
  });

  it("omits assist hops from the thread strip (cards, not theatre)", () => {
    const events = threadActivityFromTrace(
      traceWithTools([{ name: "assist.propose", ok: true, data: {} }]),
    );
    expect(events).toEqual([]);
  });

  it("marks egress.allowed forensic-only and hides it from the thread strip", () => {
    const all = projectActivityFromTrace(MOCK_LLM_TRACE_LLM);
    const egress = all.find((event) => event.kind === "egress.allowed");
    expect(egress?.forensic_only).toBe(true);
    expect(threadActivityFromTrace(MOCK_LLM_TRACE_LLM).some((event) => event.kind === "egress.allowed")).toBe(
      false,
    );
  });

  it("emits nothing for a router turn with no tools", () => {
    expect(threadActivityFromTrace(MOCK_LLM_TRACE_ROUTER)).toEqual([]);
  });

  it("maps attention and referent hops to the product labels", () => {
    const events = threadActivityFromTrace(
      traceWithTools([
        { name: "attention.get_current", ok: true, data: {} },
        { name: "context.resolve_referent", ok: true, data: {} },
      ]),
    );
    expect(events.map((event) => event.label)).toEqual([
      "Checked what needs you",
      "Matched this to the token inventory",
    ]);
  });
});
