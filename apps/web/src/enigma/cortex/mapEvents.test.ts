import { describe, expect, it } from "vitest";
import type { DemoEvent, EgressDisclosure } from "../types";
import { resetBrainEventIdsForTests, projectDemoEvent, projectEgressDisclosure } from "./mapEvents";

describe("mapEvents", () => {
  it("maps demo attention events to upper region", () => {
    resetBrainEventIdsForTests();
    const [event] = projectDemoEvent({
      kind: "attention_surfaced",
      at: "2026-01-19T10:00:00+00:00",
      needs_you_count: 3,
    } satisfies DemoEvent);
    expect(event?.type).toBe("attention_qualified");
    expect(event?.region).toBe("upper");
  });

  it("maps blocked egress to privacy_transform", () => {
    resetBrainEventIdsForTests();
    const event = projectEgressDisclosure({
      id: "disc-blocked",
      correlation_id: "corr-1",
      timestamp: "2026-01-19T10:00:00+00:00",
      purpose: "reasoning.semantic_judge",
      provider: "openai",
      model: "gpt-4",
      transformation_profile: "semantic_judge_v1",
      payload_field_summary: {},
      payload_hash: "abc",
      byte_count: 0,
      blocked: true,
      block_reason: "classification HIGH",
      classification: "HIGH",
      prompt_tokens: 0,
      completion_tokens: 0,
    } satisfies EgressDisclosure);
    expect(event.type).toBe("privacy_transform");
    if (event.type === "privacy_transform") {
      expect(event.blocked).toBe(true);
    }
  });

  it("maps sent egress to egress event", () => {
    resetBrainEventIdsForTests();
    const event = projectEgressDisclosure({
      id: "disc-sent",
      correlation_id: "corr-2",
      timestamp: "2026-01-19T10:01:00+00:00",
      purpose: "conversation.orchestrate",
      provider: "openai",
      model: "gpt-4",
      transformation_profile: "orchestrate_v1",
      payload_field_summary: {},
      payload_hash: "def",
      byte_count: 120,
      blocked: false,
      classification: "LOW",
      prompt_tokens: 10,
      completion_tokens: 5,
    } satisfies EgressDisclosure);
    expect(event.type).toBe("egress");
  });
});
