import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CalendarSelection } from "./CalendarSelection";
import type { CalendarSource } from "./types";

const calendars: CalendarSource[] = [
  { id: "apple:work", name: "Work", provider: "apple_calendar", enabled: true },
  {
    id: "apple:personal",
    name: "Personal",
    provider: "apple_calendar",
    enabled: false,
  },
];

describe("CalendarSelection", () => {
  it("renders calendars with enable/disable checkboxes", () => {
    render(<CalendarSelection calendars={calendars} onToggle={() => undefined} />);
    expect(screen.getByRole("heading", { name: /calendars/i })).toBeInTheDocument();
    const work = screen.getByRole("checkbox", { name: /work/i });
    const personal = screen.getByRole("checkbox", { name: /personal/i });
    expect(work).toBeChecked();
    expect(personal).not.toBeChecked();
  });

  it("notifies when a calendar is toggled", () => {
    const onToggle = vi.fn();
    render(<CalendarSelection calendars={calendars} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole("checkbox", { name: /personal/i }));
    expect(onToggle).toHaveBeenCalledWith("apple:personal", true);
    fireEvent.click(screen.getByRole("checkbox", { name: /work/i }));
    expect(onToggle).toHaveBeenCalledWith("apple:work", false);
  });
});
