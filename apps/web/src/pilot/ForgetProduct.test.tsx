import { fireEvent, screen, waitFor } from "@testing-library/react";
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
} from "./WorldMockLifeScripts";
import { askEnigma, jumpDemoCheckpoint, launchAlexLab } from "./pilotProductHelpers";

describe("P02e Forget Life Script (pilot shell)", () => {
  it("retains ceramics, forgets it, and does not resurrect stale memory in the UI", async () => {
    await launchAlexLab();
    await jumpDemoCheckpoint(/Jan 19 · 10:00/);

    await askEnigma(FORGET_RETAIN_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_RETAIN_ACK)).toBeInTheDocument();
    });

    await askEnigma(FORGET_RECALL_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_RECALL_REPLY)).toBeInTheDocument();
    });

    await askEnigma(FORGET_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_ACK)).toBeInTheDocument();
    });

    await askEnigma(FORGET_RECALL_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(FORGET_AFTER_RECALL_REPLY)).toBeInTheDocument();
    });
    expect(screen.getByText(FORGET_AFTER_RECALL_REPLY)).toHaveTextContent(/not claiming it was deleted everywhere/i);

    fireEvent.click(screen.getByRole("link", { name: /^cases$/i }));
    expect(screen.getByText(MAYA_BIRTHDAY_TITLE)).toBeInTheDocument();
    expect(screen.queryByText(/likes ceramics/i)).not.toBeInTheDocument();
  });
});
