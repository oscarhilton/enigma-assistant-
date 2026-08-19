import { describe, expect, it } from "vitest";
import type { LlmTrace } from "../../enigma/types";
import {
  bindForensicTurn,
  calendarNegativeEvidenceFromTurn,
  streamTraceHasTurnComplete,
} from "./forensicTurn";
import { buildForensicModel } from "./buildForensicModel";
import { buildCopyBundle, parseCopyBundle } from "./copyBundles";
import { projectStreamTrace, type CapturedStreamEvent } from "../streamTrace";
import type { ConversationStreamEvent } from "../streamTypes";

const T0 = Date.parse("2026-01-19T20:31:04.000Z");

function capture(atOffsetMs: number, event: ConversationStreamEvent): CapturedStreamEvent {
  return { capturedAt: T0 + atOffsetMs, event };
}

const work = (phase: "in_flight" | "complete") =>
  ({
    type: "agent_work",
    data: {
      exists: true,
      phase,
      semanticToken: phase === "complete" ? "Checked calendar" : "in-flight",
      inspectTarget: null,
      inspectLabels: phase === "complete" ? ["Checked calendar"] : [],
    },
  }) satisfies ConversationStreamEvent;

describe("FORENSIC_TURN_BINDING", () => {
  it("forbids Turn: none when the trace contains TURN complete", () => {
    const llmTrace: LlmTrace = {
      path: "llm",
      planner: "private",
      user_message: "Anything on my calendar today?",
      conversation_state: { current_subject_id: null, current_subject_kind: null },
      tools_available: ["availability.check"],
      model_tool_request: [],
      executed_tool_request: [{ name: "availability.check", arguments: { period: "today" } }],
      tool_results: [
        {
          name: "availability.check",
          ok: true,
          data: { period: "today", calendar_items: [] },
        },
      ],
      model_response: [],
      correlation_id: "corr-calendar-empty-001",
    };

    const captured: CapturedStreamEvent[] = [
      capture(1, work("in_flight")),
      capture(2, { type: "prose", data: { delta: "I don't see anything in your calendar today." } }),
      capture(3, work("complete")),
      capture(
        4,
        {
          type: "turn_complete",
          data: {
            items: [
              {
                kind: "enigma_message",
                text: "I don't see anything in your calendar today.",
                at: "2026-01-19T10:00:00+00:00",
              },
            ],
            conversation: {
              items: [
                {
                  kind: "user_message",
                  text: "Anything on my calendar today?",
                  at: "2026-01-19T10:00:00+00:00",
                },
                {
                  kind: "enigma_message",
                  text: "I don't see anything in your calendar today.",
                  at: "2026-01-19T10:00:00+00:00",
                },
              ],
            },
            llm_trace: llmTrace,
            calendar_facts_used: [],
          },
        },
      ),
    ];

    const streamingTrace = projectStreamTrace(captured);
    const forensicTurn = bindForensicTurn(captured, {
      text: "Anything on my calendar today?",
      at: "2026-01-19T10:00:00+00:00",
    });

    expect(streamTraceHasTurnComplete(streamingTrace)).toBe(true);
    expect(forensicTurn?.turnIndex).toBe(1);
    expect(forensicTurn?.llmTrace?.correlation_id).toBe("corr-calendar-empty-001");
    expect(forensicTurn?.agentWork?.exists).toBe(true);
    expect(forensicTurn?.agentWork?.phase).toBe("complete");

    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "my_enigma",
      provenance: null,
      streamingTrace,
      forensicTurn,
    });

    expect(model.snapshot.turnIndex).toBe(1);
    expect(model.snapshot.turnCount).toBe(1);
    expect(model.snapshot.correlationId).toBe("corr-calendar-empty-001");
    expect(model.userInput.data.text).toBe("Anything on my calendar today?");
    expect(model.agentWork.status).toBe("wired");
    expect(model.agentWork.data.phase).toBe("complete");

    const bundle = buildCopyBundle(model, "detailed");
    expect(bundle).toContain("Turn: 1 / 1");
    expect(bundle).not.toContain("Turn: none");
  });
});

