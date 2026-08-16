import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SHADOW_BANNER_TEXT, ShadowModeBanner } from "./ShadowModeBanner";

describe("ShadowModeBanner", () => {
  it("renders SHADOW MODE banner when active", () => {
    render(<ShadowModeBanner active />);
    expect(screen.getByText(SHADOW_BANNER_TEXT)).toBeInTheDocument();
  });

  it("renders nothing when inactive", () => {
    const { container } = render(<ShadowModeBanner active={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
