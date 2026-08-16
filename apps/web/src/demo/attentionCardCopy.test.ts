import { describe, expect, it } from "vitest";
import {
  canWaitLabel,
  cardReason,
  compactBadges,
  isEvidenceDumpBody,
  mattersNowHeadline,
  priorityLabel,
  timingLabel,
} from "./attentionCardCopy";
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

  it("prefers glance reason and never surfaces evidence dumps", () => {
    expect(cardReason(item())).toBe("Deadline approaching.");
    expect(
      cardReason(
        item({
          why_now_glance: null,
          body: "Reminder: Review proposal; Email: Re: Proposal",
        }),
      ),
    ).toBe("Before Friday.");
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

  it("builds compact priority · timing badges", () => {
    expect(priorityLabel(4)).toBe("HIGH PRIORITY");
    expect(timingLabel(item())).toBe("DUE SOON");
    expect(compactBadges(item())).toEqual(["HIGH PRIORITY", "DUE SOON"]);
    expect(compactBadges(item({ priority: 3, when: null, why_now_glance: "Thread waiting on you" }))).toEqual([
      "MEDIUM",
    ]);
  });

  it("formats matters-now and can-wait copy", () => {
    expect(mattersNowHeadline(0)).toBe("Nothing needs you right now");
    expect(mattersNowHeadline(1)).toBe("1 thing matters now");
    expect(mattersNowHeadline(2)).toBe("2 things matter now");
    expect(canWaitLabel(1)).toBe("Show 1 that can wait");
    expect(canWaitLabel(47)).toBe("Show 47 that can wait");
  });
});
