import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import {
  BRUNCH_BOOKED_DISTINCTION,
  BRUNCH_CALENDAR_EVENT,
  BRUNCH_CASE_ID,
  BRUNCH_TITLE,
} from "./WorldMockClient";

async function launchAlexLab() {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
  fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: "alex_lab" } });
  await waitFor(() => {
    expect(screen.getByTestId("pilot-shell")).toHaveAttribute("data-world", "alex_lab");
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

async function resetToBrunchFixture() {
  fireEvent.click(screen.getByRole("button", { name: /Demo ·/i }));
  fireEvent.click(await screen.findByRole("button", { name: /Jan 20 · 11:00/ }));
  await waitFor(() => {
    expect(screen.getByText(BRUNCH_TITLE)).toBeInTheDocument();
  });
}

describe("P02 Brunch Life Script (pilot shell)", () => {
  it("talked about ≠ calendar ≠ booked, Goose tracks work, Why explains evidence", async () => {
    await launchAlexLab();
    await resetToBrunchFixture();

    expect(screen.getByText(/one thing needs you/i)).toBeInTheDocument();
    expect(screen.getByText(BRUNCH_TITLE)).toBeInTheDocument();
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: /^cases$/i }));
    fireEvent.click(await screen.findByTestId(`select-case-${BRUNCH_CASE_ID}`));
    expect(screen.getByTestId("selected-case")).toHaveAttribute("data-case-id", BRUNCH_CASE_ID);

    fireEvent.click(screen.getByRole("link", { name: /^today$/i }));
    await waitFor(() => {
      expect(screen.getByText(BRUNCH_TITLE)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/ask enigma/i);
    fireEvent.change(input, { target: { value: "what did I book?" } });
    fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
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
