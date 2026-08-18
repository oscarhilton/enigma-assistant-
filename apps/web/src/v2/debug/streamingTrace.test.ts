import { describe, expect, it } from "vitest";
import {
  formatLane,
  formatStreamTimeline,
  formatTimelineLine,
  projectStreamTrace,
  type CapturedStreamEvent,
} from "../streamTrace";
import type { ConversationStreamEvent } from "../streamTypes";
import { buildForensicModel } from "./buildForensicModel";
import { buildCopyBundle, parseCopyBundle } from "./copyBundles";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM } from "../../enigma/fixtures";
import type { ConversationItem } from "../../enigma/types";

const T0 = Date.parse("2026-01-19T20:31:04.000Z");

function capture(atOffsetMs: number, event: ConversationStreamEvent): CapturedStreamEvent {
  return { capturedAt: T0 + atOffsetMs, event };
}

const work = (phase: "in_flight" | "waiting" | "complete"): ConversationStreamEvent => ({
  type: "agent_work",
  data: {
    exists: true,
    phase,
    semanticToken: phase,
    inspectTarget: null,
    inspectLabels: [],
  },
});

const prose = (delta: string): ConversationStreamEvent => ({
  type: "prose",
  data: { delta },
});

describe("projectStreamTrace", () => {
  it("keeps assistant output and agent work lanes independent", () => {
    const projection = projectStreamTrace([
      capture(102, work("in_flight")),
      capture(241, prose("Team ")),
      capture(611, work("complete")),
      capture(744, prose("standup")),
      capture(801, { type: "turn_complete", data: { items: [] } }),
    ]);
    expect(projection).toEqual({
      prose: { steps: ["chunk", "chunk", "complete"] },
      agentWork: { steps: ["investigating", "handled"] },
      timeline: [
        { capturedAt: T0 + 102, kind: "WORK", detail: "in_flight" },
        { capturedAt: T0 + 241, kind: "PROSE", detail: '"Team "' },
        { capturedAt: T0 + 611, kind: "WORK", detail: "complete" },
        { capturedAt: T0 + 744, kind: "PROSE", detail: '"standup"' },
        { capturedAt: T0 + 801, kind: "TURN", detail: "complete" },
      ],
      formatted: [
        "STREAM TRACE",
        "─────────────────────────────",
        "",
        formatTimelineLine({ capturedAt: T0 + 102, kind: "WORK", detail: "in_flight" }),
        formatTimelineLine({ capturedAt: T0 + 241, kind: "PROSE", detail: '"Team "' }),
        formatTimelineLine({ capturedAt: T0 + 611, kind: "WORK", detail: "complete" }),
        formatTimelineLine({ capturedAt: T0 + 744, kind: "PROSE", detail: '"standup"' }),
        formatTimelineLine({ capturedAt: T0 + 801, kind: "TURN", detail: "complete" }),
      ].join("\n"),
    });
    expect(formatLane(projection!.prose.steps)).toBe("chunk → chunk → complete");
    expect(formatLane(projection!.agentWork.steps)).toBe("investigating → handled");
    expect(projection!.prose.steps).not.toContain("investigating");
    expect(projection!.agentWork.steps).not.toContain("chunk");
  });

  it("orders timeline chronologically with WORK before and after PROSE", () => {
    const projection = projectStreamTrace([
      capture(100, work("in_flight")),
      capture(200, prose("I")),
      capture(300, prose(" can")),
      capture(400, work("complete")),
      capture(500, prose(" check")),
      capture(600, { type: "turn_complete", data: { items: [] } }),
    ]);
    expect(projection?.timeline.map((entry) => entry.kind)).toEqual([
      "WORK",
      "PROSE",
      "PROSE",
      "WORK",
      "PROSE",
      "TURN",
    ]);
    expect(projection?.timeline[0]?.detail).toBe("in_flight");
    expect(projection?.timeline[1]?.detail).toBe('"I"');
    expect(projection?.timeline[3]?.detail).toBe("complete");
    expect(projection?.timeline.at(-1)?.kind).toBe("TURN");
  });

  it("maps waiting to waiting / verifying without inventing missing steps", () => {
    const projection = projectStreamTrace([
      capture(1, work("in_flight")),
      capture(2, work("in_flight")),
      capture(3, work("waiting")),
      capture(4, work("complete")),
    ]);
    expect(projection?.agentWork.steps).toEqual([
      "investigating",
      "advancing",
      "waiting / verifying",
      "handled",
    ]);
    expect(projection?.prose.steps).toEqual([]);
    expect(projection?.timeline.map((entry) => entry.detail)).toEqual([
      "in_flight",
      "in_flight",
      "waiting",
      "complete",
    ]);
  });

  it("includes ERROR events on the timeline", () => {
    const projection = projectStreamTrace([
      capture(1, work("in_flight")),
      capture(2, { type: "error", data: { message: "dropped" } }),
    ]);
    expect(projection?.timeline).toEqual([
      { capturedAt: T0 + 1, kind: "WORK", detail: "in_flight" },
      { capturedAt: T0 + 2, kind: "ERROR", detail: "dropped" },
    ]);
  });

  it("returns null when no stream events were captured", () => {
    expect(projectStreamTrace([])).toBeNull();
  });
});

