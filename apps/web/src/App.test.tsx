import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the product name", async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("personal-enigma")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^enigma$/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("conversation-viewport")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
  });
});
