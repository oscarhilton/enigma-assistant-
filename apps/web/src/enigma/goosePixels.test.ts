import { describe, expect, it } from "vitest";
import {
  expressivenessFromRemoteContext,
  latestThreadActivities,
  licenceFromConversation,
  licenseGoosePixels,
  pixelsAllowedOn,
  workSnapshotFromConversation,
  type AgentWorkSnapshot,
} from "./goosePixels";
import { MOCK_ATTENTION_JAN19, MOCK_CONVERSATION, MOCK_LLM_TRACE_LLM } from "./fixtures";
import type { ConversationItem } from "./types";

const WORK: AgentWorkSnapshot = {
  exists: true,
  phase: "complete",
  semanticToken: "stable-work-1",
  inspectTarget: "item-obligation_token_audit",
  inspectLabels: ["Checked why this matters"],
};

const PLAYFUL_REMOTE = {
  relational_bootstrap: {
    kind: "relational_bootstrap",
    continuation: { culture_palette_available: true },
  },
};

const SERIOUS_REMOTE = {
  relational_bootstrap: {
    kind: "relational_bootstrap",
    continuation: { culture_palette_available: false },
  },
};

function turnWithTrace(remote: unknown = MOCK_LLM_TRACE_LLM.remote_context_sent): ConversationItem[] {
  return [
    {
      kind: "enigma_message",
      text: "Because the token inventory is unblocked.",
      at: MOCK_ATTENTION_JAN19.simulated_time,
      llm_trace: {
        ...MOCK_LLM_TRACE_LLM,
        remote_context_sent: remote as Record<string, unknown> | null,
      },
    },
  ];
}

describe("goose pixel licence", () => {
  it("NO_WORK: does not fabricate activity even when playful", () => {
    const licence = licenseGoosePixels(null, "playful");
    expect(licence.motion).toBe("absent");
    expect(licence.workSemanticToken).toBe("");
    expect(
      licenceFromConversation({ items: MOCK_CONVERSATION, busy: false, loading: false }).motion,
    ).toBe("absent");
  });

  it("WORK_EXISTS: motion corresponds to real work", () => {
    expect(licenseGoosePixels({ ...WORK, phase: "in_flight" }, "restrained").motion).toBe("walk");
    expect(licenseGoosePixels({ ...WORK, phase: "waiting" }, "restrained").motion).toBe("idle");
    expect(licenseGoosePixels(WORK, "restrained").motion).toBe("return");
    const fromTrace = workSnapshotFromConversation({
      items: turnWithTrace(),
      busy: false,
      loading: false,
    });
    expect(fromTrace.exists).toBe(true);
    expect(fromTrace.phase).toBe("complete");
    expect(latestThreadActivities(turnWithTrace()).some((event) => event.kind === "world.explained")).toBe(
      true,
    );
  });

  it("SERIOUS_FRAME: work remains visible; comic expression suppressed", () => {
    const serious = licenseGoosePixels(WORK, expressivenessFromRemoteContext(SERIOUS_REMOTE));
    expect(serious.motion).toBe("return");
    expect(serious.expressiveness).toBe("restrained");
    expect(serious.workSemanticToken).toBe(WORK.semanticToken);
  });

  it("PLAYFUL_FRAME: same semantic work may be playful", () => {
    const playful = licenseGoosePixels(WORK, expressivenessFromRemoteContext(PLAYFUL_REMOTE));
    expect(playful.motion).toBe("return");
    expect(playful.expressiveness).toBe("playful");
    expect(playful.workSemanticToken).toBe(WORK.semanticToken);
  });

  it("FRAME_CHANGE: presentation changes; AgentWork does not", () => {
    const itemsPlayful = turnWithTrace(PLAYFUL_REMOTE);
    const itemsSerious = turnWithTrace(SERIOUS_REMOTE);
    const before = licenceFromConversation({ items: itemsPlayful, busy: false, loading: false });
    const after = licenceFromConversation({ items: itemsSerious, busy: false, loading: false });
    expect(before.motion).toBe(after.motion);
    expect(before.workSemanticToken).toBe(after.workSemanticToken);
    expect(before.inspectTarget).toBe(after.inspectTarget);
    expect(before.inspectLabels).toEqual(after.inspectLabels);
    expect(before.expressiveness).toBe("playful");
    expect(after.expressiveness).toBe("restrained");
  });

  it("busy in-flight work is walk regardless of frame", () => {
    const licence = licenceFromConversation({
      items: turnWithTrace(SERIOUS_REMOTE),
      busy: true,
      loading: false,
    });
    expect(licence.motion).toBe("walk");
    expect(licence.expressiveness).toBe("restrained");
  });

  it("pending assist is idle work, not fabricated wandering", () => {
    const items: ConversationItem[] = [
      {
        kind: "assist_proposal",
        at: MOCK_ATTENTION_JAN19.simulated_time,
        proposal: {
          id: "assist-token",
          title: "Draft colour + spacing token inventory",
          description: "Prepare the inventory",
          action_label: "Approve",
        },
      },
    ];
    const snapshot = workSnapshotFromConversation({ items, busy: false, loading: false });
    expect(snapshot.phase).toBe("waiting");
    expect(licenseGoosePixels(snapshot, "playful").motion).toBe("idle");
  });

  it("LAYER_01 / AUTHORITY_01: SURFACE only; never evidence or authority", () => {
    const licence = licenseGoosePixels(WORK, "playful");
    expect(licence.layer).toBe("surface");
    expect(licence.grantsAuthority).toBe(false);
    expect(licence.isEvidence).toBe(false);
    expect(pixelsAllowedOn("surface", licence)).toBe(true);
    expect(pixelsAllowedOn("inspectable", licence)).toBe(false);
    expect(pixelsAllowedOn("forensic", licence)).toBe(false);
    expect(pixelsAllowedOn("surface", licenseGoosePixels(null, "playful"))).toBe(false);
  });
});
