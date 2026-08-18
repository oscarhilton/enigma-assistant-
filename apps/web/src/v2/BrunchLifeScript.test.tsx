import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  BRUNCH_BOOKED_DISTINCTION,
  BRUNCH_CALENDAR_EVENT,
  BRUNCH_CASE_ID,
  BRUNCH_TITLE,
} from "../pilot/WorldMockClient";
import { askV2Enigma, jumpV2DemoCheckpoint, launchV2AlexLab } from "./v2ProductHelpers";

describe("UI2-06 Brunch Life Script (v2 shell)", () => {
  it("talked about ≠ calendar ≠ booked, Goose tracks work, Why explains evidence", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 20 · 11:00/);

    expect(screen.getByText(/one thing needs you/i)).toBeInTheDocument();
    expect(screen.getByText(BRUNCH_TITLE)).toBeInTheDocument();
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: /^cases$/i }));
    fireEvent.click(await screen.findByTestId(`select-case-${BRUNCH_CASE_ID}`));
    expect(screen.getByTestId("selected-case")).toHaveAttribute("data-case-id", BRUNCH_CASE_ID);

    fireEvent.click(screen.getByRole("link", { name: /^chat$/i }));
    await waitFor(() => {
      expect(screen.getByText(BRUNCH_TITLE)).toBeInTheDocument();
    });

    await askV2Enigma("what did I book?");
    await waitFor(() => {
      expect(screen.getByText(BRUNCH_BOOKED_DISTINCTION)).toBeInTheDocument();
    });
    expect(screen.getByText(BRUNCH_BOOKED_DISTINCTION)).toHaveTextContent(BRUNCH_CALENDAR_EVENT);
    expect(screen.getByText(BRUNCH_BOOKED_DISTINCTION)).toHaveTextContent(/still open/i);
    expect(screen.getByText(BRUNCH_BOOKED_DISTINCTION)).toHaveTextContent(/not a reservation/i);
    expect(screen.queryByText(/confirmed the reservation|reservation is booked/i)).not.toBeInTheDocument();

    expect(await screen.findByTestId("surface-goose")).toHaveAttribute("data-motion", "return");

    fireEvent.click(screen.getByRole("button", { name: /why now/i }));
    await waitFor(() => {
      expect(screen.getByText(/calendar hold cal-brunch-parents is not a reservation/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/rem-brunch-book is still open/i)).toBeInTheDocument();
  });
});
