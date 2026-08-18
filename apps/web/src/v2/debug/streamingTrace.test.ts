import { describe, expect, it } from "vitest";
import { formatLane, projectStreamTrace } from "../streamTrace";
import type { ConversationStreamEvent } from "../streamTypes";
import { buildForensicModel } from "./buildForensicModel";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM } from "../../enigma/fixtures";
import type { ConversationItem } from "../../enigma/types";

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
      work("in_flight"),
      prose("Team "),
      work("complete"),
      prose("standup"),
      { type: "turn_complete", data: { items: [] } },
    ]);
    expect(projection).toEqual({
      prose: { steps: ["chunk", "chunk", "complete"] },
      agentWork: { steps: ["investigating", "handled"] },
    });
    expect(formatLane(projection!.prose.steps)).toBe("chunk → chunk → complete");
    expect(formatLane(projection!.agentWork.steps)).toBe("investigating → handled");
    expect(projection!.prose.steps).not.toContain("investigating");
    expect(projection!.agentWork.steps).not.toContain("chunk");
  });

  it("maps waiting to waiting / verifying without inventing missing steps", () => {
    const projection = projectStreamTrace([
      work("in_flight"),
      work("in_flight"),
      work("waiting"),
      work("complete"),
    ]);
    expect(projection?.agentWork.steps).toEqual([
      "investigating",
      "advancing",
      "waiting / verifying",
      "handled",
    ]);
    expect(projection?.prose.steps).toEqual([]);
  });

  it("returns null when no stream events were captured", () => {
    expect(projectStreamTrace([])).toBeNull();
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
    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "my_enigma",
      provenance: null,
      streamingTrace: {
        prose: { steps: ["chunk", "complete"] },
        agentWork: { steps: ["investigating", "handled"] },
      },
    });
    expect(model.streamingTrace.status).toBe("wired");
    expect(model.streamingTrace.data?.prose.steps).toEqual(["chunk", "complete"]);
  });
});
