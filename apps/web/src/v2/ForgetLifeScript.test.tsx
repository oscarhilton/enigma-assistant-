import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  FORGET_ACK,
  FORGET_AFTER_RECALL_REPLY,
  FORGET_PROMPT,
  FORGET_RECALL_PROMPT,
  FORGET_RECALL_REPLY,
  FORGET_RETAIN_ACK,
  FORGET_RETAIN_PROMPT,
  MAYA_BIRTHDAY_TITLE,
} from "../pilot/WorldMockLifeScripts";
import { askV2Enigma, jumpV2DemoCheckpoint, launchV2AlexLab } from "./v2ProductHelpers";

describe("UI2-06 Forget Life Script (v2 shell)", () => {
  it("retains ceramics, forgets it, and does not resurrect stale memory in the UI", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(FORGET_RETAIN_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_RETAIN_ACK)).toBeInTheDocument();
    });

    await askV2Enigma(FORGET_RECALL_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_RECALL_REPLY)).toBeInTheDocument();
    });

    await askV2Enigma(FORGET_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_ACK)).toBeInTheDocument();
    });

    await askV2Enigma(FORGET_RECALL_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_AFTER_RECALL_REPLY)).toBeInTheDocument();
    });
    expect(screen.getByText(FORGET_AFTER_RECALL_REPLY)).toHaveTextContent(/not claiming it was deleted everywhere/i);

    fireEvent.click(screen.getByRole("link", { name: /^cases$/i }));
    const cases = screen.getByTestId("v2-cases-surface");
    expect(within(cases).getByText(MAYA_BIRTHDAY_TITLE)).toBeInTheDocument();
    expect(within(cases).queryByText(/likes ceramics/i)).not.toBeInTheDocument();
  });
});
