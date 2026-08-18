import { describe, expect, it } from "vitest";
import type { ConversationItem } from "../enigma/types";
import {
  NEW_CHAT_TITLE,
  reconcileThreadTitleOnItemsChange,
  threadTitleFromMessage,
} from "./threadTypes";

const ATTENTION_HEAD: ConversationItem = {
  kind: "attention_summary",
  at: "2026-01-19T10:00:00.000Z",
  state: { needs_you: [], context: [], simulated_time: "2026-01-19T10:00:00.000Z" },
};

const USER_CERAMICS: ConversationItem = {
  kind: "user_message",
  text: "Maya mentioned she likes ceramics.",
  at: "2026-01-19T10:01:00.000Z",
};

describe("reconcileThreadTitleOnItemsChange", () => {
  it("keeps dialogue label after in-thread forget (append-only)", () => {
    const before = [ATTENTION_HEAD, USER_CERAMICS];
    const after = [
      ...before,
      { kind: "enigma_message", text: "Okay — dropped.", at: "2026-01-19T10:02:00.000Z" },
    ];
    const title = threadTitleFromMessage(USER_CERAMICS.text);
    expect(reconcileThreadTitleOnItemsChange(before, after, title)).toBe(title);
  });

  it("resets title on checkpoint wholesale replace", () => {
    const before = [
      ATTENTION_HEAD,
      USER_CERAMICS,
      { kind: "enigma_message", text: "Got it.", at: "2026-01-19T10:01:30.000Z" },
    ];
    const after = [ATTENTION_HEAD];
    const ceramicsTitle = threadTitleFromMessage(USER_CERAMICS.text);
    expect(reconcileThreadTitleOnItemsChange(before, after, ceramicsTitle)).toBe(NEW_CHAT_TITLE);
  });

  it("derives title from first user message on wholesale replace with speech", () => {
    const before = [ATTENTION_HEAD, USER_CERAMICS];
    const otherHead: ConversationItem = {
      ...ATTENTION_HEAD,
      at: "2026-01-20T11:00:00.000Z",
    };
    const brunchUser: ConversationItem = {
      kind: "user_message",
      text: "what did I book?",
      at: "2026-01-20T11:01:00.000Z",
    };
    const after = [otherHead, brunchUser];
    expect(reconcileThreadTitleOnItemsChange(before, after, "Maya mentioned she likes ceramics.")).toBe(
      threadTitleFromMessage("what did I book?"),
    );
  });
});
