import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatPage } from "./ChatPage";

describe("ChatPage", () => {
  it("renders preview-first controls", () => {
    render(<ChatPage />);
    expect(screen.getByRole("heading", { name: /^chat$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /privacy preview/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm send/i })).toBeInTheDocument();
  });
});
