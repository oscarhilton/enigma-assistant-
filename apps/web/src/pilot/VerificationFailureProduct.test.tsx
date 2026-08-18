import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  NOTIFY_TEAM_CASE_ID,
  NOTIFY_TEAM_TITLE,
  VERIFICATION_CHECK_PROMPT,
  VERIFICATION_FAILURE_REPLY,
  VERIFICATION_FAILURE_RESULT,
  VERIFICATION_OUTCOME_PROMPT,
  VERIFICATION_PREPARE_PROMPT,
  VERIFICATION_VERIFYING_REPLY,
} from "./WorldMockLifeScripts";
import { askEnigma, jumpDemoCheckpoint, launchAlexLab } from "./pilotProductHelpers";

describe("P02d Verification failure / FALSE VICTORY (pilot shell)", () => {
  it("PREPARE → APPROVE → ACTING → VERIFYING → fail — return is not victory", async () => {
    await launchAlexLab();
    await jumpDemoCheckpoint(/Jan 19 · 10:00/);

    expect(screen.getByText(NOTIFY_TEAM_TITLE)).toBeInTheDocument();

    await askEnigma(VERIFICATION_PREPARE_PROMPT);
    await waitFor(() => {
      expect(screen.getByTestId("assist-proposal")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("assist-result")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^approve$/i }));
    await waitFor(() => {
      expect(screen.getByText(/sending the note now/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("assist-result")).not.toBeInTheDocument();

    await askEnigma(VERIFICATION_CHECK_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(VERIFICATION_VERIFYING_REPLY)).toBeInTheDocument();
    });
    expect(screen.getByText(/checking whether the note/i)).toBeInTheDocument();

    await askEnigma(VERIFICATION_OUTCOME_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(VERIFICATION_FAILURE_REPLY)).toBeInTheDocument();
    });
    const result = screen.getByTestId("assist-result");
    expect(result).toHaveTextContent(VERIFICATION_FAILURE_RESULT);
    expect(result.className).toMatch(/error/);
    expect(screen.queryByText(/^Done —|successfully completed|job succeeded/i)).not.toBeInTheDocument();

    const goose = await screen.findByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-motion", "return");

    fireEvent.click(screen.getByRole("link", { name: /^cases$/i }));
    expect(await screen.findByTestId(`select-case-${NOTIFY_TEAM_CASE_ID}`)).toBeInTheDocument();
    expect(screen.getByText(NOTIFY_TEAM_TITLE)).toBeInTheDocument();
  });
});
