import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GoogleCalendarSelection } from "./GoogleCalendarSelection";

describe("GoogleCalendarSelection", () => {
  it("toggles calendar selection and excludes unchecked calendars", () => {
    const onChange = vi.fn();
    render(
      <GoogleCalendarSelection
        calendars={[
          { id: "primary", summary: "Personal", primary: true },
          { id: "work@example.com", summary: "Work" },
        ]}
        selectedIds={["primary"]}
        onChange={onChange}
      />,
    );

    expect(screen.getByRole("heading", { name: /google calendars/i })).toBeInTheDocument();
    const work = screen.getByRole("checkbox", { name: /work/i });
    expect(work).not.toBeChecked();
    fireEvent.click(work);
    expect(onChange).toHaveBeenCalledWith(["primary", "work@example.com"]);

    const personal = screen.getByRole("checkbox", { name: /personal/i });
    fireEvent.click(personal);
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
