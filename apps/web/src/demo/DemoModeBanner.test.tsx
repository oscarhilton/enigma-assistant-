import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DEMO_BANNER_TEXT, DemoModeBanner } from "./DemoModeBanner";

describe("DemoModeBanner", () => {
  it("renders unmistakable copy when active", () => {
    render(<DemoModeBanner active scenarioLabel="Alex Morgan v1" />);
    expect(screen.getByText(DEMO_BANNER_TEXT)).toBeInTheDocument();
    expect(screen.getByText(/Scenario: Alex Morgan v1/i)).toBeInTheDocument();
  });

  it("renders nothing when inactive", () => {
    const { container } = render(<DemoModeBanner active={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
