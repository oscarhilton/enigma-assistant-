import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  FORGET_ACK,
  FORGET_AFTER_RECALL_REPLY,
  FORGET_PROMPT,
  FORGET_RECALL_PROMPT,
  FORGET_RETAIN_PROMPT,
} from "../pilot/WorldMockLifeScripts";
import { askV2Enigma, jumpV2DemoCheckpoint, launchV2AlexLab } from "./v2ProductHelpers";
import { threadTitleFromMessage } from "./threadTypes";

describe("UI2 fossil hunt — Forget + checkpoint leftovers", () => {
  it("sidebar title is first-utterance dialogue label, not post-forget memory", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(FORGET_RETAIN_PROMPT);
    await waitFor(() => {
      expect(screen.getByTestId("v2-thread-list")).toHaveTextContent(
        threadTitleFromMessage(FORGET_RETAIN_PROMPT),
      );
    });

    await askV2Enigma(FORGET_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_ACK)).toBeInTheDocument();
    });

    await askV2Enigma(FORGET_RECALL_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_AFTER_RECALL_REPLY)).toBeInTheDocument();
    });

    // POLICY-OK: title echoes what was said, not what Enigma retains.
    expect(screen.getByTestId("v2-thread-list")).toHaveTextContent(
      threadTitleFromMessage(FORGET_RETAIN_PROMPT),
    );
    expect(screen.getByText(FORGET_AFTER_RECALL_REPLY)).not.toHaveTextContent(/ceramics/i);
  });

  it("checkpoint jump clears stale sidebar title from prior conversation", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(FORGET_RETAIN_PROMPT);
    await waitFor(() => {
      expect(screen.getByTestId("v2-thread-list")).toHaveTextContent(/ceramics/i);
    });

    await jumpV2DemoCheckpoint(/Jan 20 · 11:00/);
    await waitFor(() => {
      expect(screen.getByTestId("v2-thread-list")).not.toHaveTextContent(/ceramics/i);
    });
    expect(screen.getByTestId("v2-thread-list")).toHaveTextContent(/new chat/i);
  });
});