describe("formatStreamTimeline", () => {
  it("renders Oscar-style chronological log header and lines", () => {
    const text = formatStreamTimeline([
      { capturedAt: T0 + 102, kind: "WORK", detail: "in_flight" },
      { capturedAt: T0 + 241, kind: "PROSE", detail: '"I"' },
      { capturedAt: T0 + 801, kind: "TURN", detail: "complete" },
    ]);
    expect(text).toContain("STREAM TRACE");
    expect(text).toContain("─────────────────────────────");
    expect(text).toContain('PROSE  "I"');
    expect(text).toContain("TURN   complete");
  });
});

describe("buildForensicModel streamingTrace", () => {
  it("does not reconstruct a streaming trace from the assistant message", () => {
    const items: ConversationItem[] = [
      { kind: "user_message", at: MOCK_ATTENTION_JAN19.simulated_time, text: "What's on?" },
      {
        kind: "enigma_message",
        at: MOCK_ATTENTION_JAN19.simulated_time,
        text: "Team standup",
        llm_trace: MOCK_LLM_TRACE_LLM,
      },
    ];
    const model = buildForensicModel({
      items,
      attention: MOCK_ATTENTION_JAN19,
      busy: false,
      loading: false,
      world: "alex_lab",
      provenance: null,
    });
    expect(model.streamingTrace).toEqual({ status: "unavailable", data: null });
  });

  it("wires STREAMING TRACE only from a captured stream projection", () => {
    const trace = projectStreamTrace([
      capture(1, work("in_flight")),
      capture(2, { type: "turn_complete", data: { items: [] } }),
    ]);
    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "my_enigma",
      provenance: null,
      streamingTrace: trace,
    });
    expect(model.streamingTrace.status).toBe("wired");
    expect(model.streamingTrace.data?.timeline).toHaveLength(2);
    expect(model.streamingTrace.data?.formatted).toContain("STREAM TRACE");
  });
});

describe("copyBundles streaming trace", () => {
  it("includes formatted timeline in detailed bundle when captured", () => {
    const trace = projectStreamTrace([
      capture(102, work("in_flight")),
      capture(241, prose("I")),
      capture(801, { type: "turn_complete", data: { items: [] } }),
    ]);
    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "my_enigma",
      provenance: null,
      streamingTrace: trace,
    });
    const parsed = parseCopyBundle(buildCopyBundle(model, "detailed")) as {
      streaming_trace: { formatted: string; timeline: unknown[] };
    };
    expect(parsed.streaming_trace.formatted).toContain("STREAM TRACE");
    expect(parsed.streaming_trace.timeline).toHaveLength(3);
  });

  it("shows Not captured for one-shot turns in detailed bundle", () => {
    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "alex_lab",
      provenance: null,
    });
    const parsed = parseCopyBundle(buildCopyBundle(model, "detailed")) as {
      streaming_trace: string;
    };
    expect(parsed.streaming_trace).toBe("Not captured for this turn");
  });
});
