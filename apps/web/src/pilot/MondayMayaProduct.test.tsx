import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  MAYA_BIRTHDAY_TITLE,
  MAYA_CONTINUE_PROMPT,
  MAYA_CONTINUE_REPLY,
  MAYA_OPENING_PROMPT,
  MAYA_OPENING_REPLY,
} from "./WorldMockLifeScripts";
import { askEnigma, jumpDemoCheckpoint, launchAlexLab } from "./pilotProductHelpers";

describe("P02b Monday/Maya Life Script (pilot shell)", () => {
  it("qualifies a false Sunday-only premise with bank-holiday discovery, not schedule invention", async () => {
    await launchAlexLab();
    await jumpDemoCheckpoint(/Jan 19 · 10:00/);

    expect(screen.getByText(/nothing needs you/i)).toBeInTheDocument();
    expect(screen.getByText(MAYA_BIRTHDAY_TITLE)).toBeInTheDocument();

    await askEnigma(MAYA_OPENING_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(MAYA_OPENING_REPLY)).toBeInTheDocument();
    });
    expect(screen.getByText(MAYA_OPENING_REPLY)).toHaveTextContent(/bank holiday/i);
    expect(screen.getByText(MAYA_OPENING_REPLY)).toHaveTextContent(/24 Feb/i);
    expect(screen.getByText(MAYA_OPENING_REPLY)).toHaveTextContent(/not your only window/i);
    expect(screen.queryByText(/you're off on bank holidays|you have the day off/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/brunch|elena|riverside/i)).not.toBeInTheDocument();
    expect(await screen.findByTestId("activity-strip")).toHaveTextContent(/checked your week/i);

    await askEnigma(MAYA_CONTINUE_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(MAYA_CONTINUE_REPLY)).toBeInTheDocument();
    });
    expect(screen.queryByText(/you always work mondays/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText(/Also on my radar/i));
    fireEvent.click(screen.getByRole("button", { name: MAYA_BIRTHDAY_TITLE }));
    const mayaRow = screen.getByRole("button", { name: MAYA_BIRTHDAY_TITLE }).closest(".radar-item")!;
    fireEvent.click(within(mayaRow).getByRole("button", { name: /Why now/i }));
    await waitFor(() => {
      expect(screen.getByText(/not the same as knowing you are off work/i)).toBeInTheDocument();
    });
    expect(await screen.findByTestId("surface-goose")).toHaveAttribute("data-motion", "return");
  });
});
