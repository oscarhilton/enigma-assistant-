import { describe, expect, it } from "vitest";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM } from "../../enigma/fixtures";
import type { ConversationItem } from "../../enigma/types";
import { buildForensicModel } from "./buildForensicModel";
import { buildCopyBundle, parseCopyBundle } from "./copyBundles";

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
    disclosures: [],
  });
}

describe("copyBundles", () => {
  it("copies valid JSON for each tier", () => {
    const model = baseModel();
    for (const tier of ["safe", "detailed", "local"] as const) {
      const text = buildCopyBundle(model, tier);
      const parsed = parseCopyBundle(text);
      expect(parsed).toBeTruthy();
      expect((parsed as { tier: string }).tier).toBe(
        tier === "local" ? "local_forensic" : tier,
      );
    }
  });

  it("safe tier never includes raw user message text or private payloads", () => {
    const text = buildCopyBundle(baseModel(), "safe");
    expect(text).not.toContain("Why do I need to do this?");
    expect(text).not.toContain('"privateperson"');
    expect(text).not.toContain('"notes"');
    expect(text).toContain('"tier": "safe"');
  });

  it("detailed tier includes user input but strips private keys", () => {
    const text = buildCopyBundle(baseModel(), "detailed");
    const parsed = parseCopyBundle(text) as {
      user_input: { text: string };
      tier: string;
    };
    expect(parsed.tier).toBe("detailed");
    expect(parsed.user_input.text).toBe("Why do I need to do this?");
    expect(text.toLowerCase()).not.toContain("privateperson");
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
});
