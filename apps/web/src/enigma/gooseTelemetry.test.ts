import { describe, expect, it } from "vitest";
import { licenseGoosePixels, type AgentWorkSnapshot, type GoosePixelLicence } from "./goosePixels";
import {
  FORBIDDEN_GOOSE_TELEMETRY_EVENTS,
  GOOSE_TELEMETRY_EVENTS,
  impliedMeaning,
  inspectGooseEvent,
  installGooseTelemetrySink,
  isForbiddenGooseTelemetry,
  projectGooseEvents,
  recordGooseTelemetry,
} from "./gooseTelemetry";

const WORK: AgentWorkSnapshot = {
  exists: true,
  phase: "in_flight",
  semanticToken: "retrieve-attention",
  inspectTarget: "item-obligation_token_audit",
  inspectLabels: ["Looking up what needs you"],
};

const DONE: AgentWorkSnapshot = {
  ...WORK,
  phase: "complete",
  inspectLabels: ["Checked why this matters"],
};

function licence(work: AgentWorkSnapshot | null, expressiveness: GoosePixelLicence["expressiveness"]) {
  return licenseGoosePixels(work, expressiveness);
}

describe("goose telemetry", () => {
  it("allowlists meaning events and forbids engagement scores", () => {
    expect([...GOOSE_TELEMETRY_EVENTS]).toEqual([
      "goose_became_visible",
      "goose_motion_started",
      "goose_returned",
      "goose_inspected",
      "agent_work_changed",
      "frame_expression_changed",
    ]);
    expect([...FORBIDDEN_GOOSE_TELEMETRY_EVENTS]).toEqual([
      "goose_clicked_17_times",
      "goose_engagement_score",
      "user_affection",
      "daily_goose_retention",
    ]);
    expect(isForbiddenGooseTelemetry("goose_engagement_score")).toBe(true);
  });

  it("walks when work starts and returns when work completes", () => {
    const started = projectGooseEvents(null, licence(WORK, "playful"));
    expect(started.map((event) => event.name)).toEqual([
      "agent_work_changed",
      "goose_became_visible",
      "goose_motion_started",
    ]);
    expect(started[0]?.motion).toBe("walk");
    const finished = projectGooseEvents(licence(WORK, "playful"), licence(DONE, "playful"));
    expect(finished.map((event) => event.name)).toContain("goose_returned");
    expect(finished.some((event) => event.name === "agent_work_changed")).toBe(true);
  });

  it("frame change emits presentation-only telemetry", () => {
    const playful = licence(WORK, "playful");
    const serious = licence(WORK, "restrained");
    const events = projectGooseEvents(playful, serious);
    expect(events.map((event) => event.name)).toEqual(["frame_expression_changed"]);
    expect(events[0]?.motion).toBe("walk");
    expect(events[0]?.workSemanticToken).toBe(WORK.semanticToken);
  });

  it("no work emits nothing performative", () => {
    const absent = licence(null, "playful");
    expect(projectGooseEvents(null, absent)).toEqual([]);
    expect(projectGooseEvents(absent, absent)).toEqual([]);
  });

  it("inspect payload matches the implied animation", () => {
    const walking = licence(WORK, "restrained");
    const inspected = inspectGooseEvent(walking);
    expect(inspected.name).toBe("goose_inspected");
    expect(inspected.inspectLabels).toEqual(["Looking up what needs you"]);
    expect(inspected.impliedMeaning).toBe(impliedMeaning("walk"));
    expect(impliedMeaning("idle")).toBe("looks finished");
    expect(impliedMeaning("return")).toBe("returned with a result");
  });

  it("records into a local sink and refuses engagement names", () => {
    const buffer: ReturnType<typeof projectGooseEvents> = [];
    installGooseTelemetrySink(buffer);
    recordGooseTelemetry(projectGooseEvents(null, licence(WORK, "playful")));
    expect(buffer.some((event) => event.name === "goose_became_visible")).toBe(true);
    installGooseTelemetrySink(null);
    expect(() =>
      recordGooseTelemetry([
        {
          name: "goose_engagement_score" as never,
          motion: "walk",
          previousMotion: null,
          workPhase: "in_flight",
          workSemanticToken: "x",
          expressiveness: "playful",
          inspectTarget: null,
          inspectLabels: [],
          impliedMeaning: "actively working",
        },
      ]),
    ).toThrow(/engagement telemetry is forbidden/);
  });
});
