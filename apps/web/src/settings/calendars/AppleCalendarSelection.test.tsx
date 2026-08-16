import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppleCalendarSelection } from "./AppleCalendarSelection";

describe("AppleCalendarSelection", () => {
  it("toggles calendar selection", () => {
    const onChange = vi.fn();
    render(
      <AppleCalendarSelection
        calendars={[
          { id: "cal-personal", title: "Personal" },
          { id: "cal-work", title: "Work" },
        ]}
        selectedIds={["cal-personal"]}
        onChange={onChange}
      />,
    );

    expect(screen.getByRole("heading", { name: /apple calendars/i })).toBeInTheDocument();
    const work = screen.getByRole("checkbox", { name: /work/i });
    expect(work).not.toBeChecked();
    fireEvent.click(work);
    expect(onChange).toHaveBeenCalledWith(["cal-personal", "cal-work"]);
  });
});
