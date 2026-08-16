import { describe, expect, it } from "vitest";
import {
  canWaitLabel,
  cardReason,
  compactBadges,
  defaultCanWaitGroups,
  deriveNaturalReason,
  holdingSignalsNote,
  isEvidenceDumpBody,
  lastEvaluatedLabel,
  mattersNowHeadline,
  priorityLabel,
  resolveCanWaitGroups,
  timingLabel,
} from "./attentionCardCopy";
import { FIXTURE_CAN_WAIT_GROUPS, FIXTURE_SUPPRESSED } from "./fixtures";
import type { DemoAttentionItem } from "./types";

function item(overrides: Partial<DemoAttentionItem> = {}): DemoAttentionItem {
  return {
    id: "att-test",
    title: "Review Atlas proposal before Friday",
    when: "Before Friday",
    why_now_glance: "Deadline approaching",
    body: "You said you'd review this before Friday, and it still appears unfinished.",
    kind: "commitment",
    priority: 4,
    confidence: 0.91,
    attention_rank: 0.86,
    evidence_ids: ["ev-mail-1"],
    ...overrides,
  };
}

describe("attentionCardCopy", () => {
  it("detects obligations-style evidence dumps", () => {
    expect(
      isEvidenceDumpBody(
        "Reminder: Review proposal; Email: Re: Proposal; Calendar: Proposal review",
      ),
    ).toBe(true);
    expect(isEvidenceDumpBody("Email: alone is still a dump")).toBe(true);
    expect(
      isEvidenceDumpBody(
        "You said you'd review this before Friday, and it still appears unfinished.",
      ),
    ).toBe(false);
  });

  it("prefers natural body sentences and never surfaces evidence dumps", () => {
    expect(cardReason(item())).toBe(
      "You said you'd review this before Friday, and it still appears unfinished.",
    );
    expect(
      cardReason(
        item({
          title: "Follow up with Maya on scheduling",
          when: null,
          why_now_glance: "Thread waiting on you",
          body: "Maya is still waiting for a scheduling response.",
          kind: "follow_up",
          priority: 3,
        }),
      ),
    ).toBe("Maya is still waiting for a scheduling response.");
    expect(
      cardReason(
        item({
          why_now_glance: "Deadline approaching",
          body: "Reminder: Review proposal; Email: Re: Proposal",
        }),
      ),
    ).toBe(
      "You said you'd review this before friday, and it still appears unfinished.",
    );
    expect(
      cardReason(
        item({
          why_now_glance: null,
          when: null,
          body: "Reminder: Review proposal; Email: Re: Proposal",
        }),
      ),
    ).toBeNull();
  });

  it("derives natural reasons when body is an evidence dump", () => {
    expect(
      deriveNaturalReason(
        item({
          body: "Reminder: Review proposal; Email: Re: Proposal",
        }),
      ),
    ).toMatch(/review this before friday/i);
    expect(
      deriveNaturalReason(
        item({
          title: "Follow up with Maya on scheduling",
          when: null,
          why_now_glance: "Thread waiting on you",
          body: "Reminder: Scheduling; Email: Re: times",
          kind: "follow_up",
          priority: 3,
        }),
      ),
    ).toBe("Maya is still waiting for a scheduling response.");
  });

  it("builds compact priority · timing badges", () => {
    expect(priorityLabel(4)).toBe("HIGH PRIORITY");
    expect(timingLabel(item())).toBe("DUE SOON");
    expect(compactBadges(item())).toEqual(["HIGH PRIORITY", "DUE SOON"]);
    expect(
      compactBadges(
        item({
          priority: 3,
          when: null,
          why_now_glance: "Thread waiting on you",
          body: "Maya is still waiting for a scheduling response.",
        }),
      ),
    ).toEqual(["MEDIUM"]);
  });

  it("formats need-attention headline, holding note, and can-wait copy", () => {
    expect(mattersNowHeadline(0)).toBe("Nothing needs you right now");
    expect(mattersNowHeadline(1)).toBe("1 thing needs your attention");
    expect(mattersNowHeadline(2)).toBe("2 things need your attention");
    expect(canWaitLabel(1)).toBe("Show 1 that can wait");
    expect(canWaitLabel(47)).toBe("Show 47 that can wait");
    expect(holdingSignalsNote(47)).toMatch(
      /holding 47 lower-priority signals out of view/i,
    );
  });

  it("formats last-evaluated relative copy", () => {
    const now = Date.parse("2026-01-01T09:00:00+00:00");
    expect(lastEvaluatedLabel(now, now)).toBe("Last evaluated just now");
    expect(lastEvaluatedLabel(now - 120_000, now)).toBe(
      "Last evaluated 2 minutes ago",
    );
  });

  it("groups can-wait into secondary category counts", () => {
    const fromFixture = resolveCanWaitGroups(47, FIXTURE_CAN_WAIT_GROUPS);
    expect(fromFixture).toEqual(FIXTURE_CAN_WAIT_GROUPS);
    expect(fromFixture.reduce((sum, g) => sum + g.count, 0)).toBe(47);

    const fromSamples = resolveCanWaitGroups(
      47,
      null,
      FIXTURE_SUPPRESSED.items,
    );
    expect(fromSamples.map((g) => g.label)).toEqual(
      expect.arrayContaining(["Informational", "Automated / noise"]),
    );
    expect(fromSamples.reduce((sum, g) => sum + g.count, 0)).toBe(47);

    const defaults = defaultCanWaitGroups(47);
    expect(defaults.map((g) => g.label)).toEqual([
      "Upcoming calendar",
      "Open threads",
      "Informational",
      "Automated / noise",
    ]);
    expect(defaults.reduce((sum, g) => sum + g.count, 0)).toBe(47);
  });
});
