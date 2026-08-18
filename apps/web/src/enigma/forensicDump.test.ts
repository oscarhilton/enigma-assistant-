import { describe, expect, it } from "vitest";
import {
  formatLastTurnDump,
  formatSessionDump,
  stitchLlmTrace,
  tracesFromItems,
} from "./forensicDump";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM, MOCK_LLM_TRACE_ROUTER } from "./fixtures";
import type { ConversationItem } from "./types";

const items: ConversationItem[] = [
  {
    kind: "user_message",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    text: "What should I do next?",
  },
  {
    kind: "next_action",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    action: MOCK_ATTENTION_JAN19.next_actions[0]!,
    llm_trace: MOCK_LLM_TRACE_ROUTER,
  },
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

describe("forensicDump", () => {
  it("collects one trace per assistant run", () => {
    expect(tracesFromItems(items)).toEqual([MOCK_LLM_TRACE_ROUTER, MOCK_LLM_TRACE_LLM]);
  });

  it("formats a session dump with under-bonnet labels", () => {
    const dump = formatSessionDump(tracesFromItems(items));
    expect(dump).toContain("# Enigma forensic dump");
    expect(dump).toContain("Turns: 2");
    expect(dump).toContain("======== Turn 1 of 2 ========");
    expect(dump).toContain("PATH\nintent_router");
    expect(dump).toContain("CORRELATION\ncorr-router-001");
    expect(dump).toContain("USER MESSAGE\nWhat should I do next?");
    expect(dump).toContain("CONVERSATION STATE\nitem-obligation_token_audit (next_action)");
    expect(dump).toContain("INTENT\nnext_action_query");
    expect(dump).toContain("TOOLS AVAILABLE\n");
    expect(dump).toContain("REMOTE CONTEXT SENT\nnone");
    expect(dump).toContain("MODEL TOOL REQUEST\nnone — router fallback");
    expect(dump).toContain("TOOL RESULT\nnone");
    expect(dump).toContain("MODEL RESPONSE");
    expect(dump).toContain("Privacy disclosure");
    expect(dump).toContain("No remote payload — intent_router fallback handled this turn.");
    expect(dump).toContain("======== Turn 2 of 2 ========");
    expect(dump).toContain("PATH\nllm");
    expect(dump).toContain("CORRELATION\ncorr-demo-orchestrate-001");
    expect(dump).toContain("USER MESSAGE\nWhy do I need to do this?");
    expect(dump).toContain('"name": "world.explain"');
    expect(dump).toContain("Provider\nfireworks/accounts/fireworks/models/gpt-oss-120b");
    expect(dump).toContain("Purpose\nconversation.orchestrate");
    expect(dump).toContain("PRIVATE_RAW");
  });

  it("formats only the latest turn", () => {
    const dump = formatLastTurnDump(tracesFromItems(items));
    expect(dump).toContain("# Enigma forensic dump (last turn)");
    expect(dump).toContain("======== Turn 2 of 2 ========");
    expect(dump).toContain("PATH\nllm");
    expect(dump).not.toContain("PATH\nintent_router");
    expect(dump).not.toContain("What should I do next?");
  });

  it("stitches a missing turn trace onto the last assistant run", () => {
    const withoutTrace: ConversationItem[] = [
      { kind: "user_message", at: MOCK_ATTENTION_JAN19.simulated_time, text: "Why?" },
      {
        kind: "enigma_message",
        at: MOCK_ATTENTION_JAN19.simulated_time,
        text: "Because.",
      },
    ];
    const stitched = stitchLlmTrace(withoutTrace, MOCK_LLM_TRACE_LLM);
    expect(stitched[1]?.llm_trace).toEqual(MOCK_LLM_TRACE_LLM);
  });

  it("does not overwrite a trace already stored on the run", () => {
    const stitched = stitchLlmTrace(items, MOCK_LLM_TRACE_LLM);
    expect(stitched).toBe(items);
  });
});
