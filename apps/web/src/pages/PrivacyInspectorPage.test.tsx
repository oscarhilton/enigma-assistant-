import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrivacyInspectorPage } from "./PrivacyInspectorPage";

describe("PrivacyInspectorPage", () => {
  it("renders inspector controls", () => {
    render(<PrivacyInspectorPage />);
    expect(screen.getByRole("heading", { name: /privacy inspector/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /preview remote payload/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel remote send/i })).toBeInTheDocument();
  });
});