describe("NEGATIVE_EVIDENCE", () => {
  it("shows calendar scope was checked when the answer is empty", () => {
    const negative = calendarNegativeEvidenceFromTurn({
      calendarFactsUsed: [],
      llmTrace: {
        path: "llm",
        planner: "private",
        user_message: "Anything today?",
        conversation_state: { current_subject_id: null, current_subject_kind: null },
        tools_available: ["availability.check"],
        model_tool_request: [],
        executed_tool_request: [{ name: "availability.check", arguments: { period: "today" } }],
        tool_results: [
          {
            name: "availability.check",
            ok: true,
            data: { period: "today", calendar_items: [] },
          },
        ],
        model_response: [],
        correlation_id: "corr-calendar-empty-002",
      },
    });

    expect(negative).toEqual({
      checked: true,
      scope: "today",
      resultCount: 0,
      source: "availability.check",
    });

    const captured: CapturedStreamEvent[] = [
      capture(1, work("complete")),
      capture(
        2,
        {
          type: "turn_complete",
          data: {
            items: [],
            conversation: {
              items: [
                { kind: "user_message", text: "Anything today?", at: "2026-01-19T10:00:00+00:00" },
              ],
            },
            llm_trace: {
              path: "llm",
              planner: "private",
              user_message: "Anything today?",
              conversation_state: { current_subject_id: null, current_subject_kind: null },
              tools_available: ["availability.check"],
              model_tool_request: [],
              executed_tool_request: [{ name: "availability.check", arguments: { period: "today" } }],
              tool_results: [
                {
                  name: "availability.check",
                  ok: true,
                  data: { period: "today", calendar_items: [] },
                },
              ],
              model_response: [],
              correlation_id: "corr-calendar-empty-002",
            },
            calendar_facts_used: [],
          },
        },
      ),
    ];

    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "my_enigma",
      provenance: null,
      streamingTrace: projectStreamTrace(captured),
      forensicTurn: bindForensicTurn(captured),
    });

    expect(model.evidence.status).toBe("wired");
    expect(model.evidence.data.calendarNegativeEvidence).toEqual({
      checked: true,
      scope: "today",
      resultCount: 0,
      source: "availability.check",
    });

    const parsed = parseCopyBundle(buildCopyBundle(model, "detailed")) as {
      evidence: {
        calendar_negative_evidence: {
          scope: string;
          resultCount: number;
          source: string;
        };
      };
    };
    expect(parsed.evidence.calendar_negative_evidence).toEqual({
      checked: true,
      scope: "today",
      resultCount: 0,
      source: "availability.check",
    });
  });
});

describe("FORENSIC_NEGATIVE_EVIDENCE_02", () => {
  it("shows calendar scope was checked for empty world.explain calendar_items", () => {
    const negative = calendarNegativeEvidenceFromTurn({
      calendarFactsUsed: [],
      llmTrace: {
        path: "intent_router",
        planner: "private_calendar_read",
        user_message: "Get my events",
        conversation_state: {
          authority_ceiling: "READ_SUPPORT",
          capability_contract: { allowed: ["world.explain"], unavailable: [] },
        },
        tools_available: ["agenda.get", "world.explain"],
        model_tool_request: [],
        executed_tool_request: [{ name: "world.explain", arguments: {} }],
        tool_results: [{ name: "world.explain", ok: true, calendar_items: [] }],
        model_response: [],
        correlation_id: "corr-world-explain-empty-001",
      },
    });

    expect(negative).toEqual({
      checked: true,
      scope: "unknown",
      resultCount: 0,
      source: "world.explain",
    });
  });
});

describe("AUTHORITY_PROJECTION", () => {
  it("projects authority_ceiling from llm_trace conversation_state without inference", () => {
    const llmTrace: LlmTrace = {
      path: "intent_router",
      planner: "private_calendar_read",
      user_message: "Get my events",
      conversation_state: {
        authority_ceiling: "READ_SUPPORT",
        capability_contract: {
          allowed: ["agenda.get", "availability.check", "world.explain"],
          unavailable: ["assist.propose", "calendar.sync"],
        },
      },
      tools_available: ["agenda.get", "availability.check", "world.explain"],
      model_tool_request: [],
      executed_tool_request: [{ name: "agenda.get", arguments: { period: "this_week" } }],
      tool_results: [
        {
          name: "agenda.get",
          ok: true,
          data: { period: "this_week", calendar_items: [] },
        },
      ],
      model_response: [],
      correlation_id: "corr-authority-projection-001",
    };

    const captured: CapturedStreamEvent[] = [
      capture(1, work("complete")),
      capture(
        2,
        {
          type: "turn_complete",
          data: {
            items: [],
            conversation: {
              items: [{ kind: "user_message", text: "Get my events", at: "2026-01-19T10:00:00+00:00" }],
            },
            llm_trace: llmTrace,
            calendar_facts_used: [],
          },
        },
      ),
    ];

    const model = buildForensicModel({
      items: [],
      attention: null,
      busy: false,
      loading: false,
      world: "my_enigma",
      provenance: null,
      streamingTrace: projectStreamTrace(captured),
      forensicTurn: bindForensicTurn(captured),
    });

    expect(model.authority).toEqual({
      status: "wired",
      data: {
        authority_ceiling: "READ_SUPPORT",
        capability_contract: {
          allowed: ["agenda.get", "availability.check", "world.explain"],
          unavailable: ["assist.propose", "calendar.sync"],
        },
      },
    });

    const parsed = parseCopyBundle(buildCopyBundle(model, "detailed")) as {
      authority: {
        authority_ceiling: string;
        capability_contract: { allowed: string[] };
      };
    };
    expect(parsed.authority.authority_ceiling).toBe("READ_SUPPORT");
    expect(parsed.authority.capability_contract.allowed).toContain("agenda.get");
  });
});
