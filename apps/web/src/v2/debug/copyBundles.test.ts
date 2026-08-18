import { describe, expect, it } from "vitest";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM } from "../../enigma/fixtures";
import type { ConversationItem, LlmTrace } from "../../enigma/types";
import { buildForensicModel } from "./buildForensicModel";
import { buildCopyBundle, parseCopyBundle } from "./copyBundles";
import { NOT_CAPTURED } from "./types";

const items: ConversationItem[] = [
  {
    kind: "user_message",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    text: "Why do I need to do this?",
  },
  {
    kind: "enigma_message",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    text: "Because the token inventory is unblocked.",
    llm_trace: MOCK_LLM_TRACE_LLM,
  },
];

function baseModel() {
  return buildForensicModel({
    items,
    attention: MOCK_ATTENTION_JAN19,
    busy: false,
    loading: false,
    world: "alex_lab",
    provenance: null,
  });
}

function expectHeader(text: string, privacy: "SAFE" | "DETAILED" | "LOCAL") {
  const lines = text.split("\n");
  expect(lines[0]).toBe("ENIGMA FORENSIC SNAPSHOT");
  expect(lines[1]).toMatch(/^Build: /);
  expect(lines[2]).toMatch(/^World: /);
  expect(lines[3]).toMatch(/^Turn: /);
  expect(lines[4]).toBe(`Privacy level: ${privacy}`);
}

describe("copyBundles", () => {
  it("copies valid JSON for each tier after an unmistakable header", () => {
    const model = baseModel();
    const expected = { safe: "SAFE", detailed: "DETAILED", local: "LOCAL" } as const;
    for (const tier of ["safe", "detailed", "local"] as const) {
      const text = buildCopyBundle(model, tier);
      expectHeader(text, expected[tier]);
      const parsed = parseCopyBundle(text);
      expect(parsed).toBeTruthy();
      expect((parsed as { tier: string }).tier).toBe(tier === "local" ? "local_forensic" : tier);
    }
  });

  it("safe tier never includes raw user message text or private payloads", () => {
    const text = buildCopyBundle(baseModel(), "safe");
    expect(text).not.toContain("Why do I need to do this?");
    expect(text).not.toContain('"privateperson"');
    expect(text).not.toContain('"notes"');
    expect(text).toContain('"tier": "safe"');
  });

  it("detailed tier includes user input but strips private keys and does not invent unavailable projections", () => {
    const text = buildCopyBundle(baseModel(), "detailed");
    const parsed = parseCopyBundle(text) as {
      user_input: { text: string };
      tier: string;
      turn_contract: string;
      authority: string;
      streaming_trace: string;
      memory: string;
    };
    expect(parsed.tier).toBe("detailed");
    expect(parsed.user_input.text).toBe("Why do I need to do this?");
    expect(text.toLowerCase()).not.toContain("privateperson");
    expect(parsed.turn_contract).toBe(NOT_CAPTURED);
    expect(parsed.authority).toBe(NOT_CAPTURED);
    expect(parsed.streaming_trace).toBe(NOT_CAPTURED);
    expect(parsed.memory).toBe(NOT_CAPTURED);
    expect(text).not.toContain("grantsAuthority");
    expect(text).not.toContain("enigmaActions");
  });

  it("local forensic tier includes full trace", () => {
    const text = buildCopyBundle(baseModel(), "local");
    const parsed = parseCopyBundle(text) as { trace: { correlation_id: string } };
    expect(parsed.trace.correlation_id).toBe("corr-demo-orchestrate-001");
  });
});

describe("buildForensicModel", () => {
  it("builds turn snapshot from conversation and world state", () => {
    const model = baseModel();
    expect(model.snapshot.world).toBe("alex_lab");
    expect(model.snapshot.turnIndex).toBe(1);
    expect(model.snapshot.correlationId).toBe("corr-demo-orchestrate-001");
    expect(model.userInput.status).toBe("wired");
    expect(model.remotePayload.status).toBe("wired");
  });

  it("does not reconstruct unavailable projections from nearby fields", () => {
    const model = baseModel();
    expect(model.turnContract).toEqual({ status: "unavailable", data: null });
    expect(model.handoff).toEqual({ status: "unavailable", data: null });
    expect(model.relationalBootstrap).toEqual({ status: "unavailable", data: null });
    expect(model.authority).toEqual({ status: "unavailable", data: null });
    expect(model.streamingTrace).toEqual({ status: "unavailable", data: null });
    expect(model.memory).toEqual({ status: "unavailable", data: null });
    expect(model.whyNot).toEqual({
      status: "wired",
      data: {
        source: "can_wait_summary",
        total_suppressed: 1,
        sample_titles: [],
      },
    });
  });

  it("shows a named projection only when it is actually on the wire", () => {
    const trace: LlmTrace = {
      ...MOCK_LLM_TRACE_LLM,
      remote_context_sent: {
        ...(MOCK_LLM_TRACE_LLM.remote_context_sent as Record<string, unknown>),
        turn_contract: { intent: "explain_why" },
        relational_bootstrap: { kind: "relational_bootstrap" },
      },
    };
    const model = buildForensicModel({
      items: [
        items[0]!,
        { ...items[1]!, llm_trace: trace },
      ],
      attention: MOCK_ATTENTION_JAN19,
      busy: false,
      loading: false,
      world: "alex_lab",
      provenance: null,
    });
    expect(model.turnContract).toEqual({ status: "wired", data: { intent: "explain_why" } });
    expect(model.relationalBootstrap).toEqual({
      status: "wired",
      data: { kind: "relational_bootstrap" },
    });
    expect(model.handoff.status).toBe("unavailable");
  });
});
